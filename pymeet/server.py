"""PyMeet sunucusu: gelen sohbet, ses ve ekran verisini odadaki herkese iletir.

Kullanım:  python server.py --host 0.0.0.0 --port 5050
"""
import argparse
import asyncio
import json

from protocol import (AUDIO, HEADER, JOIN, MAX_FRAME, STOP, SYS, TEXT, USERS,
                      VIDEO, pack)


class Client:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.name = "Misafir"
        self.queue = asyncio.Queue(maxsize=1000)

    def put(self, data: bytes, limit: int | None = None):
        # Yavaş istemcide ses/görüntü birikmesin diye eski yerine yeniyi atla
        if limit is not None and self.queue.qsize() >= limit:
            return
        try:
            self.queue.put_nowait(data)
        except asyncio.QueueFull:
            pass

    async def write_loop(self):
        try:
            while True:
                data = await self.queue.get()
                if data is None:
                    break
                self.writer.write(data)
                await self.writer.drain()
        except (ConnectionError, OSError):
            pass


class Room:
    def __init__(self):
        self.clients: set[Client] = set()
        self.sharer: Client | None = None
        self.last_frame: bytes | None = None

    def broadcast(self, kind, payload, exclude=None, limit=None):
        data = pack(kind, payload)
        for c in list(self.clients):
            if c is not exclude:
                c.put(data, limit)

    def notify(self, text):
        self.broadcast(SYS, text.encode())

    def send_users(self):
        names = sorted(c.name for c in self.clients)
        self.broadcast(USERS, json.dumps(names).encode())

    def unique_name(self, name):
        name = (name.strip() or "Misafir")[:32]
        taken = {c.name for c in self.clients}
        base, i = name, 2
        while name in taken:
            name = f"{base} ({i})"
            i += 1
        return name

    async def read_frame(self, reader):
        kind, size = HEADER.unpack(await reader.readexactly(HEADER.size))
        if size > MAX_FRAME:
            raise ValueError("Çerçeve çok büyük")
        return kind, await reader.readexactly(size)

    async def handle(self, reader, writer):
        c = Client(reader, writer)
        writer_task = asyncio.create_task(c.write_loop())
        joined = False
        try:
            kind, payload = await self.read_frame(reader)
            if kind != JOIN:
                return
            c.name = self.unique_name(payload.decode("utf-8", "ignore"))
            self.clients.add(c)
            joined = True
            self.notify(f"{c.name} katıldı")
            self.send_users()
            if self.sharer and self.last_frame:
                c.put(pack(SYS, f"{self.sharer.name} ekranını paylaşıyor".encode()))
                c.put(pack(VIDEO, self.last_frame))

            while True:
                kind, payload = await self.read_frame(reader)
                if kind == TEXT:
                    msg = {"name": c.name, "text": payload.decode("utf-8", "ignore")}
                    self.broadcast(TEXT, json.dumps(msg).encode())
                elif kind == AUDIO:
                    tag = c.name.encode()[:255]
                    self.broadcast(AUDIO, bytes([len(tag)]) + tag + payload,
                                   exclude=c, limit=50)
                elif kind == VIDEO:
                    if self.sharer is not c:
                        if self.sharer:
                            self.sharer.put(pack(STOP))
                        self.sharer = c
                        self.notify(f"{c.name} ekranını paylaşıyor")
                    self.last_frame = payload
                    self.broadcast(VIDEO, payload, exclude=c, limit=5)
                elif kind == STOP and self.sharer is c:
                    self.sharer, self.last_frame = None, None
                    self.broadcast(STOP, b"", exclude=c)
                    self.notify(f"{c.name} paylaşımı durdurdu")
        except (asyncio.IncompleteReadError, ConnectionError, ValueError, OSError):
            pass
        finally:
            if joined:
                self.clients.discard(c)
                if self.sharer is c:
                    self.sharer, self.last_frame = None, None
                    self.broadcast(STOP)
                self.notify(f"{c.name} ayrıldı")
                self.send_users()
            c.queue.put_nowait(None) if not c.queue.full() else None
            writer_task.cancel()
            writer.close()


async def main():
    ap = argparse.ArgumentParser(description="PyMeet sunucusu")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=5050)
    args = ap.parse_args()

    room = Room()
    server = await asyncio.start_server(room.handle, args.host, args.port)
    print(f"PyMeet sunucusu çalışıyor: {args.host}:{args.port}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Sunucu kapatıldı.")

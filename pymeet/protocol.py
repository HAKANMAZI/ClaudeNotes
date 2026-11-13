"""Sunucu ve istemcinin ortak kullandığı basit çerçeve protokolü.

Her çerçeve: 1 bayt tür + 4 bayt uzunluk (big-endian) + veri.
"""
import struct

HEADER = struct.Struct("!cI")
MAX_FRAME = 8 * 1024 * 1024  # 8 MB

JOIN = b"J"   # istemci -> sunucu: kullanıcı adı
TEXT = b"T"   # sohbet mesajı
AUDIO = b"A"  # ses (int16 PCM). Sunucu, gönderen adını başa ekler
VIDEO = b"V"  # ekran görüntüsü (JPEG)
STOP = b"S"   # ekran paylaşımı bitti
USERS = b"U"  # kullanıcı listesi (JSON)
SYS = b"M"    # sistem bildirimi


def pack(kind: bytes, payload: bytes = b"") -> bytes:
    return HEADER.pack(kind, len(payload)) + payload


def _recv_exact(sock, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Bağlantı kapandı")
        buf.extend(chunk)
    return bytes(buf)


def recv_frame(sock):
    kind, size = HEADER.unpack(_recv_exact(sock, HEADER.size))
    if size > MAX_FRAME:
        raise ValueError("Çerçeve çok büyük")
    return kind, _recv_exact(sock, size)

"""PyMeet istemcisi: sohbet, sesli konuşma ve ekran paylaşımı.

Kullanım:  python client.py --host SUNUCU_IP --port 5050 --name Hasan
(Parametre verilmezse açılışta sorulur.)
"""
import argparse
import collections
import io
import json
import queue
import socket
import threading
import time
import tkinter as tk
from tkinter import messagebox, simpledialog

import numpy as np
from PIL import Image, ImageTk

try:
    import sounddevice as sd
except Exception:  # PortAudio yoksa ses kapalı çalışır
    sd = None
try:
    import mss
except Exception:
    mss = None

from protocol import (AUDIO, JOIN, STOP, SYS, TEXT, USERS, VIDEO, pack,
                      recv_frame)

RATE = 16000      # Hz
BLOCK = 640       # 40 ms
FPS = 6           # ekran paylaşımı kare/sn
MAX_SIZE = (1280, 720)
JPEG_QUALITY = 55

BG, PANEL, FG, ACCENT, MUTED = "#1e1f24", "#2a2c33", "#e8e8ea", "#2d8cff", "#8a8d96"


class App:
    def __init__(self, root, host, port, name):
        self.root = root
        self.running = True
        self.mic_on = False
        self.sharing = False
        self.inbox = queue.Queue()
        self.sendq = queue.Queue(maxsize=500)
        self.audio_bufs = collections.defaultdict(collections.deque)
        self.audio_lock = threading.Lock()
        self.latest_frame = None
        self.new_frame = False
        self.photo = None
        self.inp = self.out = None

        self.sock = socket.create_connection((host, port), timeout=10)
        self.sock.settimeout(None)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        self.build_ui(name)
        self.send(JOIN, name.encode())
        threading.Thread(target=self.send_loop, daemon=True).start()
        threading.Thread(target=self.recv_loop, daemon=True).start()
        self.start_audio()
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(30, self.poll)

    # ---------- Arayüz ----------
    def build_ui(self, name):
        r = self.root
        r.title(f"PyMeet — {name}")
        r.geometry("1150x680")
        r.configure(bg=BG)

        main = tk.Frame(r, bg=BG)
        main.pack(fill="both", expand=True, padx=8, pady=8)

        self.video = tk.Label(main, bg="black", fg=MUTED,
                              text="Kimse ekran paylaşmıyor", font=("Segoe UI", 14))
        self.video.pack(side="left", fill="both", expand=True)

        side = tk.Frame(main, bg=PANEL, width=320)
        side.pack(side="right", fill="y", padx=(8, 0))
        side.pack_propagate(False)

        tk.Label(side, text="Katılımcılar", bg=PANEL, fg=FG,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=8, pady=(8, 2))
        self.users = tk.Listbox(side, height=6, bg=BG, fg=FG, bd=0,
                                highlightthickness=0, font=("Segoe UI", 10))
        self.users.pack(fill="x", padx=8)

        tk.Label(side, text="Sohbet", bg=PANEL, fg=FG,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=8, pady=(10, 2))
        self.chat = tk.Text(side, bg=BG, fg=FG, bd=0, wrap="word",
                            state="disabled", font=("Segoe UI", 10))
        self.chat.tag_configure("sys", foreground=MUTED)
        self.chat.tag_configure("me", foreground=ACCENT)
        self.chat.pack(fill="both", expand=True, padx=8)

        row = tk.Frame(side, bg=PANEL)
        row.pack(fill="x", padx=8, pady=8)
        self.entry = tk.Entry(row, bg=BG, fg=FG, insertbackground=FG, bd=0,
                              font=("Segoe UI", 10))
        self.entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.entry.bind("<Return>", lambda e: self.send_text())
        tk.Button(row, text="Gönder", command=self.send_text, bg=ACCENT, fg="white",
                  bd=0, padx=10).pack(side="right", padx=(6, 0))

        bar = tk.Frame(r, bg=PANEL)
        bar.pack(fill="x")
        self.mic_btn = tk.Button(bar, text="🎤 Mikrofonu Aç", command=self.toggle_mic,
                                 bg=BG, fg=FG, bd=0, padx=14, pady=8)
        self.mic_btn.pack(side="left", padx=8, pady=8)
        self.share_btn = tk.Button(bar, text="🖥 Ekranı Paylaş", command=self.toggle_share,
                                   bg=BG, fg=FG, bd=0, padx=14, pady=8)
        self.share_btn.pack(side="left", pady=8)
        if mss is None:
            self.share_btn.configure(state="disabled", text="🖥 mss kurulu değil")
        tk.Button(bar, text="Ayrıl", command=self.close, bg="#d9363e", fg="white",
                  bd=0, padx=14, pady=8).pack(side="right", padx=8, pady=8)

    def add_chat(self, text, tag=None):
        self.chat.configure(state="normal")
        self.chat.insert("end", text + "\n", tag)
        self.chat.see("end")
        self.chat.configure(state="disabled")

    # ---------- Ağ ----------
    def send(self, kind, payload=b"", limit=None):
        if limit is not None and self.sendq.qsize() >= limit:
            return  # sıkışıklıkta ses/görüntü atlanır
        try:
            self.sendq.put_nowait(pack(kind, payload))
        except queue.Full:
            pass

    def send_loop(self):
        try:
            while self.running:
                data = self.sendq.get()
                if data is None:
                    break
                self.sock.sendall(data)
        except OSError:
            pass

    def recv_loop(self):
        try:
            while self.running:
                kind, p = recv_frame(self.sock)
                if kind == AUDIO:
                    n = p[0]
                    who = p[1:1 + n].decode("utf-8", "ignore")
                    pcm = np.frombuffer(p[1 + n:], dtype=np.int16)
                    with self.audio_lock:
                        dq = self.audio_bufs[who]
                        dq.append(pcm)
                        while len(dq) > 8:  # gecikme birikmesin
                            dq.popleft()
                elif kind == VIDEO:
                    try:
                        img = Image.open(io.BytesIO(p))
                        img.load()
                    except Exception:
                        continue
                    self.latest_frame, self.new_frame = img, True
                else:
                    self.inbox.put((kind, p))
        except (OSError, ConnectionError, ValueError):
            if self.running:
                self.inbox.put((b"X", b""))

    def poll(self):
        if not self.running:
            return
        while True:
            try:
                kind, p = self.inbox.get_nowait()
            except queue.Empty:
                break
            if kind == TEXT:
                m = json.loads(p)
                self.add_chat(f"{m['name']}: {m['text']}")
            elif kind == SYS:
                self.add_chat("• " + p.decode(), "sys")
            elif kind == USERS:
                self.users.delete(0, "end")
                for n in json.loads(p):
                    self.users.insert("end", n)
            elif kind == STOP:
                self.latest_frame = None
                self.video.configure(image="", text="Kimse ekran paylaşmıyor")
                self.photo = None
                if self.sharing:  # başkası paylaşımı devraldı
                    self.toggle_share()
            elif kind == b"X":
                messagebox.showerror("PyMeet", "Sunucu bağlantısı koptu.")
                self.close()
                return
        if self.new_frame and self.latest_frame is not None:
            self.new_frame = False
            self.show_frame(self.latest_frame)
        self.root.after(30, self.poll)

    def show_frame(self, img):
        w, h = self.video.winfo_width(), self.video.winfo_height()
        if w < 50 or h < 50:
            w, h = 800, 450
        s = min(w / img.width, h / img.height)
        img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))))
        self.photo = ImageTk.PhotoImage(img)
        self.video.configure(image=self.photo, text="")

    def send_text(self):
        text = self.entry.get().strip()
        if text:
            self.send(TEXT, text.encode())
            self.entry.delete(0, "end")

    # ---------- Ses ----------
    def start_audio(self):
        if sd is None:
            self.add_chat("• sounddevice yüklenemedi, ses kapalı.", "sys")
            self.mic_btn.configure(state="disabled")
            return
        try:
            self.out = sd.OutputStream(samplerate=RATE, channels=1, dtype="int16",
                                       blocksize=BLOCK, callback=self.out_cb)
            self.out.start()
        except Exception as e:
            self.add_chat(f"• Hoparlör açılamadı: {e}", "sys")
        try:
            self.inp = sd.InputStream(samplerate=RATE, channels=1, dtype="int16",
                                      blocksize=BLOCK, callback=self.in_cb)
            self.inp.start()
        except Exception as e:
            self.add_chat(f"• Mikrofon açılamadı: {e}", "sys")
            self.mic_btn.configure(state="disabled")

    def in_cb(self, indata, frames, t, status):
        if self.mic_on:
            self.send(AUDIO, indata.tobytes(), limit=50)

    def out_cb(self, outdata, frames, t, status):
        mix = np.zeros(frames, dtype=np.int32)
        with self.audio_lock:
            for dq in self.audio_bufs.values():
                if dq:
                    chunk = dq.popleft()
                    n = min(len(chunk), frames)
                    mix[:n] += chunk[:n]
        outdata[:, 0] = np.clip(mix, -32768, 32767).astype(np.int16)

    def toggle_mic(self):
        self.mic_on = not self.mic_on
        self.mic_btn.configure(text="🔇 Mikrofonu Kapat" if self.mic_on else "🎤 Mikrofonu Aç",
                               bg=ACCENT if self.mic_on else BG)

    # ---------- Ekran paylaşımı ----------
    def toggle_share(self):
        if not self.sharing:
            self.sharing = True
            self.share_btn.configure(text="⏹ Paylaşımı Durdur", bg=ACCENT)
            self.video.configure(image="", text="Ekranını paylaşıyorsun")
            self.photo = None
            threading.Thread(target=self.share_loop, daemon=True).start()
        else:
            self.sharing = False
            self.share_btn.configure(text="🖥 Ekranı Paylaş", bg=BG)
            self.video.configure(text="Kimse ekran paylaşmıyor")

    def share_loop(self):
        try:
            with mss.mss() as sct:
                mon = sct.monitors[1]
                while self.sharing and self.running:
                    t0 = time.time()
                    shot = sct.grab(mon)
                    img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                    img.thumbnail(MAX_SIZE)
                    buf = io.BytesIO()
                    img.save(buf, "JPEG", quality=JPEG_QUALITY)
                    self.send(VIDEO, buf.getvalue(), limit=5)
                    time.sleep(max(0.0, 1 / FPS - (time.time() - t0)))
        except Exception as e:
            self.inbox.put((SYS, f"Ekran yakalanamadı: {e}".encode()))
            self.sharing = False
        self.send(STOP)

    # ---------- Kapanış ----------
    def close(self):
        if not self.running:
            return
        self.sharing = False
        self.running = False
        for s in (self.inp, self.out):
            try:
                if s:
                    s.stop()
                    s.close()
            except Exception:
                pass
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()
        self.root.destroy()


def main():
    ap = argparse.ArgumentParser(description="PyMeet istemcisi")
    ap.add_argument("--host")
    ap.add_argument("--port", type=int, default=5050)
    ap.add_argument("--name")
    args = ap.parse_args()

    root = tk.Tk()
    root.withdraw()
    host = args.host or simpledialog.askstring("PyMeet", "Sunucu adresi:",
                                               initialvalue="127.0.0.1")
    name = args.name or simpledialog.askstring("PyMeet", "Adınız:")
    if not host or not name:
        return
    try:
        App(root, host, args.port, name)
    except OSError as e:
        messagebox.showerror("PyMeet", f"Sunucuya bağlanılamadı:\n{e}")
        return
    root.deiconify()
    root.mainloop()


if __name__ == "__main__":
    main()

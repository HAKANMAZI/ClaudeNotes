"""
Video İndirici - YouTube ve diğer sitelerden MP3 / MP4 indirme
Gerekli: pip install yt-dlp   +   ffmpeg (MP3 için)
"""
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

VARSAYILAN_KLASOR = os.path.join(os.path.expanduser("~"), "Downloads")


class Uygulama(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video İndirici")
        self.geometry("560x330")
        self.resizable(False, False)

        self.link = tk.StringVar()
        self.bicim = tk.StringVar(value="mp4")
        self.kalite = tk.StringVar(value="En iyi")
        self.klasor = tk.StringVar(value=VARSAYILAN_KLASOR)
        self.durum = tk.StringVar(value="Hazır")

        p = {"padx": 10, "pady": 6}
        tk.Label(self, text="Video linki:").grid(row=0, column=0, sticky="w", **p)
        tk.Entry(self, textvariable=self.link, width=55).grid(row=0, column=1, columnspan=2, **p)

        tk.Label(self, text="Biçim:").grid(row=1, column=0, sticky="w", **p)
        f = tk.Frame(self)
        f.grid(row=1, column=1, sticky="w")
        tk.Radiobutton(f, text="MP4 (video)", variable=self.bicim, value="mp4").pack(side="left")
        tk.Radiobutton(f, text="MP3 (ses)", variable=self.bicim, value="mp3").pack(side="left")

        tk.Label(self, text="Kalite:").grid(row=2, column=0, sticky="w", **p)
        ttk.Combobox(self, textvariable=self.kalite, state="readonly", width=12,
                     values=["En iyi", "1080p", "720p", "480p", "360p"]).grid(row=2, column=1, sticky="w", **p)

        tk.Label(self, text="Klasör:").grid(row=3, column=0, sticky="w", **p)
        tk.Entry(self, textvariable=self.klasor, width=42).grid(row=3, column=1, sticky="w", **p)
        tk.Button(self, text="Seç", command=self.klasor_sec).grid(row=3, column=2, **p)

        self.btn = tk.Button(self, text="İNDİR", bg="#2e7d32", fg="white",
                             font=("Segoe UI", 11, "bold"), width=20, command=self.baslat)
        self.btn.grid(row=4, column=0, columnspan=3, pady=12)

        self.bar = ttk.Progressbar(self, length=520, mode="determinate")
        self.bar.grid(row=5, column=0, columnspan=3, padx=10)
        tk.Label(self, textvariable=self.durum, fg="#555").grid(row=6, column=0, columnspan=3, pady=6)

    def klasor_sec(self):
        k = filedialog.askdirectory(initialdir=self.klasor.get())
        if k:
            self.klasor.set(k)

    def baslat(self):
        if yt_dlp is None:
            messagebox.showerror("Eksik", "Önce kurun:  pip install yt-dlp")
            return
        if not self.link.get().strip():
            messagebox.showwarning("Uyarı", "Lütfen bir link girin.")
            return
        self.btn.config(state="disabled")
        self.bar["value"] = 0
        threading.Thread(target=self.indir, daemon=True).start()

    def ilerleme(self, d):
        if d["status"] == "downloading":
            top = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            if top:
                yuzde = d["downloaded_bytes"] * 100 / top
                self.after(0, lambda: self.bar.config(value=yuzde))
                self.after(0, lambda: self.durum.set(f"İndiriliyor... %{yuzde:.0f}"))
        elif d["status"] == "finished":
            self.after(0, lambda: self.durum.set("Dönüştürülüyor..."))

    def indir(self):
        sablon = os.path.join(self.klasor.get(), "%(title)s.%(ext)s")
        ayar = {"outtmpl": sablon, "progress_hooks": [self.ilerleme],
                "noplaylist": True, "quiet": True}
        if self.bicim.get() == "mp3":
            ayar["format"] = "bestaudio/best"
            ayar["postprocessors"] = [{"key": "FFmpegExtractAudio",
                                       "preferredcodec": "mp3", "preferredquality": "192"}]
        else:
            k = self.kalite.get()
            if k == "En iyi":
                ayar["format"] = "bestvideo+bestaudio/best"
            else:
                h = k.replace("p", "")
                ayar["format"] = f"bestvideo[height<={h}]+bestaudio/best[height<={h}]"
            ayar["merge_output_format"] = "mp4"
        try:
            with yt_dlp.YoutubeDL(ayar) as ydl:
                ydl.download([self.link.get().strip()])
            self.after(0, lambda: (self.bar.config(value=100), self.durum.set("Tamamlandı ✔")))
        except Exception as e:
            hata = str(e)
            self.after(0, lambda: (self.durum.set("Hata!"), messagebox.showerror("Hata", hata)))
        finally:
            self.after(0, lambda: self.btn.config(state="normal"))


if __name__ == "__main__":
    Uygulama().mainloop()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HakTerm v3 - MobaXterm benzeri, şık ve ücretsiz SSH + SFTP istemcisi.

v3 ile gelenler (görünüm):
  - Koyu, modern arayüz; renkli simgeli üst araç çubuğu
  - Sol panelde renkli oturum kartları ve arama
  - MobaXterm gibi solda SFTP paneli (bağlanınca otomatik açılır)
  - Açılış ekranı: son oturumlar, tek tıkla bağlan
  - Beş terminal teması: Gece, Dracula, Monokai, Solarized, One Dark
  - Yazı boyutu büyüt / küçült (Ctrl + fare tekerleği)
  - Sekmelerde renkli bağlantı durumu (yeşil, sarı, kırmızı)
  - Renkli durum çubuğu, koyu pencereler
  - Sekme menüsü: yeniden bağlan, çoğalt, kapat

v2'den kalanlar:
  - Gerçek terminal emülasyonu (pyte): renkler, vim, htop, top, nano
  - Geçmişe kaydırma, bracketed paste

Kısayollar (terminalde):
  - Sağ tık          : Seçili metin varsa kopyala, yoksa yapıştır
  - Ctrl+Shift+C / V : Kopyala / yapıştır
  - Shift+PageUp/Down: Geçmişte gezin
  - Ctrl+Shift+N     : Hızlı bağlan
  - Ctrl+Shift+W     : Sekmeyi kapat
  - Ctrl+Tab         : Sonraki sekme

Gereken: pip install paramiko pyte
"""

import collections
import copy
import json
import os
import posixpath
import queue
import stat
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

import paramiko
import pyte

APP_NAME = "HakTerm"
VERSION = "v3"
HOME = os.path.expanduser("~")
SESSIONS_FILE = os.path.join(HOME, ".hakterm_sessions.json")
SETTINGS_FILE = os.path.join(HOME, ".hakterm_settings.json")
SCROLLBACK = 5000

# ---------------------------------------------------------------- renkler
UI = {
    "bg": "#16191e", "header": "#101317", "panel": "#1d2229", "panel2": "#262c35",
    "card": "#222831", "border": "#2f3742", "hover": "#2e3642", "text": "#e6edf3",
    "muted": "#8b949e", "accent": "#2f81f7", "accent_hover": "#4b93fa",
    "select": "#1c3a63", "green": "#2ea043", "yellow": "#d29922", "red": "#e5534b",
    "status": "#0d1014",
}
SESSION_COLORS = ["#2f81f7", "#2ea043", "#d29922", "#db61a2",
                  "#8957e5", "#1f9bd1", "#e5534b", "#e8853d"]
STATE_COLORS = {"connecting": UI["yellow"], "ok": UI["green"],
                "error": UI["red"], "closed": "#6e7681"}
STATE_TEXT = {"connecting": "Bağlanıyor", "ok": "Bağlı", "error": "Hata", "closed": "Kapalı"}

COLOR_NAMES = ["black", "red", "green", "brown", "blue", "magenta", "cyan", "white"]
THEMES = {
    "Gece": {"bg": "#0c0c0c", "fg": "#cccccc", "cursor": "#ffffff", "colors": [
        "#0c0c0c", "#c50f1f", "#13a10e", "#c19c00", "#0037da", "#881798", "#3a96dd", "#cccccc",
        "#767676", "#e74856", "#16c60c", "#f9f1a5", "#3b78ff", "#b4009e", "#61d6d6", "#f2f2f2"]},
    "Dracula": {"bg": "#282a36", "fg": "#f8f8f2", "cursor": "#f8f8f2", "colors": [
        "#21222c", "#ff5555", "#50fa7b", "#f1fa8c", "#bd93f9", "#ff79c6", "#8be9fd", "#f8f8f2",
        "#6272a4", "#ff6e6e", "#69ff94", "#ffffa5", "#d6acff", "#ff92df", "#a4ffff", "#ffffff"]},
    "Monokai": {"bg": "#272822", "fg": "#f8f8f2", "cursor": "#f8f8f0", "colors": [
        "#272822", "#f92672", "#a6e22e", "#f4bf75", "#66d9ef", "#ae81ff", "#a1efe4", "#f8f8f2",
        "#75715e", "#f92672", "#a6e22e", "#f4bf75", "#66d9ef", "#ae81ff", "#a1efe4", "#f9f8f5"]},
    "Solarized": {"bg": "#002b36", "fg": "#93a1a1", "cursor": "#93a1a1", "colors": [
        "#073642", "#dc322f", "#859900", "#b58900", "#268bd2", "#d33682", "#2aa198", "#eee8d5",
        "#586e75", "#cb4b16", "#859900", "#b58900", "#268bd2", "#6c71c4", "#2aa198", "#fdf6e3"]},
    "One Dark": {"bg": "#1e2127", "fg": "#abb2bf", "cursor": "#528bff", "colors": [
        "#1e2127", "#e06c75", "#98c379", "#d19a66", "#61afef", "#c678dd", "#56b6c2", "#abb2bf",
        "#5c6370", "#e06c75", "#98c379", "#e5c07b", "#61afef", "#c678dd", "#56b6c2", "#ffffff"]},
}

UI_FONT = "Segoe UI"
MONO_FONT = "Consolas"

DECCKM = 1 << 5
BRACKETED_PASTE = 2004 << 5
ALT_SCREEN = (47, 1047, 1049)

KEYMAP = {
    "Return": "\r", "KP_Enter": "\r", "BackSpace": "\x7f", "Tab": "\t",
    "Escape": "\x1b", "Up": "\x1b[A", "Down": "\x1b[B", "Right": "\x1b[C",
    "Left": "\x1b[D", "Home": "\x1b[H", "End": "\x1b[F", "Delete": "\x1b[3~",
    "Insert": "\x1b[2~", "Prior": "\x1b[5~", "Next": "\x1b[6~",
    "F1": "\x1bOP", "F2": "\x1bOQ", "F3": "\x1bOR", "F4": "\x1bOS",
    "F5": "\x1b[15~", "F6": "\x1b[17~", "F7": "\x1b[18~", "F8": "\x1b[19~",
    "F9": "\x1b[20~", "F10": "\x1b[21~", "F11": "\x1b[23~", "F12": "\x1b[24~",
}
APP_CURSOR = {"Up": "\x1bOA", "Down": "\x1bOB", "Right": "\x1bOC", "Left": "\x1bOD",
              "Home": "\x1bOH", "End": "\x1bOF"}
MODIFIER_KEYS = {"Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R",
                 "Caps_Lock", "Num_Lock", "Super_L", "Super_R", "Meta_L", "Meta_R"}


# ---------------------------------------------------------------- yardımcılar
def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def human_size(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def theme_palette(theme):
    p = {}
    for i, n in enumerate(COLOR_NAMES):
        p[n] = theme["colors"][i]
        p["bright" + n] = theme["colors"][8 + i]
    p["yellow"], p["brightyellow"] = p["brown"], p["brightbrown"]
    return p


def resolve_color(name, default, palette, bold=False):
    if name == "default":
        return default
    if bold and name in COLOR_NAMES:
        name = "bright" + name
    if len(name) == 6:
        try:
            int(name, 16)
            return "#" + name
        except ValueError:
            pass
    return palette.get(name, default)


def pick_font(candidates, fallback):
    fams = {f.lower() for f in tkfont.families()}
    for c in candidates:
        if c.lower() in fams:
            return c
    return fallback


def round_rect(cv, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


# ---------------------------------------------------------------- simgeler (Pillow gerektirmez)
def icon_dot(color, size=10):
    img = tk.PhotoImage(width=size, height=size)
    c, r = (size - 1) / 2, size / 2 - 0.3
    for y in range(size):
        xs = [x for x in range(size) if (x - c) ** 2 + (y - c) ** 2 <= r * r]
        if xs:
            img.put(color, to=(xs[0], y, xs[-1] + 1, y + 1))
    return img


def icon_folder():
    img = tk.PhotoImage(width=18, height=16)
    img.put("#c48a1f", to=(1, 2, 8, 5))
    img.put("#e8a93a", to=(1, 4, 17, 14))
    img.put("#f5c35a", to=(1, 5, 17, 7))
    return img


def icon_file():
    img = tk.PhotoImage(width=18, height=16)
    img.put("#7d93ad", to=(4, 1, 14, 16))
    img.put("#d5dfea", to=(5, 2, 13, 15))
    for y in (5, 8, 11):
        img.put("#9fb3c8", to=(7, 1 + y, 12, 2 + y))
    return img


def icon_link():
    img = icon_file()
    img.put("#2f81f7", to=(4, 11, 9, 16))
    return img


def icon_monitor(color):
    img = tk.PhotoImage(width=24, height=22)
    img.put(color, to=(1, 2, 23, 16))
    img.put("#0d1117", to=(3, 4, 21, 14))
    for i in range(3):                       # ">" işareti
        img.put("#7ee787", to=(6 + i, 6 + i, 8 + i, 7 + i))
        img.put("#7ee787", to=(6 + i, 12 - i, 8 + i, 13 - i))
    img.put("#e6edf3", to=(11, 11, 17, 13))  # "_"
    img.put(color, to=(10, 16, 14, 19))
    img.put(color, to=(6, 19, 18, 21))
    return img


def icon_app():
    img = tk.PhotoImage(width=32, height=32)
    img.put(UI["accent"], to=(2, 0, 30, 32))
    img.put(UI["accent"], to=(0, 2, 32, 30))
    for i in range(6):
        img.put("white", to=(7 + i, 8 + i, 10 + i, 10 + i))
        img.put("white", to=(7 + i, 22 - i, 10 + i, 24 - i))
    img.put("white", to=(16, 21, 26, 24))
    return img


# ---------------------------------------------------------------- küçük bileşenler
class Tooltip:
    def __init__(self, widget, text):
        self.widget, self.text, self.tip, self.job = widget, text, None, None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<Button-1>", self._hide, add="+")

    def _schedule(self, e):
        self.job = self.widget.after(500, self._show)

    def _show(self):
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, bg="#30363d", fg=UI["text"], padx=8, pady=3,
                 font=(UI_FONT, 9)).pack()

    def _hide(self, e=None):
        if self.job:
            self.widget.after_cancel(self.job)
            self.job = None
        if self.tip:
            self.tip.destroy()
            self.tip = None


class FlatButton(tk.Label):
    """Düz, renkli, üzerine gelince açılan buton."""

    def __init__(self, master, text, command, bg=None, fg=None, hover=None,
                 font=None, padx=12, pady=6, tooltip=None):
        self._bg = bg or UI["panel2"]
        self._hover = hover or UI["hover"]
        super().__init__(master, text=text, bg=self._bg, fg=fg or UI["text"],
                         font=font or (UI_FONT, 9), padx=padx, pady=pady, cursor="hand2")
        self.command = command
        self.bind("<Enter>", lambda e: self.config(bg=self._hover))
        self.bind("<Leave>", lambda e: self.config(bg=self._bg))
        self.bind("<ButtonRelease-1>", lambda e: self.command())
        if tooltip:
            Tooltip(self, tooltip)


class ToolButton(tk.Canvas):
    """Üst araç çubuğundaki renkli simgeli buton (MobaXterm şeridi gibi)."""

    def __init__(self, master, label, glyph, color, command, width=76):
        super().__init__(master, width=width, height=66, bg=UI["header"],
                         highlightthickness=0, bd=0, cursor="hand2")
        self.command, self.active, self.hover = command, False, False
        self.bgrect = round_rect(self, 3, 3, width - 3, 63, 10, fill=UI["header"], outline="")
        cx = width / 2
        round_rect(self, cx - 17, 8, cx + 17, 42, 9, fill=color, outline="")
        self.create_text(cx, 25, text=glyph, fill="white", font=(UI_FONT, 14, "bold"))
        self.create_text(cx, 53, text=label, fill=UI["text"], font=(UI_FONT, 8))
        self.bind("<Enter>", lambda e: self._paint(True))
        self.bind("<Leave>", lambda e: self._paint(False))
        self.bind("<ButtonRelease-1>", lambda e: self.command())

    def set_active(self, on):
        self.active = on
        self._paint(self.hover)

    def _paint(self, hover):
        self.hover = hover
        fill = UI["hover"] if hover else (UI["panel2"] if self.active else UI["header"])
        self.itemconfig(self.bgrect, fill=fill)


def make_entry(parent, var, show=None, width=32):
    return tk.Entry(parent, textvariable=var, show=show, width=width, bg=UI["panel2"],
                    fg=UI["text"], insertbackground=UI["text"], relief="flat",
                    highlightthickness=1, highlightbackground=UI["border"],
                    highlightcolor=UI["accent"], font=(UI_FONT, 10))


def dark_menu(master):
    return tk.Menu(master, tearoff=0, bg=UI["panel2"], fg=UI["text"],
                   activebackground=UI["accent"], activeforeground="white",
                   bd=0, font=(UI_FONT, 9))


def dark_titlebar(win):
    """Windows 10/11'de pencere başlığını koyu yapar."""
    if os.name != "nt":
        return
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        val = ctypes.c_int(1)
        for attr in (20, 19):
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(val), ctypes.sizeof(val)) == 0:
                break
    except Exception:
        pass


# ---------------------------------------------------------------- pencereler
class Dialog(tk.Toplevel):
    def __init__(self, master, title):
        super().__init__(master)
        self.withdraw()
        self.title(title)
        self.configure(bg=UI["panel"])
        self.resizable(False, False)
        self.transient(master)
        self.result = None
        self.body = tk.Frame(self, bg=UI["panel"], padx=22, pady=18)
        self.body.pack(fill="both", expand=True)
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: self.ok())

    def heading(self, text, sub=None, icon=None):
        f = tk.Frame(self.body, bg=UI["panel"])
        f.pack(fill="x", pady=(0, 14))
        if icon:
            tk.Label(f, image=icon, bg=UI["panel"]).pack(side="left", padx=(0, 10))
        t = tk.Frame(f, bg=UI["panel"])
        t.pack(side="left")
        tk.Label(t, text=text, bg=UI["panel"], fg=UI["text"],
                 font=(UI_FONT, 13, "bold")).pack(anchor="w")
        if sub:
            tk.Label(t, text=sub, bg=UI["panel"], fg=UI["muted"],
                     font=(UI_FONT, 9)).pack(anchor="w")

    def label(self, parent, text):
        return tk.Label(parent, text=text, bg=UI["panel"], fg=UI["muted"], font=(UI_FONT, 9))

    def buttons(self, ok_text):
        f = tk.Frame(self.body, bg=UI["panel"])
        f.pack(fill="x", pady=(18, 0))
        FlatButton(f, ok_text, self.ok, bg=UI["accent"], hover=UI["accent_hover"],
                   fg="white", font=(UI_FONT, 10, "bold"), padx=18).pack(side="right")
        FlatButton(f, "İptal", self.destroy, padx=16).pack(side="right", padx=8)

    def ok(self):
        self.destroy()

    def show(self, focus=None):
        self.update_idletasks()
        m = self.master
        x = m.winfo_rootx() + (m.winfo_width() - self.winfo_reqwidth()) // 2
        y = m.winfo_rooty() + (m.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.deiconify()
        dark_titlebar(self)
        self.grab_set()
        if focus:
            focus.focus_set()
            focus.icursor("end")
        self.wait_window()
        return self.result


class InputDialog(Dialog):
    def __init__(self, master, title, prompt, initial="", hint=None):
        super().__init__(master, title)
        self.heading(title, hint)
        self.label(self.body, prompt).pack(anchor="w")
        self.var = tk.StringVar(value=initial)
        self.entry = make_entry(self.body, self.var, width=40)
        self.entry.pack(fill="x", ipady=5, pady=(4, 0))
        self.buttons("Tamam")

    def ok(self):
        self.result = self.var.get().strip()
        self.destroy()


class PasswordDialog(Dialog):
    def __init__(self, master, session, icon):
        super().__init__(master, "Bağlan")
        s = session
        self.heading(s["name"], f'{s["user"]}@{s["host"]}:{s.get("port", 22)}', icon)
        prompt = "Anahtar parolası (yoksa boş bırak)" if s.get("key") else "Şifre"
        self.label(self.body, prompt).pack(anchor="w")
        self.var = tk.StringVar()
        self.entry = make_entry(self.body, self.var, show="•", width=34)
        self.entry.pack(fill="x", ipady=5, pady=(4, 0))
        self.buttons("Bağlan")

    def ok(self):
        self.result = self.var.get()
        self.destroy()


class SessionDialog(Dialog):
    def __init__(self, master, session=None, default_color=None):
        super().__init__(master, "Oturum")
        s = session or {}
        self.heading("Yeni oturum" if not session else "Oturumu düzenle",
                     "SSH bağlantı bilgileri")
        self.vars = {
            "name": tk.StringVar(value=s.get("name", "")),
            "host": tk.StringVar(value=s.get("host", "")),
            "port": tk.StringVar(value=str(s.get("port", 22))),
            "user": tk.StringVar(value=s.get("user", "")),
            "key": tk.StringVar(value=s.get("key", "")),
        }
        self.color = s.get("color") or default_color or SESSION_COLORS[0]
        grid = tk.Frame(self.body, bg=UI["panel"])
        grid.pack(fill="x")
        rows = [("Oturum adı", "name"), ("Sunucu", "host"), ("Port", "port"),
                ("Kullanıcı", "user"), ("SSH anahtarı (isteğe bağlı)", "key")]
        first = None
        for i, (text, key) in enumerate(rows):
            self.label(grid, text).grid(row=i, column=0, sticky="w", pady=5, padx=(0, 12))
            e = make_entry(grid, self.vars[key], width=30)
            e.grid(row=i, column=1, sticky="ew", ipady=4)
            first = first or (e if key == "host" else None)
        FlatButton(grid, "Seç…", self._pick_key, padx=8, pady=3).grid(row=4, column=2, padx=(6, 0))

        self.label(grid, "Renk").grid(row=5, column=0, sticky="w", pady=(10, 0))
        sw = tk.Frame(grid, bg=UI["panel"])
        sw.grid(row=5, column=1, sticky="w", pady=(10, 0))
        self.swatches = []
        for c in SESSION_COLORS:
            cv = tk.Canvas(sw, width=24, height=24, bg=UI["panel"], highlightthickness=0,
                           cursor="hand2")
            cv.pack(side="left", padx=2)
            cv.bind("<Button-1>", lambda e, c=c: self._set_color(c))
            self.swatches.append((cv, c))
        self._set_color(self.color)
        self.buttons("Kaydet")
        self.first = first

    def _set_color(self, c):
        self.color = c
        for cv, col in self.swatches:
            cv.delete("all")
            if col == c:
                cv.create_oval(1, 1, 23, 23, outline="white", width=2)
            cv.create_oval(5, 5, 19, 19, fill=col, outline="")

    def _pick_key(self):
        p = filedialog.askopenfilename(title="SSH anahtarı seç", parent=self)
        if p:
            self.vars["key"].set(p)

    def ok(self):
        d = {k: v.get().strip() for k, v in self.vars.items()}
        if not d["host"] or not d["user"]:
            messagebox.showwarning(APP_NAME, "Sunucu ve kullanıcı zorunlu.", parent=self)
            return
        try:
            d["port"] = int(d["port"] or 22)
        except ValueError:
            messagebox.showwarning(APP_NAME, "Port sayı olmalı.", parent=self)
            return
        if not d["name"]:
            d["name"] = f'{d["user"]}@{d["host"]}'
        d["color"] = self.color
        self.result = d
        self.destroy()


# ---------------------------------------------------------------- terminal ekranı
class TermScreen(pyte.Screen):
    """pyte ekranı + geçmiş (scrollback) + alternatif ekran (vim/htop)."""

    def __init__(self, columns, lines, send):
        super().__init__(columns, lines)
        self.scrollback = collections.deque(maxlen=SCROLLBACK)
        self.in_alt = False
        self._saved = None
        self._send = send

    def write_process_input(self, data):
        self._send(data)

    def select_graphic_rendition(self, *attrs, private=False, **kwargs):
        if private:
            return
        super().select_graphic_rendition(*attrs)

    def index(self):
        top, bottom = self.margins or (0, self.lines - 1)
        if not self.in_alt and top == 0 and self.cursor.y == bottom:
            line = self.buffer[0]
            self.scrollback.append([line[x] for x in range(self.columns)])
        super().index()

    def set_mode(self, *modes, **kwargs):
        if kwargs.get("private") and any(m in ALT_SCREEN for m in modes) and not self.in_alt:
            self._saved = ({y: dict(self.buffer[y]) for y in range(self.lines)},
                           copy.copy(self.cursor))
            self.in_alt = True
            self.erase_in_display(2)
        super().set_mode(*modes, **kwargs)

    def reset_mode(self, *modes, **kwargs):
        super().reset_mode(*modes, **kwargs)
        if kwargs.get("private") and any(m in ALT_SCREEN for m in modes) and self.in_alt:
            self.in_alt = False
            buf, cur = self._saved
            for y in range(self.lines):
                self.buffer[y].clear()
                self.buffer[y].update(buf.get(y, {}))
            self.cursor = cur
            self.cursor.x = min(self.cursor.x, self.columns - 1)
            self.cursor.y = min(self.cursor.y, self.lines - 1)
            self.dirty.update(range(self.lines))


# ---------------------------------------------------------------- sekme
class TerminalTab(tk.Frame):
    """Bir SSH bağlantısı. Terminal sekmede, SFTP paneli sol tarafta."""

    def __init__(self, app, session, password):
        super().__init__(app.nb, bg=app.theme["bg"])
        self.app = app
        self.session = session
        self.password = password
        self.client = self.chan = self.sftp = None
        self.remote_dir = "."
        self.alive = True
        self.state = "connecting"
        self.status_text = "Bağlanıyor…"
        self.q = queue.Queue()
        self.screen = TermScreen(120, 40, self._send)
        self.stream = pyte.ByteStream(self.screen)
        self.offset = 0
        self.dirty = True
        self._tags = {}
        self._last_size = None

        self._build_terminal()
        self._build_sftp()
        threading.Thread(target=self._connect, daemon=True).start()
        self.after(30, self._poll)

    # ---------- terminal arayüzü
    def _build_terminal(self):
        size = self.app.settings["font_size"]
        self.font = tkfont.Font(family=MONO_FONT, size=size)
        self.font_bold = tkfont.Font(family=MONO_FONT, size=size, weight="bold")
        th = self.app.theme
        self.term = tk.Text(self, bg=th["bg"], fg=th["fg"], font=self.font, wrap="none",
                            undo=False, borderwidth=0, highlightthickness=0, padx=10, pady=8,
                            insertwidth=0, selectbackground="#3a5a8c", selectforeground="white",
                            cursor="xterm")
        self.term.pack(fill="both", expand=True)
        self.term.tag_configure("cursor", background=th["cursor"], foreground=th["bg"])

        t = self.term
        t.bind("<Key>", self._on_key)
        t.bind("<Control-C>", self._copy)
        t.bind("<Control-V>", self._paste)
        t.bind("<Control-N>", lambda e: (self.app.quick_connect(), "break")[1])
        t.bind("<Control-W>", lambda e: (self.app.close_tab(self), "break")[1])
        t.bind("<Control-Tab>", lambda e: (self.app.next_tab(), "break")[1])
        t.bind("<Shift-Prior>", lambda e: self._scroll(self.screen.lines // 2))
        t.bind("<Shift-Next>", lambda e: self._scroll(-(self.screen.lines // 2)))
        t.bind("<Button-3>", self._right_click)
        t.bind("<<Paste>>", self._paste)
        t.bind("<MouseWheel>", self._on_wheel)
        t.bind("<Control-MouseWheel>", lambda e: (self.app.zoom(1 if e.delta > 0 else -1), "break")[1])
        t.bind("<Button-4>", lambda e: self._wheel_step(1))
        t.bind("<Button-5>", lambda e: self._wheel_step(-1))
        t.bind("<Configure>", self._on_resize)
        t.focus_set()

    def apply_theme(self):
        th = self.app.theme
        self.configure(bg=th["bg"])
        self.term.configure(bg=th["bg"], fg=th["fg"])
        self.term.tag_configure("cursor", background=th["cursor"], foreground=th["bg"])
        for name in self._tags.values():
            self.term.tag_delete(name)
        self._tags.clear()
        self.dirty = True

    def apply_font(self):
        size = self.app.settings["font_size"]
        self.font.configure(size=size)
        self.font_bold.configure(size=size)
        self._last_size = None
        self.after(20, self._on_resize)

    # ---------- SFTP arayüzü (sol panelde gösterilir)
    def _build_sftp(self):
        f = self.sftp_frame = tk.Frame(self.app.sftp_holder, bg=UI["panel"])
        bar = tk.Frame(f, bg=UI["panel"])
        bar.pack(fill="x", padx=8, pady=(8, 4))
        for glyph, tip, cmd in [("⬆", "Üst klasör", self.sftp_up),
                                ("⟳", "Yenile", self.sftp_refresh),
                                ("⤒", "Yükle", self.sftp_upload),
                                ("⤓", "İndir", self.sftp_download),
                                ("＋", "Yeni klasör", self.sftp_mkdir),
                                ("🗑", "Sil", self.sftp_delete),
                                ("⌂", "Terminali bu klasöre götür", self.sftp_cd_here)]:
            FlatButton(bar, glyph, cmd, font=(UI_FONT, 11), padx=7, pady=2,
                       tooltip=tip).pack(side="left", padx=1)

        self.path_var = tk.StringVar()
        pe = make_entry(f, self.path_var)
        pe.pack(fill="x", padx=8, pady=(2, 6), ipady=3)
        pe.bind("<Return>", lambda e: self.sftp_go(self.path_var.get()))

        tf = tk.Frame(f, bg=UI["panel"])
        tf.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tf, columns=("size", "date"), selectmode="extended",
                                 style="Side.Treeview")
        self.tree.heading("#0", text="Ad", anchor="w")
        self.tree.heading("size", text="Boyut", anchor="e")
        self.tree.heading("date", text="Tarih", anchor="w")
        self.tree.column("#0", width=140, minwidth=90)
        self.tree.column("size", width=64, anchor="e", stretch=False)
        self.tree.column("date", width=104, stretch=False)
        ysb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        ysb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self._on_tree_double)
        self.tree.bind("<Button-3>", self._tree_menu)

        self.sftp_info = tk.Label(f, text="", bg=UI["panel"], fg=UI["muted"],
                                  font=(UI_FONT, 8), anchor="w")
        self.sftp_info.pack(fill="x", padx=8, pady=4)

    # ---------- durum
    def set_status(self, text, state=None):
        self.status_text = text
        if state:
            self.state = state
        self.app.on_tab_status(self)

    # ---------- bağlantı (arka plan)
    def _open_client(self):
        s = self.session
        c = paramiko.SSHClient()
        try:
            c.load_system_host_keys()
        except Exception:
            pass
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(hostname=s["host"], port=int(s.get("port", 22)), username=s["user"],
                  password=self.password or None, key_filename=s.get("key") or None,
                  passphrase=(self.password or None) if s.get("key") else None,
                  timeout=15, allow_agent=True, look_for_keys=not self.password)
        return c

    def _connect(self):
        try:
            self.client = self._open_client()
            self.chan = self.client.invoke_shell(term="xterm-256color",
                                                 width=self.screen.columns,
                                                 height=self.screen.lines)
            try:
                self.sftp = self.client.open_sftp()
                self.remote_dir = self.sftp.normalize(".")
            except Exception:
                self.sftp = None
            s = self.session
            self.q.put(("status", ("ok", f'{s["user"]}@{s["host"]}:{s.get("port", 22)}')))
            self.q.put(("refresh", None))
            self.q.put(("resize", None))
            while self.alive:
                data = self.chan.recv(32768)
                if not data:
                    break
                self.q.put(("data", data))
            self.q.put(("closed", None))
        except Exception as e:
            self.q.put(("error", str(e)))

    def _poll(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "data":
                    try:
                        self.stream.feed(val)
                    except Exception:
                        pass
                    self.dirty = True
                elif kind == "status":
                    state, text = val
                    self.set_status(text, state)
                    if state == "ok":
                        self.app.on_connected(self)
                elif kind == "info":
                    self.sftp_info.config(text=val)
                elif kind == "refresh":
                    self.sftp_refresh()
                elif kind == "resize":
                    self._last_size = None
                    self._on_resize()
                elif kind == "closed" and self.alive:
                    self.set_status("Bağlantı kapandı", "closed")
                    self._message("[Bağlantı kapandı — sekmeye sağ tıklayıp yeniden bağlanabilirsin]")
                elif kind == "error":
                    self.set_status("Hata: " + val, "error")
                    self._message("[Bağlantı hatası] " + val)
        except queue.Empty:
            pass
        if self.dirty:
            self.dirty = False
            try:
                self._render()
            except Exception:
                pass
        if self.alive:
            self.after(30, self._poll)

    def _message(self, text):
        self.stream.feed(("\r\n\x1b[1;33m" + text + "\x1b[0m\r\n").encode("utf-8"))
        self.dirty = True

    # ---------- ekran çizimi
    def _tag_for(self, ch):
        th = self.app.theme
        pal = self.app.palette
        fg = resolve_color(ch.fg, th["fg"], pal, ch.bold)
        bg = resolve_color(ch.bg, th["bg"], pal)
        if ch.reverse:
            fg, bg = bg, fg
        key = (fg, bg, ch.bold, ch.underscore)
        if key == (th["fg"], th["bg"], False, False):
            return ()
        name = self._tags.get(key)
        if name is None:
            name = f"c{len(self._tags)}"
            self._tags[key] = name
            self.term.tag_configure(name, foreground=fg, background=bg,
                                    font=self.font_bold if ch.bold else self.font,
                                    underline=ch.underscore)
            self.term.tag_raise("cursor")
        return (name,)

    def _render(self):
        sc = self.screen
        rows, cols = sc.lines, sc.columns
        sb = sc.scrollback
        self.offset = min(self.offset, len(sb))
        view = []
        if self.offset:
            start = len(sb) - self.offset
            for i in range(start, min(start + rows, len(sb))):
                view.append(sb[i])
        for y in range(rows - len(view)):
            line = sc.buffer[y]
            view.append([line[x] for x in range(cols)])

        cur_y = sc.cursor.y + self.offset
        show_cursor = self.offset == 0 and pyte.modes.DECTCEM in sc.mode

        args = []
        for y, line in enumerate(view):
            line = line[:cols]
            end = len(line)
            while end > 0 and line[end - 1].data in (" ", "") and not self._tag_for(line[end - 1]):
                end -= 1
            if y == cur_y and show_cursor:
                end = max(end, sc.cursor.x + 1)
            run, run_tag = [], None
            for x in range(end):
                ch = line[x] if x < len(line) else sc.default_char
                tag = self._tag_for(ch)
                if tag != run_tag and run:
                    args += ["".join(run), run_tag]
                    run = []
                run_tag = tag
                run.append(ch.data or "")
            if run:
                args += ["".join(run), run_tag]
            if y < len(view) - 1:
                args += ["\n", ()]

        t = self.term
        try:
            sel = (t.index("sel.first"), t.index("sel.last"))
        except tk.TclError:
            sel = None
        t.delete("1.0", "end")
        if args:
            t.insert("end", *args)
        if show_cursor and 0 <= cur_y < rows:
            line_text = t.get(f"{cur_y + 1}.0", f"{cur_y + 1}.end")
            x = sc.cursor.x
            if len(line_text) < x + 1:
                t.insert(f"{cur_y + 1}.end", " " * (x + 1 - len(line_text)))
            t.tag_add("cursor", f"{cur_y + 1}.{x}", f"{cur_y + 1}.{x + 1}")
        if sel:
            t.tag_add("sel", *sel)

    # ---------- klavye / fare
    def _send(self, s):
        if self.chan and not self.chan.closed:
            try:
                self.chan.send(s)
            except Exception:
                pass

    def _on_key(self, e):
        if e.keysym in MODIFIER_KEYS:
            return "break"
        seq = None
        if DECCKM in self.screen.mode:
            seq = APP_CURSOR.get(e.keysym)
        if seq is None:
            seq = KEYMAP.get(e.keysym)
        if seq is None:
            seq = e.char
            if seq and (e.state & 0x8) and os.name != "nt":
                seq = "\x1b" + seq      # Alt+tuş (Linux)
        if seq:
            if self.offset:
                self.offset = 0
                self.dirty = True
                self.app.refresh_status()
            self._send(seq)
        return "break"

    def _scroll(self, n):
        if self.screen.in_alt:
            return "break"
        self.offset = max(0, min(len(self.screen.scrollback), self.offset + n))
        self.dirty = True
        self.app.refresh_status()
        return "break"

    def _wheel_step(self, direction):
        if self.screen.in_alt:
            key = "Up" if direction > 0 else "Down"
            seq = (APP_CURSOR if DECCKM in self.screen.mode else KEYMAP)[key]
            self._send(seq * 3)
            return "break"
        return self._scroll(3 * direction)

    def _on_wheel(self, e):
        return self._wheel_step(1 if e.delta > 0 else -1)

    def _copy(self, e=None):
        try:
            txt = self.term.get("sel.first", "sel.last")
            self.clipboard_clear()
            self.clipboard_append(txt)
        except tk.TclError:
            pass
        return "break"

    def _paste(self, e=None):
        try:
            txt = self.clipboard_get()
        except tk.TclError:
            return "break"
        txt = txt.replace("\r\n", "\r").replace("\n", "\r")
        if BRACKETED_PASTE in self.screen.mode:
            txt = "\x1b[200~" + txt + "\x1b[201~"
        self._send(txt)
        return "break"

    def _right_click(self, e):
        if self.term.tag_ranges("sel"):
            self._copy()
            self.term.tag_remove("sel", "1.0", "end")
        else:
            self._paste()
        return "break"

    def _on_resize(self, e=None):
        w = self.term.winfo_width() - 22
        h = self.term.winfo_height() - 18
        if w < 50 or h < 30:
            return
        cols = max(20, w // max(1, self.font.measure("M")))
        rows = max(5, h // max(1, self.font.metrics("linespace")))
        if (cols, rows) == self._last_size:
            return
        self._last_size = (cols, rows)
        self.screen.resize(lines=rows, columns=cols)
        self.dirty = True
        if self.chan:
            try:
                self.chan.resize_pty(width=cols, height=rows)
            except Exception:
                pass
        self.app.refresh_status()

    # ---------- SFTP işlemleri
    def _need_sftp(self):
        if not self.sftp:
            messagebox.showinfo(APP_NAME, "SFTP bağlantısı yok.")
            return False
        return True

    def sftp_refresh(self):
        if not self.sftp:
            return
        self.tree.delete(*self.tree.get_children())
        self.path_var.set(self.remote_dir)
        try:
            items = self.sftp.listdir_attr(self.remote_dir)
        except Exception as e:
            self.sftp_info.config(text=f"Klasör okunamadı: {e}")
            return
        items.sort(key=lambda a: (not stat.S_ISDIR(a.st_mode or 0), a.filename.lower()))
        icons = self.app.icons
        n_dir = n_file = 0
        for a in items:
            mode = a.st_mode or 0
            is_dir = stat.S_ISDIR(mode)
            if is_dir:
                img, n_dir = icons["folder"], n_dir + 1
            elif stat.S_ISLNK(mode):
                img, n_file = icons["link"], n_file + 1
            else:
                img, n_file = icons["file"], n_file + 1
            date = time.strftime("%d.%m.%y %H:%M", time.localtime(a.st_mtime)) if a.st_mtime else ""
            size = "" if is_dir else human_size(a.st_size or 0)
            self.tree.insert("", "end", iid=a.filename, text=" " + a.filename, image=img,
                             values=(size, date), tags=("dir" if is_dir else "file",))
        self.sftp_info.config(text=f"{n_dir} klasör, {n_file} dosya")

    def sftp_go(self, path):
        if not self._need_sftp():
            return
        try:
            new = self.sftp.normalize(path)
            self.sftp.listdir(new)
            self.remote_dir = new
            self.sftp_refresh()
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Klasör açılamadı:\n{e}")

    def sftp_up(self):
        self.sftp_go(posixpath.dirname(self.remote_dir.rstrip("/")) or "/")

    def sftp_cd_here(self):
        path = self.remote_dir.replace("'", "'\\''")
        self._send(f"cd '{path}'\r")
        self.term.focus_set()

    def _on_tree_double(self, e):
        iid = self.tree.focus()
        if not iid:
            return
        if "dir" in self.tree.item(iid, "tags"):
            self.sftp_go(posixpath.join(self.remote_dir, iid))
        else:
            self.sftp_download()

    def _tree_menu(self, e):
        iid = self.tree.identify_row(e.y)
        if iid and iid not in self.tree.selection():
            self.tree.selection_set(iid)
        m = dark_menu(self)
        m.add_command(label="İndir", command=self.sftp_download)
        m.add_command(label="Yükle…", command=self.sftp_upload)
        m.add_separator()
        m.add_command(label="Yeni klasör", command=self.sftp_mkdir)
        m.add_command(label="Sil", command=self.sftp_delete)
        m.add_separator()
        m.add_command(label="Yenile", command=self.sftp_refresh)
        m.tk_popup(e.x_root, e.y_root)

    def _bg(self, work, done_text):
        def run():
            try:
                sftp = self.client.open_sftp()
                try:
                    work(sftp)
                finally:
                    sftp.close()
                self.q.put(("info", done_text))
            except Exception as ex:
                self.q.put(("info", f"Hata: {ex}"))
            self.q.put(("refresh", None))
        threading.Thread(target=run, daemon=True).start()

    def sftp_upload(self):
        if not self._need_sftp():
            return
        files = filedialog.askopenfilenames(title="Yüklenecek dosyalar")
        if not files:
            return
        target = self.remote_dir

        def work(sftp):
            for i, f in enumerate(files, 1):
                name = os.path.basename(f)
                self.q.put(("info", f"Yükleniyor ({i}/{len(files)}): {name}"))
                sftp.put(f, posixpath.join(target, name))
        self._bg(work, f"Yükleme bitti ({len(files)} dosya).")

    def sftp_download(self):
        if not self._need_sftp():
            return
        sel = [i for i in self.tree.selection() if "file" in self.tree.item(i, "tags")]
        if not sel:
            messagebox.showinfo(APP_NAME, "İndirmek için dosya seç (klasörler indirilmez).")
            return
        dest = filedialog.askdirectory(title="Nereye indirilsin?")
        if not dest:
            return
        src = self.remote_dir

        def work(sftp):
            for i, name in enumerate(sel, 1):
                self.q.put(("info", f"İndiriliyor ({i}/{len(sel)}): {name}"))
                sftp.get(posixpath.join(src, name), os.path.join(dest, name))
        self._bg(work, f"İndirme bitti: {dest}")

    def sftp_mkdir(self):
        if not self._need_sftp():
            return
        name = InputDialog(self.app, "Yeni klasör", "Klasör adı").show()
        if name:
            try:
                self.sftp.mkdir(posixpath.join(self.remote_dir, name))
                self.sftp_refresh()
            except Exception as e:
                messagebox.showerror(APP_NAME, str(e))

    def sftp_delete(self):
        if not self._need_sftp():
            return
        sel = self.tree.selection()
        if not sel:
            return
        if not messagebox.askyesno(APP_NAME, "Seçilenler silinsin mi?\n" + "\n".join(sel)):
            return
        for name in sel:
            path = posixpath.join(self.remote_dir, name)
            try:
                if "dir" in self.tree.item(name, "tags"):
                    self.sftp.rmdir(path)
                else:
                    self.sftp.remove(path)
            except Exception as e:
                messagebox.showerror(APP_NAME, f"{name} silinemedi:\n{e}")
        self.sftp_refresh()

    # ---------- kapat
    def close(self):
        self.alive = False
        for obj in (self.sftp, self.chan, self.client):
            try:
                if obj:
                    obj.close()
            except Exception:
                pass
        self.sftp_frame.destroy()


# ---------------------------------------------------------------- ana pencere
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        global UI_FONT, MONO_FONT
        UI_FONT = pick_font(["Segoe UI", "Inter", "Ubuntu", "Noto Sans", "DejaVu Sans"], "TkDefaultFont")
        MONO_FONT = pick_font(["Cascadia Mono", "Cascadia Code", "Consolas", "JetBrains Mono",
                               "DejaVu Sans Mono", "Courier New"], "TkFixedFont")

        self.title(f"{APP_NAME} {VERSION}")
        self.geometry("1280x780")
        self.minsize(900, 520)
        self.configure(bg=UI["bg"])
        self.sessions = load_json(SESSIONS_FILE, [])
        self.settings = {"theme": "Gece", "font_size": 11}
        self.settings.update(load_json(SETTINGS_FILE, {}))
        if self.settings["theme"] not in THEMES:
            self.settings["theme"] = "Gece"
        self._set_theme_vars()

        self.icons = {"folder": icon_folder(), "file": icon_file(), "link": icon_link(),
                      "app": icon_app()}
        self.dots = {k: icon_dot(c) for k, c in STATE_COLORS.items()}
        self.monitors = {}
        self.iconphoto(True, self.icons["app"])

        self._style()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._quit)
        self.bind_all("<Control-n>", lambda e: self.quick_connect())
        dark_titlebar(self)

    # ---------- tema / stil
    def _set_theme_vars(self):
        self.theme = THEMES[self.settings["theme"]]
        self.palette = theme_palette(self.theme)

    def monitor(self, color):
        if color not in self.monitors:
            self.monitors[color] = icon_monitor(color)
        return self.monitors[color]

    def _style(self):
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure(".", background=UI["panel"], foreground=UI["text"],
                     fieldbackground=UI["panel2"], bordercolor=UI["border"],
                     lightcolor=UI["panel"], darkcolor=UI["panel"], troughcolor=UI["bg"],
                     focuscolor=UI["accent"], font=(UI_FONT, 9))
        st.configure("Side.Treeview", background=UI["panel"], fieldbackground=UI["panel"],
                     foreground=UI["text"], rowheight=24, borderwidth=0, font=(UI_FONT, 9))
        st.map("Side.Treeview", background=[("selected", UI["select"])],
               foreground=[("selected", "white")])
        st.configure("Side.Treeview.Heading", background=UI["panel2"], foreground=UI["muted"],
                     relief="flat", borderwidth=0, font=(UI_FONT, 8, "bold"))
        st.map("Side.Treeview.Heading", background=[("active", UI["hover"])])
        st.layout("Side.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        st.configure("Vertical.TScrollbar", background=UI["panel2"], troughcolor=UI["panel"],
                     bordercolor=UI["panel"], arrowcolor=UI["muted"], lightcolor=UI["panel2"],
                     darkcolor=UI["panel2"], gripcount=0, arrowsize=12)
        st.map("Vertical.TScrollbar", background=[("active", UI["hover"])])
        st.configure("Term.TNotebook", background=UI["bg"], borderwidth=0,
                     tabmargins=(6, 6, 6, 0), lightcolor=UI["bg"], darkcolor=UI["bg"],
                     bordercolor=UI["bg"])
        st.configure("Term.TNotebook.Tab", background=UI["panel"], foreground=UI["muted"],
                     padding=(14, 7), borderwidth=0, lightcolor=UI["panel"],
                     darkcolor=UI["panel"], bordercolor=UI["bg"], font=(UI_FONT, 9))
        st.map("Term.TNotebook.Tab",
               background=[("selected", UI["panel2"]), ("active", UI["hover"])],
               foreground=[("selected", UI["text"]), ("active", UI["text"])],
               lightcolor=[("selected", UI["accent"])],
               padding=[("selected", (14, 7))], expand=[("selected", (0, 0, 0, 0))])
        st.configure("TPanedwindow", background=UI["border"])
        st.configure("Sash", sashthickness=3, gripcount=0, background=UI["border"],
                     lightcolor=UI["border"], bordercolor=UI["border"])

    # ---------- arayüz
    def _build(self):
        self._build_header()
        tk.Frame(self, bg=UI["border"], height=1).pack(fill="x")
        self._build_statusbar()

        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(paned, bg=UI["panel"], width=330)
        paned.add(self.sidebar, weight=0)
        self.main = tk.Frame(paned, bg=UI["bg"])
        paned.add(self.main, weight=1)
        self.after(60, lambda: paned.sashpos(0, 330))

        self._build_sidebar()
        self.nb = ttk.Notebook(self.main, style="Term.TNotebook")
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self._on_tab_changed())
        self.nb.bind("<Button-2>", self._middle_close)
        self.nb.bind("<Button-3>", self._tab_menu)
        self.home = tk.Frame(self.main, bg=UI["bg"])
        self._build_home()
        self._update_main()
        self.show_side("sessions")

    def _build_header(self):
        h = tk.Frame(self, bg=UI["header"])
        h.pack(fill="x")
        logo = tk.Canvas(h, width=170, height=66, bg=UI["header"], highlightthickness=0)
        logo.pack(side="left", padx=(12, 6))
        round_rect(logo, 4, 15, 40, 51, 10, fill=UI["accent"], outline="")
        logo.create_text(22, 33, text=">_", fill="white", font=(MONO_FONT, 13, "bold"))
        logo.create_text(50, 27, text=APP_NAME, anchor="w", fill=UI["text"],
                         font=(UI_FONT, 15, "bold"))
        logo.create_text(51, 46, text=f"SSH · SFTP · {VERSION}", anchor="w",
                         fill=UI["muted"], font=(UI_FONT, 8))
        tk.Frame(h, bg=UI["border"], width=1).pack(side="left", fill="y", pady=12, padx=6)

        tools = [("Oturum", "+", "#2ea043", self.new_session),
                 ("Hızlı bağlan", "⚡", "#d29922", self.quick_connect),
                 ("Çoğalt", "⧉", "#2f81f7", self.duplicate_tab),
                 ("Yeniden", "↻", "#1f9bd1", self.reconnect_tab),
                 ("Kapat", "✕", "#e5534b", self.close_tab)]
        for label, glyph, color, cmd in tools:
            ToolButton(h, label, glyph, color, cmd).pack(side="left", padx=1, pady=4)
        tk.Frame(h, bg=UI["border"], width=1).pack(side="left", fill="y", pady=12, padx=6)
        self.btn_sessions = ToolButton(h, "Oturumlar", "☰", "#db61a2",
                                       lambda: self.show_side("sessions"))
        self.btn_sessions.pack(side="left", padx=1, pady=4)
        self.btn_sftp = ToolButton(h, "SFTP", "⇅", "#8957e5", lambda: self.show_side("sftp"))
        self.btn_sftp.pack(side="left", padx=1, pady=4)
        tk.Frame(h, bg=UI["border"], width=1).pack(side="left", fill="y", pady=12, padx=6)
        for label, glyph, color, cmd in [("Tema", "◐", "#e8853d", self.next_theme),
                                         ("Yazı +", "A+", "#3fb950", lambda: self.zoom(1)),
                                         ("Yazı −", "A−", "#6e7681", lambda: self.zoom(-1))]:
            ToolButton(h, label, glyph, color, cmd).pack(side="left", padx=1, pady=4)

    def _build_statusbar(self):
        s = self.statusbar = tk.Frame(self, bg=UI["status"], height=26)
        s.pack(side="bottom", fill="x")
        self.st_state = tk.Label(s, text="", bg=UI["status"], fg="white",
                                 font=(UI_FONT, 8, "bold"), padx=10)
        self.st_state.pack(side="left", fill="y")
        self.st_text = tk.Label(s, text="", bg=UI["status"], fg=UI["muted"],
                                font=(UI_FONT, 8), padx=10)
        self.st_text.pack(side="left")
        self.st_theme = tk.Label(s, text="", bg=UI["status"], fg=UI["muted"],
                                 font=(UI_FONT, 8), padx=10)
        self.st_theme.pack(side="right")
        self.st_size = tk.Label(s, text="", bg=UI["status"], fg=UI["muted"],
                                font=(UI_FONT, 8), padx=10)
        self.st_size.pack(side="right")

    def _build_sidebar(self):
        sb = self.sidebar
        seg = tk.Frame(sb, bg=UI["panel"])
        seg.pack(fill="x")
        self.seg_btns = {}
        for key, text in (("sessions", "Oturumlar"), ("sftp", "SFTP")):
            f = tk.Frame(seg, bg=UI["panel"], cursor="hand2")
            f.pack(side="left", expand=True, fill="x")
            lbl = tk.Label(f, text=text, bg=UI["panel"], fg=UI["muted"],
                           font=(UI_FONT, 10, "bold"), pady=9)
            lbl.pack(fill="x")
            bar = tk.Frame(f, bg=UI["panel"], height=3)
            bar.pack(fill="x")
            for w in (f, lbl):
                w.bind("<Button-1>", lambda e, k=key: self.show_side(k))
            self.seg_btns[key] = (lbl, bar)
        tk.Frame(sb, bg=UI["border"], height=1).pack(fill="x")

        # oturumlar görünümü
        sv = self.sessions_view = tk.Frame(sb, bg=UI["panel"])
        top = tk.Frame(sv, bg=UI["panel"])
        top.pack(fill="x", padx=10, pady=(10, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._refresh_sessions())
        se = make_entry(top, self.search_var)
        se.pack(fill="x", ipady=5)
        self._placeholder(se, "🔍  Oturum ara…")

        holder = tk.Frame(sv, bg=UI["panel"])
        holder.pack(fill="both", expand=True)
        self.list_canvas = tk.Canvas(holder, bg=UI["panel"], highlightthickness=0, bd=0)
        vsb = ttk.Scrollbar(holder, orient="vertical", command=self.list_canvas.yview)
        self.list_canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.list_canvas.pack(side="left", fill="both", expand=True)
        self.list_frame = tk.Frame(self.list_canvas, bg=UI["panel"])
        win = self.list_canvas.create_window(0, 0, window=self.list_frame, anchor="nw")
        self.list_frame.bind("<Configure>", lambda e: self.list_canvas.configure(
            scrollregion=self.list_canvas.bbox("all")))
        self.list_canvas.bind("<Configure>", lambda e: self.list_canvas.itemconfig(win, width=e.width))
        for w in (self.list_canvas, self.list_frame):
            w.bind("<MouseWheel>", self._list_wheel)
            w.bind("<Button-4>", lambda e: self.list_canvas.yview_scroll(-2, "units"))
            w.bind("<Button-5>", lambda e: self.list_canvas.yview_scroll(2, "units"))

        btns = tk.Frame(sv, bg=UI["panel"])
        btns.pack(fill="x", padx=10, pady=10)
        FlatButton(btns, "+  Yeni oturum", self.new_session, bg=UI["accent"],
                   hover=UI["accent_hover"], fg="white",
                   font=(UI_FONT, 9, "bold")).pack(side="left", expand=True, fill="x")
        FlatButton(btns, "⚡", self.quick_connect, padx=10,
                   tooltip="Hızlı bağlan").pack(side="left", padx=(6, 0))
        self.selected_session = None

        # SFTP görünümü
        self.sftp_holder = tk.Frame(sb, bg=UI["panel"])
        self.sftp_empty = tk.Label(self.sftp_holder, bg=UI["panel"], fg=UI["muted"],
                                   font=(UI_FONT, 10), justify="center",
                                   text="⇅\n\nSFTP için bir\noturuma bağlan.")
        self._refresh_sessions()

    def _placeholder(self, entry, text):
        def show(e=None):
            if not self.search_var.get():
                entry.config(fg=UI["muted"])
                entry.delete(0, "end")
                entry.insert(0, text)
                entry._ph = True

        def hide(e=None):
            if getattr(entry, "_ph", False):
                entry._ph = False
                entry.delete(0, "end")
                entry.config(fg=UI["text"])
        entry.bind("<FocusIn>", hide)
        entry.bind("<FocusOut>", show)
        self._ph_text = text
        show()

    def _list_wheel(self, e):
        self.list_canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")

    def _build_home(self):
        for w in self.home.winfo_children():
            w.destroy()
        card = tk.Frame(self.home, bg=UI["bg"])
        card.place(relx=0.5, rely=0.42, anchor="center")
        cv = tk.Canvas(card, width=96, height=96, bg=UI["bg"], highlightthickness=0)
        cv.pack()
        round_rect(cv, 4, 4, 92, 92, 24, fill=UI["accent"], outline="")
        cv.create_text(48, 48, text=">_", fill="white", font=(MONO_FONT, 30, "bold"))
        tk.Label(card, text=APP_NAME, bg=UI["bg"], fg=UI["text"],
                 font=(UI_FONT, 26, "bold")).pack(pady=(12, 0))
        tk.Label(card, text="Ücretsiz SSH terminali ve SFTP dosya yöneticisi",
                 bg=UI["bg"], fg=UI["muted"], font=(UI_FONT, 11)).pack()
        b = tk.Frame(card, bg=UI["bg"])
        b.pack(pady=20)
        FlatButton(b, "+  Yeni oturum", self.new_session, bg=UI["accent"],
                   hover=UI["accent_hover"], fg="white", font=(UI_FONT, 11, "bold"),
                   padx=22, pady=9).pack(side="left", padx=6)
        FlatButton(b, "⚡  Hızlı bağlan", self.quick_connect, font=(UI_FONT, 11),
                   padx=22, pady=9).pack(side="left", padx=6)

        recent = sorted(self.sessions, key=lambda s: s.get("last", 0), reverse=True)[:6]
        if recent:
            tk.Label(card, text="SON OTURUMLAR", bg=UI["bg"], fg=UI["muted"],
                     font=(UI_FONT, 8, "bold")).pack(anchor="w", pady=(10, 6))
            grid = tk.Frame(card, bg=UI["bg"])
            grid.pack()
            for i, s in enumerate(recent):
                self._home_card(grid, s).grid(row=i // 3, column=i % 3, padx=5, pady=5)

    def _home_card(self, parent, s):
        c = tk.Frame(parent, bg=UI["card"], cursor="hand2", width=210, height=60)
        c.pack_propagate(False)
        tk.Frame(c, bg=s.get("color", UI["accent"]), width=4).pack(side="left", fill="y")
        icon = tk.Label(c, image=self.monitor(s.get("color", UI["accent"])), bg=UI["card"])
        icon.pack(side="left", padx=10)
        t = tk.Frame(c, bg=UI["card"])
        t.pack(side="left", fill="both", expand=True, pady=10)
        n = tk.Label(t, text=s["name"], bg=UI["card"], fg=UI["text"], anchor="w",
                     font=(UI_FONT, 10, "bold"))
        n.pack(fill="x")
        a = tk.Label(t, text=f'{s["user"]}@{s["host"]}', bg=UI["card"], fg=UI["muted"],
                     anchor="w", font=(UI_FONT, 8))
        a.pack(fill="x")
        widgets = (c, icon, t, n, a)

        def paint(col):
            for w in widgets:
                w.config(bg=col)
        for w in widgets:
            w.bind("<Enter>", lambda e: paint(UI["hover"]))
            w.bind("<Leave>", lambda e: paint(UI["card"]))
            w.bind("<ButtonRelease-1>", lambda e, s=s: self.open_tab(s))
        return c

    # ---------- oturum listesi
    def _refresh_sessions(self):
        if not hasattr(self, "list_frame"):
            return
        for w in self.list_frame.winfo_children():
            w.destroy()
        q = self.search_var.get().strip().lower()
        if q == getattr(self, "_ph_text", "").lower():
            q = ""
        shown = [s for s in self.sessions
                 if not q or q in s["name"].lower() or q in s["host"].lower()]
        if not shown:
            tk.Label(self.list_frame, bg=UI["panel"], fg=UI["muted"], font=(UI_FONT, 9),
                     text="Kayıtlı oturum yok.\n„Yeni oturum“ ile ekle." if not q
                     else "Sonuç yok.", justify="center").pack(pady=30)
        for s in shown:
            self._session_row(s)

    def _session_row(self, s):
        color = s.get("color", UI["accent"])
        sel = s is self.selected_session
        bg = UI["select"] if sel else UI["panel"]
        row = tk.Frame(self.list_frame, bg=bg, cursor="hand2")
        row.pack(fill="x", padx=6, pady=1)
        stripe = tk.Frame(row, bg=color if sel else bg, width=3)
        stripe.pack(side="left", fill="y")
        icon = tk.Label(row, image=self.monitor(color), bg=bg)
        icon.pack(side="left", padx=(8, 8), pady=7)
        t = tk.Frame(row, bg=bg)
        t.pack(side="left", fill="x", expand=True)
        n = tk.Label(t, text=s["name"], bg=bg, fg=UI["text"], anchor="w",
                     font=(UI_FONT, 10, "bold"))
        n.pack(fill="x")
        a = tk.Label(t, text=f'{s["user"]}@{s["host"]}:{s.get("port", 22)}', bg=bg,
                     fg=UI["muted"], anchor="w", font=(UI_FONT, 8))
        a.pack(fill="x")
        widgets = (row, icon, t, n, a)

        def paint(col):
            for w in widgets:
                w.config(bg=col)
            if not sel:
                stripe.config(bg=col)

        def select(e):
            self.selected_session = s
            self._refresh_sessions()
        for w in widgets + (stripe,):
            w.bind("<Enter>", lambda e: paint(UI["select"] if sel else UI["hover"]))
            w.bind("<Leave>", lambda e: paint(bg))
            w.bind("<Button-1>", select)
            w.bind("<Double-1>", lambda e: self.open_tab(s))
            w.bind("<Button-3>", lambda e: self._session_menu(e, s))
            w.bind("<MouseWheel>", self._list_wheel)
            w.bind("<Button-4>", lambda e: self.list_canvas.yview_scroll(-2, "units"))
            w.bind("<Button-5>", lambda e: self.list_canvas.yview_scroll(2, "units"))

    def _session_menu(self, e, s):
        self.selected_session = s
        self._refresh_sessions()
        m = dark_menu(self)
        m.add_command(label="Bağlan", command=lambda: self.open_tab(s))
        m.add_command(label="Düzenle", command=lambda: self.edit_session(s))
        m.add_command(label="Kopyasını oluştur", command=lambda: self.copy_session(s))
        m.add_separator()
        m.add_command(label="Sil", command=lambda: self.delete_session(s))
        m.tk_popup(e.x_root, e.y_root)

    def _save_sessions(self):
        save_json(SESSIONS_FILE, self.sessions)
        self._refresh_sessions()
        self._build_home()

    def new_session(self):
        color = SESSION_COLORS[len(self.sessions) % len(SESSION_COLORS)]
        dlg = SessionDialog(self, default_color=color)
        d = dlg.show(dlg.first)
        if d:
            self.sessions.append(d)
            self.selected_session = d
            self._save_sessions()

    def edit_session(self, s):
        dlg = SessionDialog(self, s)
        d = dlg.show(dlg.first)
        if d:
            d["last"] = s.get("last", 0)
            self.sessions[self.sessions.index(s)] = d
            self.selected_session = d
            self._save_sessions()

    def copy_session(self, s):
        d = dict(s, name=s["name"] + " (kopya)", last=0)
        self.sessions.insert(self.sessions.index(s) + 1, d)
        self._save_sessions()

    def delete_session(self, s):
        if messagebox.askyesno(APP_NAME, f'"{s["name"]}" silinsin mi?'):
            self.sessions.remove(s)
            self._save_sessions()

    def quick_connect(self):
        dlg = InputDialog(self, "Hızlı bağlan", "kullanici@sunucu[:port]",
                          hint="Kaydetmeden hemen bağlan")
        txt = dlg.show(dlg.entry)
        if not txt or "@" not in txt:
            return
        user, rest = txt.split("@", 1)
        host, _, port = rest.partition(":")
        self.open_tab({"name": txt, "host": host, "user": user, "color": UI["accent"],
                       "port": int(port) if port.isdigit() else 22, "key": ""})

    # ---------- sol panel
    def show_side(self, mode):
        self.side_mode = mode
        for key, (lbl, bar) in self.seg_btns.items():
            on = key == mode
            lbl.config(fg=UI["text"] if on else UI["muted"])
            bar.config(bg=UI["accent"] if on else UI["panel"])
        self.btn_sessions.set_active(mode == "sessions")
        self.btn_sftp.set_active(mode == "sftp")
        self.sessions_view.pack_forget()
        self.sftp_holder.pack_forget()
        if mode == "sessions":
            self.sessions_view.pack(fill="both", expand=True)
        else:
            self.sftp_holder.pack(fill="both", expand=True)
            self._show_sftp_for(self.current_tab())

    def _show_sftp_for(self, tab):
        for w in self.sftp_holder.winfo_children():
            w.pack_forget()
        if tab:
            tab.sftp_frame.pack(fill="both", expand=True)
        else:
            self.sftp_empty.pack(expand=True)

    # ---------- sekmeler
    def current_tab(self):
        cur = self.nb.select()
        return self.nametowidget(cur) if cur else None

    def _update_main(self):
        if self.nb.tabs():
            self.home.pack_forget()
            self.nb.pack(fill="both", expand=True)
        else:
            self.nb.pack_forget()
            self.home.pack(fill="both", expand=True)
        self.refresh_status()

    def open_tab(self, session, password=None):
        if password is None:
            dlg = PasswordDialog(self, session, self.monitor(session.get("color", UI["accent"])))
            password = dlg.show(dlg.entry)
            if password is None:
                return
        if session in self.sessions:
            session["last"] = time.time()
            save_json(SESSIONS_FILE, self.sessions)
            self._build_home()
        tab = TerminalTab(self, session, password)
        self.nb.add(tab, text=f' {session["name"]} ', image=self.dots["connecting"],
                    compound="left")
        self._update_main()
        self.nb.select(tab)
        tab.term.focus_set()

    def on_tab_status(self, tab):
        try:
            self.nb.tab(tab, image=self.dots[tab.state])
        except tk.TclError:
            pass
        if tab is self.current_tab():
            self.refresh_status()

    def on_connected(self, tab):
        if tab is self.current_tab() and self.side_mode == "sessions":
            self.show_side("sftp")

    def _on_tab_changed(self):
        tab = self.current_tab()
        if self.side_mode == "sftp":
            self._show_sftp_for(tab)
        if tab:
            tab.term.focus_set()
        self.refresh_status()

    def refresh_status(self):
        tab = self.current_tab() if self.nb.tabs() else None
        self.st_theme.config(text=f'◐ {self.settings["theme"]}   ·   UTF-8')
        if not tab:
            self.st_state.config(text="  HakTerm  ", bg=UI["accent"])
            self.st_text.config(text=f"{len(self.sessions)} kayıtlı oturum")
            self.st_size.config(text="")
            return
        self.st_state.config(text=f"● {STATE_TEXT[tab.state]}", bg=STATE_COLORS[tab.state])
        text = tab.status_text
        if tab.offset:
            text += f"   ·   geçmiş: {tab.offset} satır yukarıda (bir tuşa basınca iner)"
        self.st_text.config(text=text)
        self.st_size.config(text=f"{tab.screen.columns} × {tab.screen.lines}")

    def close_tab(self, tab=None):
        tab = tab or self.current_tab()
        if not tab:
            return
        tab.close()
        self.nb.forget(tab)
        tab.destroy()
        self._update_main()
        if self.side_mode == "sftp":
            self._show_sftp_for(self.current_tab())

    def duplicate_tab(self):
        tab = self.current_tab()
        if tab:
            self.open_tab(tab.session, tab.password)

    def reconnect_tab(self):
        tab = self.current_tab()
        if not tab:
            return
        idx = self.nb.index(tab)
        session, pw = tab.session, tab.password
        self.close_tab(tab)
        self.open_tab(session, pw)
        new = self.current_tab()
        self.nb.insert(idx, new)
        self.nb.select(new)

    def next_tab(self):
        tabs = self.nb.tabs()
        if len(tabs) > 1:
            i = tabs.index(self.nb.select())
            self.nb.select(tabs[(i + 1) % len(tabs)])

    def _tab_at(self, e):
        try:
            return self.nb.index(f"@{e.x},{e.y}")
        except tk.TclError:
            return None

    def _middle_close(self, e):
        i = self._tab_at(e)
        if i is not None:
            self.close_tab(self.nametowidget(self.nb.tabs()[i]))

    def _tab_menu(self, e):
        i = self._tab_at(e)
        if i is None:
            return
        self.nb.select(i)
        m = dark_menu(self)
        m.add_command(label="Yeniden bağlan", command=self.reconnect_tab)
        m.add_command(label="Çoğalt", command=self.duplicate_tab)
        m.add_separator()
        m.add_command(label="Kapat", command=self.close_tab)
        m.tk_popup(e.x_root, e.y_root)

    # ---------- tema / yazı
    def next_theme(self):
        names = list(THEMES)
        i = names.index(self.settings["theme"])
        self.settings["theme"] = names[(i + 1) % len(names)]
        save_json(SETTINGS_FILE, self.settings)
        self._set_theme_vars()
        for t in self.nb.tabs():
            self.nametowidget(t).apply_theme()
        self.refresh_status()

    def zoom(self, step):
        size = max(7, min(28, self.settings["font_size"] + step))
        if size == self.settings["font_size"]:
            return
        self.settings["font_size"] = size
        save_json(SETTINGS_FILE, self.settings)
        for t in self.nb.tabs():
            self.nametowidget(t).apply_font()

    def _quit(self):
        for t in self.nb.tabs():
            try:
                self.nametowidget(t).close()
            except Exception:
                pass
        self.destroy()


def main():
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)   # net, bulanık olmayan yazı
        except Exception:
            pass
    App().mainloop()


if __name__ == "__main__":
    main()

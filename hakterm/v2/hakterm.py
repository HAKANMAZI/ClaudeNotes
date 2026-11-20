#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HakTerm v2 - MobaXterm benzeri, sade ve ücretsiz SSH + SFTP istemcisi.

v2 ile gelenler:
  - Gerçek terminal emülasyonu (pyte): renkler, kalın yazı, imleç
  - vim, nano, htop, top, mc gibi tam ekran programlar düzgün çalışır
  - Geçmişe kaydırma: fare tekerleği veya Shift+PageUp / Shift+PageDown
  - Bracketed paste: vim'e yapıştırırken girinti bozulmaz

v1'den kalanlar:
  - Kayıtlı oturumlar, sekmeler, SFTP dosya gezgini, hızlı bağlantı

Kısayollar (terminalde):
  - Sağ tık          : Seçili metin varsa kopyala, yoksa yapıştır
  - Ctrl+Shift+C     : Kopyala
  - Ctrl+Shift+V     : Yapıştır

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
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, simpledialog, ttk

import paramiko
import pyte

APP_NAME = "HakTerm v2"
SESSIONS_FILE = os.path.join(os.path.expanduser("~"), ".hakterm_sessions.json")

DEFAULT_FG = "#cccccc"
DEFAULT_BG = "#0c0c0c"
SCROLLBACK = 5000

# Windows Terminal "Campbell" renk paleti
PALETTE = {
    "black": "#0c0c0c", "red": "#c50f1f", "green": "#13a10e", "brown": "#c19c00",
    "yellow": "#c19c00", "blue": "#0037da", "magenta": "#881798", "cyan": "#3a96dd",
    "white": "#cccccc", "brightblack": "#767676", "brightred": "#e74856",
    "brightgreen": "#16c60c", "brightbrown": "#f9f1a5", "brightyellow": "#f9f1a5",
    "brightblue": "#3b78ff", "brightmagenta": "#b4009e", "brightcyan": "#61d6d6",
    "brightwhite": "#f2f2f2",
}
BASE_COLORS = {"black", "red", "green", "brown", "yellow", "blue", "magenta", "cyan", "white"}

DECCKM = 1 << 5            # uygulama imleç tuşları (vim, htop)
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


def color(name, default, bold=False):
    if name == "default":
        return default
    if bold and name in BASE_COLORS:
        name = "bright" + name
    if len(name) == 6:
        try:
            int(name, 16)
            return "#" + name
        except ValueError:
            pass
    return PALETTE.get(name, default)


class TermScreen(pyte.Screen):
    """pyte ekranı + geçmiş (scrollback) + alternatif ekran (vim/htop)."""

    def __init__(self, columns, lines, send):
        super().__init__(columns, lines)
        self.scrollback = collections.deque(maxlen=SCROLLBACK)
        self.in_alt = False
        self._saved = None
        self._send = send

    def write_process_input(self, data):
        # Terminal sorgularına (ör. cihaz özellikleri) cevap
        self._send(data)

    def select_graphic_rendition(self, *attrs, private=False, **kwargs):
        # vim gibi programlar 'CSI > 4 ; 2 m' gibi özel kodlar yollar; yok say
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


# ---------------------------------------------------------------- oturumlar
def load_sessions():
    try:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_sessions(sessions):
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)


def human_size(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


class SessionDialog(tk.Toplevel):
    """Yeni / düzenle oturum penceresi."""

    def __init__(self, master, session=None):
        super().__init__(master)
        self.title("Oturum")
        self.resizable(False, False)
        self.transient(master)
        self.result = None
        s = session or {}

        self.vars = {
            "name": tk.StringVar(value=s.get("name", "")),
            "host": tk.StringVar(value=s.get("host", "")),
            "port": tk.StringVar(value=str(s.get("port", 22))),
            "user": tk.StringVar(value=s.get("user", "")),
            "key": tk.StringVar(value=s.get("key", "")),
        }
        labels = [("Oturum adı", "name"), ("Sunucu", "host"), ("Port", "port"),
                  ("Kullanıcı", "user"), ("SSH anahtarı (isteğe bağlı)", "key")]
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)
        for i, (text, key) in enumerate(labels):
            ttk.Label(frm, text=text).grid(row=i, column=0, sticky="w", pady=3)
            ttk.Entry(frm, textvariable=self.vars[key], width=34).grid(row=i, column=1, pady=3)
        ttk.Button(frm, text="Seç...", command=self._pick_key).grid(row=4, column=2, padx=4)

        btns = ttk.Frame(frm)
        btns.grid(row=5, column=0, columnspan=3, pady=(10, 0))
        ttk.Button(btns, text="Kaydet", command=self._ok).pack(side="left", padx=4)
        ttk.Button(btns, text="İptal", command=self.destroy).pack(side="left", padx=4)

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.grab_set()
        self.wait_window()

    def _pick_key(self):
        p = filedialog.askopenfilename(title="SSH anahtarı seç", parent=self)
        if p:
            self.vars["key"].set(p)

    def _ok(self):
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
        self.result = d
        self.destroy()


# ---------------------------------------------------------------- sekme
class TerminalTab(ttk.Frame):
    """Bir SSH bağlantısı: solda SFTP, sağda terminal."""

    def __init__(self, notebook, session, password):
        super().__init__(notebook)
        self.session = session
        self.password = password
        self.client = None
        self.chan = None
        self.sftp = None
        self.remote_dir = "."
        self.alive = True
        self.q = queue.Queue()
        self.screen = TermScreen(120, 40, self._send)
        self.stream = pyte.ByteStream(self.screen)
        self.offset = 0          # geçmişte kaç satır yukarıdayız
        self.dirty = True
        self._tags = {}
        self._last_size = None

        self._build()
        threading.Thread(target=self._connect, daemon=True).start()
        self.after(30, self._poll)

    # ---------- arayüz
    def _build(self):
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # SFTP paneli
        left = ttk.Frame(paned)
        bar = ttk.Frame(left)
        bar.pack(fill="x")
        for text, cmd in [("⬆", self.sftp_up), ("⟳", self.sftp_refresh),
                          ("Yükle", self.sftp_upload), ("İndir", self.sftp_download),
                          ("Klasör+", self.sftp_mkdir), ("Sil", self.sftp_delete)]:
            ttk.Button(bar, text=text, command=cmd, width=len(text) + 2).pack(side="left", padx=1, pady=2)

        self.path_var = tk.StringVar()
        path_entry = ttk.Entry(left, textvariable=self.path_var)
        path_entry.pack(fill="x", padx=2)
        path_entry.bind("<Return>", lambda e: self.sftp_go(self.path_var.get()))

        tree_frame = ttk.Frame(left)
        tree_frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tree_frame, columns=("size",), selectmode="extended")
        self.tree.heading("#0", text="Ad")
        self.tree.heading("size", text="Boyut")
        self.tree.column("#0", width=200)
        self.tree.column("size", width=80, anchor="e")
        ysb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        ysb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self._on_tree_double)
        paned.add(left, weight=1)

        # Terminal
        right = tk.Frame(paned, bg=DEFAULT_BG)
        self.font = tkfont.Font(family="Consolas", size=11)
        self.font_bold = tkfont.Font(family="Consolas", size=11, weight="bold")
        self.term = tk.Text(right, bg=DEFAULT_BG, fg=DEFAULT_FG, font=self.font,
                            wrap="none", undo=False, borderwidth=0, highlightthickness=0,
                            padx=2, pady=2, insertwidth=0, selectbackground="#264f78",
                            cursor="xterm")
        self.term.pack(fill="both", expand=True)
        self.term.tag_configure("cursor", background=DEFAULT_FG, foreground=DEFAULT_BG)
        paned.add(right, weight=3)
        self.after(50, lambda: paned.sashpos(0, 260))

        t = self.term
        t.bind("<Key>", self._on_key)
        t.bind("<Control-C>", self._copy)        # Ctrl+Shift+C
        t.bind("<Control-V>", self._paste)       # Ctrl+Shift+V
        t.bind("<Shift-Prior>", lambda e: self._scroll(self.screen.lines // 2))
        t.bind("<Shift-Next>", lambda e: self._scroll(-(self.screen.lines // 2)))
        t.bind("<Button-3>", self._right_click)
        t.bind("<<Paste>>", self._paste)
        t.bind("<MouseWheel>", self._on_wheel)                 # Windows / macOS
        t.bind("<Button-4>", lambda e: self._wheel_step(1))    # Linux
        t.bind("<Button-5>", lambda e: self._wheel_step(-1))
        t.bind("<Configure>", self._on_resize)

        self.status = ttk.Label(self, text="Bağlanıyor...", anchor="w")
        self.status.pack(fill="x")
        t.focus_set()

    # ---------- bağlantı (arka plan)
    def _open_client(self):
        s = self.session
        c = paramiko.SSHClient()
        c.load_system_host_keys()
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
            self.q.put(("status", f'Bağlandı: {s["user"]}@{s["host"]}:{s.get("port", 22)}'))
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
                        pass   # bilinmeyen kaçış kodu terminali durdurmasın
                    self.dirty = True
                elif kind == "status":
                    self.status.config(text=val)
                elif kind == "refresh":
                    self.sftp_refresh()
                elif kind == "resize":
                    self._last_size = None
                    self._on_resize()
                elif kind == "closed":
                    self.status.config(text="Bağlantı kapandı.")
                    self._message("[Bağlantı kapandı]")
                elif kind == "error":
                    self.status.config(text="Hata: " + val)
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
        self.stream.feed(("\r\n\x1b[33m" + text + "\x1b[0m\r\n").encode("utf-8"))
        self.dirty = True

    # ---------- ekran çizimi
    def _tag_for(self, ch):
        fg = color(ch.fg, DEFAULT_FG, ch.bold)
        bg = color(ch.bg, DEFAULT_BG)
        if ch.reverse:
            fg, bg = bg, fg
        key = (fg, bg, ch.bold, ch.underscore)
        if key == (DEFAULT_FG, DEFAULT_BG, False, False):
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
            # sondaki boş, renksiz hücreleri at (kopyalarken boşluk gelmesin)
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
            # geniş karakterlerde sütun = metin içindeki konum
            x = sc.cursor.x
            if len(line_text) < x + 1:
                t.insert(f"{cur_y + 1}.end", " " * (x + 1 - len(line_text)))
            t.tag_add("cursor", f"{cur_y + 1}.{x}", f"{cur_y + 1}.{x + 1}")
        if sel:
            t.tag_add("sel", *sel)
        if self.offset:
            self.status.config(text=f"Geçmiş: {self.offset} satır yukarıda "
                                    f"(aşağı inmek için bir tuşa bas)")

    # ---------- klavye / fare
    def _send(self, s):
        if self.chan and not self.chan.closed:
            try:
                self.chan.send(s)
            except Exception:
                pass

    def _on_key(self, e):
        if e.keysym in ("Shift_L", "Shift_R", "Control_L", "Control_R",
                        "Alt_L", "Alt_R", "Caps_Lock", "Num_Lock"):
            return "break"
        seq = None
        if DECCKM in self.screen.mode:
            seq = APP_CURSOR.get(e.keysym)
        if seq is None:
            seq = KEYMAP.get(e.keysym)
        if seq is None:
            seq = e.char
            if seq and (e.state & 0x20000 or e.state & 0x8) and e.keysym not in KEYMAP \
                    and os.name != "nt":
                seq = "\x1b" + seq      # Alt+tuş (Linux)
        if seq:
            if self.offset:
                self.offset = 0
                self.dirty = True
                self.status.config(text="")
            self._send(seq)
        return "break"

    def _scroll(self, n):
        if self.screen.in_alt:
            return "break"
        self.offset = max(0, min(len(self.screen.scrollback), self.offset + n))
        if self.offset == 0:
            self.status.config(text="")
        self.dirty = True
        return "break"

    def _wheel_step(self, direction):
        if self.screen.in_alt:
            # vim/htop içinde tekerlek = ok tuşları
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
        w = self.term.winfo_width() - 6
        h = self.term.winfo_height() - 6
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

    # ---------- SFTP
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
            self.status.config(text=f"Klasör okunamadı: {e}")
            return
        items.sort(key=lambda a: (not stat.S_ISDIR(a.st_mode or 0), a.filename.lower()))
        for a in items:
            is_dir = stat.S_ISDIR(a.st_mode or 0)
            name = ("📁 " if is_dir else "📄 ") + a.filename
            size = "" if is_dir else human_size(a.st_size or 0)
            self.tree.insert("", "end", text=name, values=(size,),
                             tags=("dir" if is_dir else "file",),
                             iid=a.filename)

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

    def _on_tree_double(self, e):
        iid = self.tree.focus()
        if not iid:
            return
        if "dir" in self.tree.item(iid, "tags"):
            self.sftp_go(posixpath.join(self.remote_dir, iid))
        else:
            self.sftp_download()

    def _bg(self, work, done_text):
        """Dosya aktarımını ayrı SFTP bağlantısıyla arka planda yapar."""
        def run():
            try:
                sftp = self.client.open_sftp()
                try:
                    work(sftp)
                finally:
                    sftp.close()
                self.q.put(("status", done_text))
            except Exception as ex:
                self.q.put(("status", f"Hata: {ex}"))
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
                self.q.put(("status", f"Yükleniyor ({i}/{len(files)}): {name}"))
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
                self.q.put(("status", f"İndiriliyor ({i}/{len(sel)}): {name}"))
                sftp.get(posixpath.join(src, name), os.path.join(dest, name))
        self._bg(work, f"İndirme bitti: {dest}")

    def sftp_mkdir(self):
        if not self._need_sftp():
            return
        name = simpledialog.askstring(APP_NAME, "Yeni klasör adı:")
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
                    self.sftp.rmdir(path)  # yalnızca boş klasör
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


# ---------------------------------------------------------------- ana pencere
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1200x720")
        self.sessions = load_sessions()
        try:
            ttk.Style(self).theme_use("vista" if os.name == "nt" else "clam")
        except tk.TclError:
            pass
        self._build_menu()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._quit)

    def _build_menu(self):
        m = tk.Menu(self)
        f = tk.Menu(m, tearoff=0)
        f.add_command(label="Yeni oturum", command=self.new_session)
        f.add_command(label="Hızlı bağlan...", command=self.quick_connect, accelerator="Ctrl+N")
        f.add_separator()
        f.add_command(label="Çıkış", command=self._quit)
        m.add_cascade(label="Dosya", menu=f)
        t = tk.Menu(m, tearoff=0)
        t.add_command(label="Sekmeyi kapat", command=self.close_tab, accelerator="Ctrl+W")
        m.add_cascade(label="Sekme", menu=t)
        self.config(menu=m)
        self.bind_all("<Control-n>", lambda e: self.quick_connect())
        self.bind_all("<Control-w>", lambda e: self.close_tab())

    def _build(self):
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)

        left = ttk.Frame(paned, padding=4)
        ttk.Label(left, text="Oturumlar", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.listbox = tk.Listbox(left, activestyle="none", font=("Segoe UI", 10), width=24)
        self.listbox.pack(fill="both", expand=True, pady=4)
        self.listbox.bind("<Double-1>", lambda e: self.connect_selected())
        self.listbox.bind("<Return>", lambda e: self.connect_selected())
        btns = ttk.Frame(left)
        btns.pack(fill="x")
        for text, cmd in [("Bağlan", self.connect_selected), ("Yeni", self.new_session),
                          ("Düzenle", self.edit_session), ("Sil", self.delete_session)]:
            ttk.Button(btns, text=text, command=cmd).pack(side="left", expand=True, fill="x", padx=1)
        paned.add(left, weight=0)

        right = ttk.Frame(paned)
        self.nb = ttk.Notebook(right)
        self.nb.pack(fill="both", expand=True)
        self.nb.bind("<Button-2>", self._middle_close)
        self.welcome = ttk.Label(
            right, anchor="center", justify="center", font=("Segoe UI", 12),
            text="HakTerm\n\nSoldan bir oturuma çift tıkla\nveya Ctrl+N ile hızlı bağlan.")
        self.welcome.place(relx=0.5, rely=0.5, anchor="center")
        paned.add(right, weight=1)
        self.after(50, lambda: paned.sashpos(0, 200))
        self._refresh_list()

    # ---------- oturum listesi
    def _refresh_list(self):
        self.listbox.delete(0, "end")
        for s in self.sessions:
            self.listbox.insert("end", f'🖥  {s["name"]}')

    def _selected_index(self):
        sel = self.listbox.curselection()
        return sel[0] if sel else None

    def new_session(self):
        d = SessionDialog(self).result
        if d:
            self.sessions.append(d)
            save_sessions(self.sessions)
            self._refresh_list()

    def edit_session(self):
        i = self._selected_index()
        if i is None:
            return
        d = SessionDialog(self, self.sessions[i]).result
        if d:
            self.sessions[i] = d
            save_sessions(self.sessions)
            self._refresh_list()

    def delete_session(self):
        i = self._selected_index()
        if i is None:
            return
        if messagebox.askyesno(APP_NAME, f'"{self.sessions[i]["name"]}" silinsin mi?'):
            del self.sessions[i]
            save_sessions(self.sessions)
            self._refresh_list()

    def connect_selected(self):
        i = self._selected_index()
        if i is not None:
            self.open_tab(self.sessions[i])

    def quick_connect(self):
        txt = simpledialog.askstring(APP_NAME, "kullanici@sunucu[:port] yaz:", parent=self)
        if not txt or "@" not in txt:
            return
        user, rest = txt.strip().split("@", 1)
        host, _, port = rest.partition(":")
        self.open_tab({"name": txt.strip(), "host": host, "user": user,
                       "port": int(port) if port.isdigit() else 22, "key": ""})

    # ---------- sekmeler
    def open_tab(self, session):
        prompt = ("Anahtar parolası (yoksa boş bırak):" if session.get("key")
                  else f'{session["user"]}@{session["host"]} şifresi:')
        pw = simpledialog.askstring(APP_NAME, prompt, show="*", parent=self)
        if pw is None:
            return
        self.welcome.place_forget()
        tab = TerminalTab(self.nb, session, pw)
        self.nb.add(tab, text=f'  {session["name"]}  ')
        self.nb.select(tab)
        tab.term.focus_set()

    def close_tab(self):
        cur = self.nb.select()
        if cur:
            tab = self.nametowidget(cur)
            tab.close()
            self.nb.forget(cur)
            tab.destroy()
        if not self.nb.tabs():
            self.welcome.place(relx=0.5, rely=0.5, anchor="center")

    def _middle_close(self, e):
        try:
            idx = self.nb.index(f"@{e.x},{e.y}")
            self.nb.select(idx)
            self.close_tab()
        except tk.TclError:
            pass

    def _quit(self):
        for t in self.nb.tabs():
            try:
                self.nametowidget(t).close()
            except Exception:
                pass
        self.destroy()


if __name__ == "__main__":
    App().mainloop()

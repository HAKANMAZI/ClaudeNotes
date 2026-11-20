#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HakTerm - MobaXterm benzeri, sade ve ücretsiz SSH + SFTP istemcisi.

Özellikler:
  - Kayıtlı oturumlar (sol panel)
  - Sekmeli SSH terminali
  - Her sekmede solda SFTP dosya gezgini (yükle, indir, sil, klasör aç)
  - Hızlı bağlantı (kullanici@sunucu:port)
  - Şifre veya SSH anahtarı ile giriş

Kısayollar (terminalde):
  - Sağ tık          : Seçili metin varsa kopyala, yoksa yapıştır
  - Ctrl+Shift+C     : Kopyala
  - Ctrl+Shift+V     : Yapıştır

Gereken: pip install paramiko
"""

import codecs
import json
import os
import posixpath
import queue
import re
import stat
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, simpledialog, ttk

import paramiko

APP_NAME = "HakTerm"
SESSIONS_FILE = os.path.join(os.path.expanduser("~"), ".hakterm_sessions.json")

# Terminal renk/kontrol kodlarını temizlemek için
ANSI_RE = re.compile(
    r"\x1b\[[0-?]*[ -/]*[@-~]"        # CSI dizileri (renk, imleç vb.)
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"  # OSC (pencere başlığı vb.)
    r"|\x1b[()][A-Za-z0-9]"           # karakter seti seçimi
    r"|\x1b[=>78DEHMc]"               # tek karakterli kaçış kodları
)

KEYMAP = {
    "Return": "\r", "KP_Enter": "\r", "BackSpace": "\x7f", "Tab": "\t",
    "Escape": "\x1b", "Up": "\x1b[A", "Down": "\x1b[B", "Right": "\x1b[C",
    "Left": "\x1b[D", "Home": "\x1b[H", "End": "\x1b[F", "Delete": "\x1b[3~",
    "Insert": "\x1b[2~", "Prior": "\x1b[5~", "Next": "\x1b[6~",
    "F1": "\x1bOP", "F2": "\x1bOQ", "F3": "\x1bOR", "F4": "\x1bOS",
    "F5": "\x1b[15~", "F6": "\x1b[17~", "F7": "\x1b[18~", "F8": "\x1b[19~",
    "F9": "\x1b[20~", "F10": "\x1b[21~", "F11": "\x1b[23~", "F12": "\x1b[24~",
}


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
        self.decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
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
        right = ttk.Frame(paned)
        self.font = tkfont.Font(family="Consolas", size=11)
        self.term = tk.Text(right, bg="#0c0c0c", fg="#d0d0d0", insertbackground="#d0d0d0",
                            font=self.font, wrap="char", undo=False, borderwidth=0,
                            selectbackground="#264f78")
        tsb = ttk.Scrollbar(right, orient="vertical", command=self.term.yview)
        self.term.configure(yscrollcommand=tsb.set)
        self.term.pack(side="left", fill="both", expand=True)
        tsb.pack(side="right", fill="y")
        paned.add(right, weight=3)

        self.term.bind("<Key>", self._on_key)
        self.term.bind("<Control-C>", self._copy)      # Ctrl+Shift+C
        self.term.bind("<Control-V>", self._paste)     # Ctrl+Shift+V
        self.term.bind("<Button-3>", self._right_click)
        self.term.bind("<<Paste>>", self._paste)
        self.term.bind("<Configure>", self._on_resize)

        self.status = ttk.Label(self, text="Bağlanıyor...", anchor="w")
        self.status.pack(fill="x")
        self.term.focus_set()

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
            self.chan = self.client.invoke_shell(term="xterm", width=120, height=40)
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
                data = self.chan.recv(4096)
                if not data:
                    break
                self.q.put(("data", self.decoder.decode(data)))
            self.q.put(("closed", None))
        except Exception as e:
            self.q.put(("error", str(e)))

    def _poll(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "data":
                    self._write(val)
                elif kind == "status":
                    self.status.config(text=val)
                elif kind == "refresh":
                    self.sftp_refresh()
                elif kind == "resize":
                    self._last_size = None
                    self._on_resize()
                elif kind == "closed":
                    self.status.config(text="Bağlantı kapandı.")
                    self._write("\n[Bağlantı kapandı]\n")
                elif kind == "error":
                    self.status.config(text="Hata: " + val)
                    self._write(f"\n[Bağlantı hatası] {val}\n")
        except queue.Empty:
            pass
        if self.alive:
            self.after(30, self._poll)

    # ---------- terminal
    def _write(self, text):
        text = ANSI_RE.sub("", text).replace("\r\n", "\n")
        buf = []

        def flush():
            if buf:
                self.term.insert("end", "".join(buf))
                buf.clear()

        for ch in text:
            if ch == "\b":
                flush()
                if self.term.get("end-2c") != "\n":
                    self.term.delete("end-2c", "end-1c")
            elif ch in ("\r", "\x07", "\x00", "\x0f", "\x0e"):
                continue
            else:
                buf.append(ch)
        flush()
        self.term.mark_set("insert", "end-1c")
        self.term.see("end")

    def _send(self, s):
        if self.chan and not self.chan.closed:
            try:
                self.chan.send(s)
            except Exception:
                pass

    def _on_key(self, e):
        seq = KEYMAP.get(e.keysym)
        if seq is None:
            seq = e.char
        if seq:
            self._send(seq)
        return "break"

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
        self._send(txt.replace("\r\n", "\r").replace("\n", "\r"))
        return "break"

    def _right_click(self, e):
        if self.term.tag_ranges("sel"):
            self._copy()
            self.term.tag_remove("sel", "1.0", "end")
        else:
            self._paste()
        return "break"

    def _on_resize(self, e=None):
        if not self.chan:
            return
        w, h = self.term.winfo_width(), self.term.winfo_height()
        cols = max(20, w // max(1, self.font.measure("M")))
        rows = max(5, h // max(1, self.font.metrics("linespace")))
        if (cols, rows) != self._last_size:
            self._last_size = (cols, rows)
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
        self.listbox = tk.Listbox(left, activestyle="none", font=("Segoe UI", 10))
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

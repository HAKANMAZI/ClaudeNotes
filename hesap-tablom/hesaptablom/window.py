"""Hesap Tablom ana penceresi."""
from __future__ import annotations

import copy
import csv
import io
import json
import os
import time

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QStandardPaths, Qt, QTimer
from PySide6.QtGui import QAction, QBrush, QColor, QFont, QGuiApplication, QKeySequence, QTextDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QAbstractItemDelegate, QAbstractItemView, QColorDialog, QComboBox, QFileDialog, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox, QTabBar, QTableView, QToolBar, QToolButton, QVBoxLayout,
    QWidget,
)

from .formula import (
    FErr, Engine, compare, display, is_num, key, map_formula, parse_ref, shift_formula, structural_map,
)

ROWS, COLS, DEFW = 1000, 52, 100
APP = "Hesap Tablom"
ACCENT = "#1d5fa8"


# Sayfalar için kısa, benzersiz bir kimlik üretir.
def _uid():
    return format(time.time_ns(), "x")[-10:]


# Boş bir sayfa sözlüğü oluşturur.
def new_sheet(name):
    return {"id": _uid(), "name": name, "cells": {}, "colW": {}}


# Tek sayfalı boş bir çalışma kitabı oluşturur.
def new_book():
    return {"sheets": [new_sheet("Sayfa1")], "active": 0}


# ====================================================================== model
class SheetModel(QAbstractTableModel):
    # Kurucu: başlangıç durumunu hazırlar.
    def __init__(self, win):
        super().__init__()
        self.win = win

    # Tablodaki satır sayısı.
    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else ROWS

    # Tablodaki sütun sayısı.
    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else COLS

    # Her hücrenin seçilebilir ve düzenlenebilir olduğunu bildirir.
    def flags(self, idx):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    # Satır ve sütun başlıklarının metnini verir.
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return self.win.col_label(section) if orientation == Qt.Horizontal else str(section + 1)
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        return None

    # Bir hücrenin ekranda nasıl görüneceğini (metin, yazı tipi, renk, hizalama) bildirir.
    def data(self, idx, role=Qt.DisplayRole):
        if not idx.isValid():
            return None
        r, c = idx.row(), idx.column()
        sh = self.win.sheet()
        cell = sh["cells"].get(key(r, c))
        if role == Qt.EditRole:
            return cell.get("v", "") if cell else ""
        if not cell:
            return None
        st = cell.get("s") or {}
        if role == Qt.DisplayRole:
            return display(self.win.engine.value(sh, r, c), st)
        if role == Qt.TextAlignmentRole:
            al = st.get("al")
            if not al:
                v = self.win.engine.value(sh, r, c)
                al = "right" if is_num(v) else ("center" if isinstance(v, (bool, FErr)) else "left")
            h = {"left": Qt.AlignLeft, "center": Qt.AlignHCenter, "right": Qt.AlignRight}[al]
            return h | Qt.AlignVCenter
        if role == Qt.FontRole:
            if st.get("b") or st.get("i") or st.get("u"):
                f = QFont()
                f.setBold(bool(st.get("b")))
                f.setItalic(bool(st.get("i")))
                f.setUnderline(bool(st.get("u")))
                return f
            return None
        if role == Qt.ForegroundRole:
            if isinstance(self.win.engine.value(sh, r, c), FErr):
                return QBrush(QColor("#b3261e"))
            if st.get("fc"):
                return QBrush(QColor(st["fc"]))
            return None
        if role == Qt.BackgroundRole:
            return QBrush(QColor(st["bg"])) if st.get("bg") else None
        return None

    # Kullanıcının hücreye yazdığını kaydeder.
    def setData(self, idx, value, role=Qt.EditRole):
        if role != Qt.EditRole or not idx.isValid():
            return False
        self.win.set_cell(idx.row(), idx.column(), "" if value is None else str(value))
        return True

    # Önbelleği boşaltıp tüm tabloyu yeniden çizdirir.
    def refresh(self):
        self.win.engine.clear()
        self.dataChanged.emit(self.index(0, 0), self.index(ROWS - 1, COLS - 1))


# ====================================================================== tablo görünümü
class Grid(QTableView):
    # Kurucu: başlangıç durumunu hazırlar.
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed
        )
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.horizontalHeader().setDefaultSectionSize(DEFW)
        self.verticalHeader().setDefaultSectionSize(24)
        self.verticalHeader().setMinimumWidth(46)
        self.setContextMenuPolicy(Qt.CustomContextMenu)

    # Hücre düzenleyicisi kapanınca Enter'da aşağı, Tab'da sağa geçer.
    def closeEditor(self, editor, hint):
        super().closeEditor(editor, QAbstractItemDelegate.NoHint)
        if hint == QAbstractItemDelegate.SubmitModelCache:
            self.win.move(1, 0)
        elif hint == QAbstractItemDelegate.EditNextItem:
            self.win.move(0, 1)
        elif hint == QAbstractItemDelegate.EditPreviousItem:
            self.win.move(0, -1)

    # Özel tuşları yakalar (Enter, Delete, Esc).
    def keyPressEvent(self, e):
        if self.state() != QAbstractItemView.EditingState:
            k, shift = e.key(), bool(e.modifiers() & Qt.ShiftModifier)
            if k in (Qt.Key_Return, Qt.Key_Enter):
                self.win.move(-1 if shift else 1, 0)
                return
            if k in (Qt.Key_Delete, Qt.Key_Backspace):
                self.win.clear_content()
                return
        super().keyPressEvent(e)


class FormulaBar(QLineEdit):
    # Kurucu: başlangıç durumunu hazırlar.
    def __init__(self, win):
        super().__init__()
        self.win = win

    # Özel tuşları yakalar (Enter, Delete, Esc).
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.win.update_bars()
            self.win.grid.setFocus()
            return
        super().keyPressEvent(e)


# ====================================================================== pencere
class MainWindow(QMainWindow):
    # Kurucu: başlangıç durumunu hazırlar.
    def __init__(self):
        super().__init__()
        self.book = new_book()
        self.title = "Adsız tablo"
        self.path = None
        self.engine = Engine(lambda: self.book)
        self.undo_stack, self.redo_stack = [], []
        self.clip = None
        self._loading = False

        self.autosave_path = os.path.join(
            QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) or os.path.expanduser("~"),
            "otomatik.htab",
        )
        self.save_timer = QTimer(self, singleShot=True, interval=800, timeout=self.autosave)

        self.model = SheetModel(self)
        self.grid = Grid(self)
        self.grid.setModel(self.model)
        self._build_ui()
        self._load_autosave()
        self.apply_col_widths()
        self.grid.setCurrentIndex(self.model.index(0, 0))
        self.grid.setFocus()
        self.update_title()

    # ------------------------------------------------------------ arayüz
    def _build_ui(self):
        self.resize(1200, 760)
        self.setStyleSheet(
            f"""
            QTableView {{ gridline-color: palette(midlight); selection-background-color: rgba(29,95,168,40);
                          selection-color: palette(text); }}
            QTableView::item:focus {{ border: 2px solid {ACCENT}; }}
            QLineEdit#fb, QLineEdit#nb {{ padding: 3px 6px; font-family: 'Cascadia Mono', Consolas, monospace; }}
            QToolBar {{ spacing: 2px; padding: 3px; }}
            """
        )

        # Kısayollu bir menü/araç çubuğu eylemi oluşturur.
        def act(text, slot, shortcut=None, tip=None, checkable=False):
            a = QAction(text, self)
            a.triggered.connect(slot)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            a.setToolTip(tip or (f"{text} ({shortcut})" if shortcut else text))
            a.setCheckable(checkable)
            self.addAction(a)
            return a

        # Dosya araç çubuğu
        tb = QToolBar("Dosya")
        tb.setMovable(False)
        self.addToolBar(tb)
        tb.addAction(act("Yeni", self.new_doc, "Ctrl+N"))
        tb.addAction(act("Aç", self.open_file, "Ctrl+O"))
        tb.addAction(act("Kaydet", lambda: self.save_file(False), "Ctrl+S"))
        tb.addAction(act("Farklı kaydet", lambda: self.save_file(True), "Ctrl+Shift+S"))
        tb.addAction(act("CSV dışa aktar", self.export_csv))
        tb.addAction(act("Yazdır", self.print_sheet, "Ctrl+P"))
        tb.addSeparator()
        tb.addAction(act("Yardım", self.show_help, "F1"))

        self.addToolBarBreak()

        # Biçim araç çubuğu
        fb = QToolBar("Biçim")
        fb.setMovable(False)
        self.addToolBar(fb)
        fb.addAction(act("↶", self.undo, "Ctrl+Z", "Geri al (Ctrl+Z)"))
        fb.addAction(act("↷", self.redo, "Ctrl+Y", "Yinele (Ctrl+Y)"))
        fb.addSeparator()
        self.aB = act("K", lambda: self.toggle_style("b"), "Ctrl+B", "Kalın (Ctrl+B)", True)
        self.aI = act("T", lambda: self.toggle_style("i"), "Ctrl+I", "İtalik (Ctrl+I)", True)
        self.aU = act("A", lambda: self.toggle_style("u"), "Ctrl+U", "Altı çizili (Ctrl+U)", True)
        for a, attr in ((self.aB, "setBold"), (self.aI, "setItalic"), (self.aU, "setUnderline")):
            f = QFont()
            getattr(f, attr)(True)
            a.setFont(f)
            fb.addAction(a)
        fb.addAction(act("Yazı rengi", lambda: self.pick_color("fc")))
        fb.addAction(act("Dolgu", lambda: self.pick_color("bg")))
        fb.addAction(act("Biçimi temizle", self.clear_format))
        fb.addSeparator()
        self.aAL = act("Sola", lambda: self.set_align("left"), tip="Sola hizala", checkable=True)
        self.aAC = act("Orta", lambda: self.set_align("center"), tip="Ortala", checkable=True)
        self.aAR = act("Sağa", lambda: self.set_align("right"), tip="Sağa hizala", checkable=True)
        for a in (self.aAL, self.aAC, self.aAR):
            fb.addAction(a)
        fb.addSeparator()
        self.fmt = QComboBox()
        for text, val in (("Genel", ""), ("Sayı (1.234,56)", "num"), ("Tam sayı (1.235)", "int"),
                          ("Para (₺)", "cur"), ("Yüzde (%)", "pct")):
            self.fmt.addItem(text, val)
        self.fmt.setToolTip("Sayı biçimi")
        self.fmt.activated.connect(lambda i: self.apply_style("fmt", self.fmt.itemData(i) or None))
        fb.addWidget(self.fmt)
        fb.addSeparator()
        fb.addAction(act("Σ Topla", self.auto_sum, "Alt+=", "Seçimin altına TOPLA ekle (Alt+=)"))
        fb.addAction(act("A→Z", lambda: self.sort_sel(False), tip="Etkin sütuna göre artan sırala"))
        fb.addAction(act("Z→A", lambda: self.sort_sel(True), tip="Etkin sütuna göre azalan sırala"))
        fb.addSeparator()
        fb.addAction(act("+ Satır", lambda: self.structural(True, True), tip="Üste satır ekle"))
        fb.addAction(act("− Satır", lambda: self.structural(True, False), tip="Satırı sil"))
        fb.addAction(act("+ Sütun", lambda: self.structural(False, True), tip="Sola sütun ekle"))
        fb.addAction(act("− Sütun", lambda: self.structural(False, False), tip="Sütunu sil"))

        # Görünmez kısayollar
        act("Kopyala", lambda: self.copy(False), "Ctrl+C")
        act("Kes", lambda: self.copy(True), "Ctrl+X")
        act("Yapıştır", self.paste, "Ctrl+V")
        act("Aşağı doldur", self.fill_down, "Ctrl+D")

        # Formül çubuğu
        central = QWidget()
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        bar = QWidget()
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(8, 4, 8, 4)
        self.namebox = QLineEdit(objectName="nb")
        self.namebox.setFixedWidth(100)
        self.namebox.setToolTip("Bir adres yazıp Enter'a basın (örn. C10 veya A1:B5)")
        self.namebox.returnPressed.connect(self.goto_name)
        fx = QLabel("<i>fx</i>")
        fx.setStyleSheet("color: gray; padding: 0 6px; font-family: Georgia, serif;")
        self.fb = FormulaBar(self)
        self.fb.setObjectName("fb")
        self.fb.setPlaceholderText("Değer veya =formül")
        self.fb.returnPressed.connect(self.commit_fb)
        bl.addWidget(self.namebox)
        bl.addWidget(fx)
        bl.addWidget(self.fb)
        lay.addWidget(bar)
        lay.addWidget(self.grid, 1)

        # Sayfa sekmeleri
        bottom = QWidget()
        bt = QHBoxLayout(bottom)
        bt.setContentsMargins(6, 2, 6, 2)
        self.tabs = QTabBar()
        self.tabs.setExpanding(False)
        self.tabs.setDocumentMode(True)
        self.tabs.currentChanged.connect(self.switch_sheet)
        self.tabs.tabBarDoubleClicked.connect(self.rename_sheet)
        self.tabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self.tab_menu)
        add = QToolButton(text="+")
        add.setToolTip("Yeni sayfa")
        add.clicked.connect(self.add_sheet)
        bt.addWidget(self.tabs)
        bt.addWidget(add)
        bt.addStretch(1)
        lay.addWidget(bottom)
        self.setCentralWidget(central)

        self.status = QLabel()
        self.statusBar().addPermanentWidget(self.status)

        sm = self.grid.selectionModel()
        sm.currentChanged.connect(lambda *_: self.update_bars())
        sm.selectionChanged.connect(lambda *_: self.update_status())
        self.grid.horizontalHeader().sectionResized.connect(self.col_resized)
        self.grid.customContextMenuRequested.connect(self.grid_menu)

    # ------------------------------------------------------------ yardımcılar
    def sheet(self):
        return self.book["sheets"][self.book["active"]]

    # Sütun başlığındaki harfi döndürür.
    @staticmethod
    def col_label(c):
        return key(0, c)[:-1]

    # Etkin hücrenin satır ve sütununu döndürür.
    def cur(self):
        i = self.grid.currentIndex()
        return (i.row(), i.column()) if i.isValid() else (0, 0)

    # Seçimi kapsayan dikdörtgenin köşelerini döndürür.
    def sel_range(self):
        idx = self.grid.selectionModel().selectedIndexes()
        if not idx:
            r, c = self.cur()
            return r, c, r, c
        rows = [i.row() for i in idx]
        cols = [i.column() for i in idx]
        return min(rows), min(cols), max(rows), max(cols)

    # Seçili hücrelerin listesi.
    def selected_cells(self):
        idx = self.grid.selectionModel().selectedIndexes()
        return [(i.row(), i.column()) for i in idx] or [self.cur()]

    # Etkin hücreyi verilen satır/sütun kadar kaydırır.
    def move(self, dr, dc):
        r, c = self.cur()
        r, c = max(0, min(ROWS - 1, r + dr)), max(0, min(COLS - 1, c + dc))
        self.grid.setCurrentIndex(self.model.index(r, c))

    # Hücreye yazılan ham metni (formül dahil) döndürür.
    def get_raw(self, r, c):
        cell = self.sheet()["cells"].get(key(r, c))
        return cell.get("v", "") if cell else ""

    # Hücreye ham değer yazar (geri alma kaydı tutmaz).
    def set_raw(self, r, c, v, sh=None):
        sh = sh or self.sheet()
        k = key(r, c)
        cell = sh["cells"].get(k)
        if v == "":
            if cell:
                if cell.get("s"):
                    cell["v"] = ""
                else:
                    del sh["cells"][k]
            return
        if cell:
            cell["v"] = v
        else:
            sh["cells"][k] = {"v": v}

    # Hücreyi değiştirir; geri alma kaydı tutar ve yeniden hesaplar.
    def set_cell(self, r, c, v):
        if v == self.get_raw(r, c):
            return
        self.push_undo()
        self.set_raw(r, c, v)
        self.changed()

    # Bir değişiklikten sonra yeniden hesaplar, ekranı ve çubukları günceller.
    def changed(self):
        self.engine.clear()
        self.model.refresh()
        self.update_bars()
        self.update_status()
        if not self._loading:
            self.save_timer.start()

    # Durum çubuğunda kısa bir bildirim gösterir.
    def toast(self, msg):
        self.statusBar().showMessage(msg, 2500)

    # ------------------------------------------------------------ geri al
    def push_undo(self):
        self.undo_stack.append(json.dumps(self.book))
        if len(self.undo_stack) > 150:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    # Geri al/yinele için saklanan bir anlık görüntüyü yükler.
    def _restore(self, s):
        self.book = json.loads(s)
        self.engine.ast.clear()
        self.refresh_tabs()
        self.apply_col_widths()
        self.changed()

    # Son işlemi geri alır.
    def undo(self):
        if not self.undo_stack:
            self.toast("Geri alınacak bir şey yok")
            return
        self.redo_stack.append(json.dumps(self.book))
        self._restore(self.undo_stack.pop())

    # Geri alınan işlemi yeniden yapar.
    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(json.dumps(self.book))
            self._restore(self.redo_stack.pop())

    # ------------------------------------------------------------ çubuklar
    def update_bars(self):
        r, c = self.cur()
        if not self.fb.hasFocus():
            self.fb.setText(self.get_raw(r, c))
        r1, c1, r2, c2 = self.sel_range()
        multi = (r1, c1) != (r2, c2)
        self.namebox.setText(f"{key(r1, c1)}:{key(r2, c2)}" if multi else key(r, c))
        cell = self.sheet()["cells"].get(key(r, c)) or {}
        st = cell.get("s") or {}
        self.aB.setChecked(bool(st.get("b")))
        self.aI.setChecked(bool(st.get("i")))
        self.aU.setChecked(bool(st.get("u")))
        self.aAL.setChecked(st.get("al") == "left")
        self.aAC.setChecked(st.get("al") == "center")
        self.aAR.setChecked(st.get("al") == "right")
        i = self.fmt.findData(st.get("fmt") or "")
        self.fmt.setCurrentIndex(max(0, i))

    # Seçim için Toplam, Ortalama ve Sayı bilgisini gösterir.
    def update_status(self):
        cells = self.selected_cells()
        if len(cells) < 2:
            self.status.setText("")
            return
        sh, s, n, cnt = self.sheet(), 0.0, 0, 0
        for r, c in cells:
            v = self.engine.value(sh, r, c)
            if v not in (None, ""):
                cnt += 1
            if is_num(v):
                s += v
                n += 1

        # Yardımcı dönüşüm işlevi.
        def f(x):
            return f"{x:,.4f}".rstrip("0").rstrip(".").replace(",", "X").replace(".", ",").replace("X", ".")

        self.status.setText(
            f"Toplam: {f(s)}    Ortalama: {f(s / n)}    Sayı: {cnt}" if n else f"Dolu hücre: {cnt}"
        )

    # Formül çubuğundaki değeri etkin hücreye yazar.
    def commit_fb(self):
        r, c = self.cur()
        self.set_cell(r, c, self.fb.text())
        self.grid.setFocus()
        self.move(1, 0)

    # Ad kutusuna yazılan adrese (C10 ya da A1:B5) gider.
    def goto_name(self):
        txt = self.namebox.text().strip().replace(" ", "")
        parts = txt.split(":")
        refs = [parse_ref(p) for p in parts]
        if not refs or None in refs or len(refs) > 2 or any(r >= ROWS or c >= COLS for r, c in refs):
            self.toast("Geçerli bir adres yazın, örneğin C10 veya A1:B5")
            self.update_bars()
            return
        (r1, c1), (r2, c2) = refs[0], refs[-1]
        self.grid.setCurrentIndex(self.model.index(r1, c1))
        if len(refs) == 2:
            from PySide6.QtCore import QItemSelection, QItemSelectionModel
            sel = QItemSelection(self.model.index(min(r1, r2), min(c1, c2)), self.model.index(max(r1, r2), max(c1, c2)))
            self.grid.selectionModel().select(sel, QItemSelectionModel.ClearAndSelect)
        self.grid.setFocus()

    # ------------------------------------------------------------ biçim
    def apply_style(self, prop, val):
        self.push_undo()
        sh = self.sheet()
        for r, c in self.selected_cells():
            k = key(r, c)
            cell = sh["cells"].setdefault(k, {"v": ""})
            s = dict(cell.get("s") or {})
            if val in (None, "", False):
                s.pop(prop, None)
            else:
                s[prop] = val
            if s:
                cell["s"] = s
            else:
                cell.pop("s", None)
            if not cell.get("s") and not cell.get("v"):
                del sh["cells"][k]
        self.changed()
        self.grid.setFocus()

    # Etkin hücrenin biçim sözlüğünü döndürür.
    def _active_style(self):
        r, c = self.cur()
        return (self.sheet()["cells"].get(key(r, c)) or {}).get("s") or {}

    # Kalın/italik/altı çizili biçimini açar ya da kapatır.
    def toggle_style(self, p):
        self.apply_style(p, None if self._active_style().get(p) else True)

    # Hizalamayı ayarlar; aynı düğmeye ikinci basış kaldırır.
    def set_align(self, al):
        self.apply_style("al", None if self._active_style().get("al") == al else al)

    # Renk seçtirip yazı ya da dolgu rengi olarak uygular.
    def pick_color(self, prop):
        col = QColorDialog.getColor(QColor(self._active_style().get(prop) or ("#b3261e" if prop == "fc" else "#ffe08a")),
                                    self, "Yazı rengi" if prop == "fc" else "Dolgu rengi")
        if col.isValid():
            self.apply_style(prop, col.name())

    # Seçili hücrelerin biçimini kaldırır.
    def clear_format(self):
        self.push_undo()
        sh = self.sheet()
        for r, c in self.selected_cells():
            k = key(r, c)
            cell = sh["cells"].get(k)
            if cell:
                cell.pop("s", None)
                if not cell.get("v"):
                    del sh["cells"][k]
        self.changed()

    # Seçili hücrelerin içeriğini siler, biçimi korur.
    def clear_content(self):
        self.push_undo()
        for r, c in self.selected_cells():
            self.set_raw(r, c, "")
        self.changed()

    # ------------------------------------------------------------ pano
    def copy(self, cut):
        if self.fb.hasFocus() or self.namebox.hasFocus():
            w = self.focusWidget()
            w.cut() if cut else w.copy()
            return
        r1, c1, r2, c2 = self.sel_range()
        sh = self.sheet()
        rows, lines = [], []
        for r in range(r1, r2 + 1):
            row, txt = [], []
            for c in range(c1, c2 + 1):
                cell = sh["cells"].get(key(r, c))
                row.append(copy.deepcopy(cell) if cell else None)
                txt.append(display(self.engine.value(sh, r, c), (cell or {}).get("s")))
            rows.append(row)
            lines.append("\t".join(txt))
        text = "\r\n".join(lines)
        self.clip = {"r1": r1, "c1": c1, "rows": rows, "cut": cut, "sheet": sh["id"], "text": text}
        QGuiApplication.clipboard().setText(text)
        self.toast("Kesildi" if cut else "Kopyalandı")

    # Panodaki veriyi etkin hücreden başlayarak yapıştırır.
    def paste(self):
        if self.fb.hasFocus() or self.namebox.hasFocus():
            self.focusWidget().paste()
            return
        text = QGuiApplication.clipboard().text()
        sh = self.sheet()
        self.push_undo()
        r0, c0 = self.cur()
        clip = self.clip
        if clip and text == clip["text"]:
            rows = clip["rows"]
            h, w = len(rows), len(rows[0])
            g = self.sel_range()
            one = h == 1 and w == 1
            tr, tc = ((g[2] - g[0] + 1), (g[3] - g[1] + 1)) if one else (h, w)
            br, bc = (g[0], g[1]) if one else (r0, c0)
            if clip["cut"]:
                src = next((s for s in self.book["sheets"] if s["id"] == clip["sheet"]), None)
                if src:
                    for i in range(h):
                        for j in range(w):
                            src["cells"].pop(key(clip["r1"] + i, clip["c1"] + j), None)
            for i in range(tr):
                for j in range(tc):
                    r, c = br + i, bc + j
                    if r >= ROWS or c >= COLS:
                        continue
                    s = rows[i % h][j % w]
                    k = key(r, c)
                    if not s:
                        sh["cells"].pop(k, None)
                        continue
                    v = s.get("v", "")
                    if not clip["cut"]:
                        v = shift_formula(v, r - (clip["r1"] + i % h), c - (clip["c1"] + j % w))
                    cell = {"v": v}
                    if s.get("s"):
                        cell["s"] = dict(s["s"])
                    sh["cells"][k] = cell
            if clip["cut"]:
                self.clip = None
        else:
            lines = text.replace("\r", "").split("\n")
            if len(lines) > 1 and lines[-1] == "":
                lines.pop()
            for i, ln in enumerate(lines):
                for j, v in enumerate(ln.split("\t")):
                    if r0 + i < ROWS and c0 + j < COLS:
                        self.set_raw(r0 + i, c0 + j, v)
        self.changed()

    # ------------------------------------------------------------ doldur, topla, sırala
    def fill_down(self):
        r1, c1, r2, c2 = self.sel_range()
        if r1 == r2:
            return
        self.push_undo()
        sh = self.sheet()
        for c in range(c1, c2 + 1):
            src = sh["cells"].get(key(r1, c))
            for r in range(r1 + 1, r2 + 1):
                k = key(r, c)
                if not src:
                    sh["cells"].pop(k, None)
                    continue
                cell = {"v": shift_formula(src.get("v", ""), r - r1, 0)}
                if src.get("s"):
                    cell["s"] = dict(src["s"])
                sh["cells"][k] = cell
        self.changed()

    # Seçimin altına (ya da etkin hücreye) otomatik TOPLA formülü yazar.
    def auto_sum(self):
        r1, c1, r2, c2 = self.sel_range()
        sh = self.sheet()
        self.engine.clear()
        if (r1, c1) == (r2, c2):
            r = r1 - 1
            while r >= 0 and is_num(self.engine.value(sh, r, c1)):
                r -= 1
            if r == r1 - 1:
                self.toast("Üstünde toplanacak sayı yok")
                return
            self.set_cell(r1, c1, f"=TOPLA({key(r + 1, c1)}:{key(r1 - 1, c1)})")
            return
        tr = r2 + 1
        if tr >= ROWS:
            return
        self.push_undo()
        for c in range(c1, c2 + 1):
            self.set_raw(tr, c, f"=TOPLA({key(r1, c)}:{key(r2, c)})")
        self.changed()
        self.grid.setCurrentIndex(self.model.index(tr, c1))

    # Seçimi etkin sütuna göre sıralar; boş hücreler sona gider.
    def sort_sel(self, desc):
        r1, c1, r2, c2 = self.sel_range()
        if r1 == r2:
            self.toast("Sıralamak için birden fazla satır seçin")
            return
        _, ac = self.cur()
        self.push_undo()
        self.engine.clear()
        sh = self.sheet()
        rows = []
        for r in range(r1, r2 + 1):
            v = self.engine.value(sh, r, ac)
            rows.append(([sh["cells"].get(key(r, c)) for c in range(c1, c2 + 1)], None if isinstance(v, FErr) else v))
        filled = [x for x in rows if x[1] not in (None, "")]
        empty = [x for x in rows if x[1] in (None, "")]
        import functools
        filled.sort(key=functools.cmp_to_key(lambda a, b: compare(a[1], b[1])), reverse=desc)
        for i, (cells, _) in enumerate(filled + empty):
            for j, cell in enumerate(cells):
                k = key(r1 + i, c1 + j)
                if cell:
                    sh["cells"][k] = cell
                else:
                    sh["cells"].pop(k, None)
        self.changed()

    # ------------------------------------------------------------ satır / sütun
    def structural(self, is_row, insert):
        r1, c1, r2, c2 = self.sel_range()
        at, count = (r1, r2 - r1 + 1) if is_row else (c1, c2 - c1 + 1)
        if not insert and count >= (ROWS if is_row else COLS):
            self.toast("Tüm satırlar ya da sütunlar silinemez")
            return
        self.push_undo()
        sh = self.sheet()
        limit = ROWS if is_row else COLS
        cells = {}
        for k, cell in sh["cells"].items():
            r, c = parse_ref(k)
            i = r if is_row else c
            if insert:
                if i >= at:
                    i += count
            else:
                if at <= i < at + count:
                    continue
                if i >= at + count:
                    i -= count
            if i < limit:
                cells[key(i, c) if is_row else key(r, i)] = cell
        sh["cells"] = cells
        if not is_row:
            w = {}
            for c, v in sh["colW"].items():
                i = int(c)
                if insert:
                    if i >= at:
                        i += count
                else:
                    if at <= i < at + count:
                        continue
                    if i >= at + count:
                        i -= count
                w[str(i)] = v
            sh["colW"] = w
            self.apply_col_widths()
        fn = structural_map(is_row, insert, at, count)
        for cell in sh["cells"].values():
            cell["v"] = map_formula(cell.get("v", ""), fn)
        self.engine.ast.clear()
        self.changed()

    # ------------------------------------------------------------ sütun genişliği
    def apply_col_widths(self):
        hdr = self.grid.horizontalHeader()
        hdr.blockSignals(True)
        cw = self.sheet().get("colW", {})
        for c in range(COLS):
            hdr.resizeSection(c, int(cw.get(str(c), DEFW)))
        hdr.blockSignals(False)

    # Kullanıcı sütun genişliğini değiştirince kaydeder.
    def col_resized(self, c, _old, new):
        if self._loading:
            return
        self.sheet().setdefault("colW", {})[str(c)] = int(new)
        self.save_timer.start()

    # ------------------------------------------------------------ sayfalar
    def refresh_tabs(self):
        self.tabs.blockSignals(True)
        while self.tabs.count():
            self.tabs.removeTab(0)
        for s in self.book["sheets"]:
            self.tabs.addTab(s["name"])
        self.tabs.setCurrentIndex(self.book["active"])
        self.tabs.blockSignals(False)

    # Başka bir sayfaya geçer.
    def switch_sheet(self, i):
        if i < 0 or i == self.book["active"]:
            return
        self.book["active"] = i
        self.apply_col_widths()
        self.grid.setCurrentIndex(self.model.index(0, 0))
        self.grid.scrollToTop()
        self.changed()

    # Yeni boş bir sayfa ekler ve ona geçer.
    def add_sheet(self):
        self.push_undo()
        n = len(self.book["sheets"]) + 1
        while self.engine.sheet_by_name(f"Sayfa{n}"):
            n += 1
        self.book["sheets"].append(new_sheet(f"Sayfa{n}"))
        self.book["active"] = len(self.book["sheets"]) - 1
        self.refresh_tabs()
        self.apply_col_widths()
        self.changed()

    # Sayfayı yeniden adlandırır ve ona başvuran formülleri günceller.
    def rename_sheet(self, i):
        if i < 0:
            return
        old = self.book["sheets"][i]["name"]
        new, ok = QInputDialog.getText(self, "Sayfayı yeniden adlandır", "Sayfa adı:", text=old)
        new = (new or "").strip()
        if not ok or not new or new == old:
            return
        if any(ch in new for ch in "!'[]*?:/\\"):
            QMessageBox.warning(self, APP, "Ad şu karakterleri içeremez: ! ' [ ] * ? : / \\")
            return
        if self.engine.sheet_by_name(new):
            QMessageBox.warning(self, APP, "Bu adda bir sayfa zaten var.")
            return
        self.push_undo()
        import re
        quoted = f"'{new}'" if re.search(r"[^A-Za-z0-9_ÇĞİÖŞÜçğıöşü]", new) else new
        pat = re.compile("('" + re.escape(old) + "'|(?<![A-Za-z0-9_ÇĞİÖŞÜçğıöşü])" + re.escape(old) + ")!", re.I)
        for s in self.book["sheets"]:
            for cell in s["cells"].values():
                v = cell.get("v", "")
                if v.startswith("="):
                    cell["v"] = pat.sub(quoted + "!", v)
        self.book["sheets"][i]["name"] = new
        self.engine.ast.clear()
        self.refresh_tabs()
        self.changed()

    # Onay alıp bir sayfayı siler.
    def delete_sheet(self, i):
        if len(self.book["sheets"]) == 1:
            self.toast("Son sayfa silinemez")
            return
        name = self.book["sheets"][i]["name"]
        if QMessageBox.question(self, APP, f'"{name}" sayfası silinsin mi?') != QMessageBox.Yes:
            return
        self.push_undo()
        self.book["sheets"].pop(i)
        self.book["active"] = min(self.book["active"], len(self.book["sheets"]) - 1)
        self.refresh_tabs()
        self.apply_col_widths()
        self.changed()

    # Sayfa sekmesinde sağ tık menüsünü gösterir.
    def tab_menu(self, pos):
        i = self.tabs.tabAt(pos)
        if i < 0:
            return
        m = QMenu(self)
        m.addAction("Yeniden adlandır", lambda: self.rename_sheet(i))
        m.addAction("Sil", lambda: self.delete_sheet(i))
        m.exec(self.tabs.mapToGlobal(pos))

    # Tabloda sağ tık menüsünü gösterir.
    def grid_menu(self, pos):
        m = QMenu(self)
        m.addAction("Kes\tCtrl+X", lambda: self.copy(True))
        m.addAction("Kopyala\tCtrl+C", lambda: self.copy(False))
        m.addAction("Yapıştır\tCtrl+V", self.paste)
        m.addSeparator()
        m.addAction("Üste satır ekle", lambda: self.structural(True, True))
        m.addAction("Satırı sil", lambda: self.structural(True, False))
        m.addAction("Sola sütun ekle", lambda: self.structural(False, True))
        m.addAction("Sütunu sil", lambda: self.structural(False, False))
        m.addSeparator()
        m.addAction("İçeriği temizle\tDelete", self.clear_content)
        m.addAction("Biçimi temizle", self.clear_format)
        m.exec(self.grid.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------ dosyalar
    def file_data(self):
        return json.dumps({"app": "HesapTablom", "ver": 1, "title": self.title, "book": self.book},
                          ensure_ascii=False)

    # Bir .htab JSON metnini açar ve ekrana yükler.
    def load_data(self, text, title=None):
        d = json.loads(text)
        book = d.get("book")
        if not book or not isinstance(book.get("sheets"), list) or not book["sheets"]:
            raise ValueError("geçersiz dosya")
        for s in book["sheets"]:
            s.setdefault("id", _uid())
            s.setdefault("cells", {})
            s["colW"] = {str(k): v for k, v in (s.get("colW") or {}).items()}
            s.setdefault("name", "Sayfa")
        book["active"] = max(0, min(int(book.get("active", 0)), len(book["sheets"]) - 1))
        self._loading = True
        self.book = book
        self.title = d.get("title") or title or "Adsız tablo"
        self.engine.ast.clear()
        self.refresh_tabs()
        self.apply_col_widths()
        self.changed()
        self._loading = False

    # Açılışta en son otomatik kaydedilen tabloyu geri yükler.
    def _load_autosave(self):
        try:
            with open(self.autosave_path, encoding="utf-8") as f:
                d = json.load(f)
            self.path = d.get("path")
            self.load_data(json.dumps(d))
        except (OSError, ValueError, KeyError):
            self.refresh_tabs()
            self.changed()

    # Tabloyu uygulama veri klasörüne otomatik kaydeder.
    def autosave(self):
        try:
            os.makedirs(os.path.dirname(self.autosave_path), exist_ok=True)
            data = json.loads(self.file_data())
            data["path"] = self.path
            with open(self.autosave_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except OSError:
            pass
        self.update_title()

    # Pencere başlığına tablo adını yazar.
    def update_title(self):
        self.setWindowTitle(f"{self.title} – {APP}")

    # Tabloyu .htab dosyasına kaydeder.
    def save_file(self, as_new):
        path = self.path
        if as_new or not path:
            start = os.path.join(os.path.expanduser("~"), "Documents", self._safe_title() + ".htab")
            path, _ = QFileDialog.getSaveFileName(self, "Kaydet", start, "Hesap Tablom dosyası (*.htab)")
            if not path:
                return
            if not path.lower().endswith(".htab"):
                path += ".htab"
            self.title = os.path.splitext(os.path.basename(path))[0]
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.file_data())
        except OSError as e:
            QMessageBox.critical(self, APP, f"Dosya kaydedilemedi:\n{e}")
            return
        self.path = path
        self.autosave()
        self.toast(f"Kaydedildi: {path}")

    # Tablo adını dosya adında kullanılabilir hale getirir.
    def _safe_title(self):
        return "".join("_" if ch in '\\/:*?"<>|' else ch for ch in (self.title or "Tablo"))

    # Dosya seçtirip açar.
    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Aç", os.path.join(os.path.expanduser("~"), "Documents"),
            "Tablo dosyaları (*.htab *.json *.csv);;Tüm dosyalar (*)",
        )
        if path:
            self.open_path(path)

    # Verilen yoldaki .htab ya da .csv dosyasını açar.
    def open_path(self, path):
        try:
            with open(path, encoding="utf-8-sig") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError):
            try:
                with open(path, encoding="cp1254") as f:
                    text = f.read()
            except OSError as e:
                QMessageBox.critical(self, APP, f"Dosya açılamadı:\n{e}")
                return
        name = os.path.splitext(os.path.basename(path))[0]
        if path.lower().endswith(".csv"):
            self.import_csv(text, name)
            return
        try:
            self.load_data(text, name)
        except (ValueError, TypeError, KeyError):
            QMessageBox.warning(self, APP, "Bu dosya okunamadı. .htab veya .csv dosyası seçin.")
            return
        self.path = path if path.lower().endswith(".htab") else None
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.autosave()
        self.toast(f"Açıldı: {path}")

    # CSV metnini yeni bir sayfaya aktarır.
    def import_csv(self, text, name):
        first = text.split("\n", 1)[0]
        delim = max(("\t", ";", ","), key=first.count)
        self.push_undo()
        base, nm, n = name or "İçe aktarılan", name or "İçe aktarılan", 2
        while self.engine.sheet_by_name(nm):
            nm = f"{base} ({n})"
            n += 1
        sh = new_sheet(nm)
        for r, row in enumerate(csv.reader(io.StringIO(text), delimiter=delim)):
            for c, v in enumerate(row):
                if v and r < ROWS and c < COLS:
                    sh["cells"][key(r, c)] = {"v": v}
        self.book["sheets"].append(sh)
        self.book["active"] = len(self.book["sheets"]) - 1
        self.refresh_tabs()
        self.apply_col_widths()
        self.changed()
        self.toast("CSV yeni sayfaya aktarıldı")

    # Sayfadaki dolu alanın son satır ve sütununu bulur.
    def _used(self):
        sh = self.sheet()
        mr = mc = -1
        for k, cell in sh["cells"].items():
            if cell.get("v"):
                r, c = parse_ref(k)
                mr, mc = max(mr, r), max(mc, c)
        return mr, mc

    # Etkin sayfayı CSV dosyası olarak dışa aktarır.
    def export_csv(self):
        mr, mc = self._used()
        if mr < 0:
            self.toast("Bu sayfa boş")
            return
        sh = self.sheet()
        start = os.path.join(os.path.expanduser("~"), "Documents", f"{self._safe_title()} - {sh['name']}.csv")
        path, _ = QFileDialog.getSaveFileName(self, "CSV dışa aktar", start, "CSV (*.csv)")
        if not path:
            return
        self.engine.clear()
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, delimiter=";")
            for r in range(mr + 1):
                w.writerow([display(self.engine.value(sh, r, c), (sh["cells"].get(key(r, c)) or {}).get("s"))
                            for c in range(mc + 1)])
        self.toast(f"Dışa aktarıldı: {path}")

    # Etkin sayfayı yazıcıya gönderir.
    def print_sheet(self):
        mr, mc = self._used()
        if mr < 0:
            self.toast("Bu sayfa boş")
            return
        from html import escape
        sh = self.sheet()
        rows = []
        for r in range(mr + 1):
            tds = []
            for c in range(mc + 1):
                cell = sh["cells"].get(key(r, c)) or {}
                st = cell.get("s") or {}
                v = self.engine.value(sh, r, c)
                al = st.get("al") or ("right" if is_num(v) else "left")
                css = f"text-align:{al};"
                css += "font-weight:bold;" if st.get("b") else ""
                css += "font-style:italic;" if st.get("i") else ""
                css += f"background:{st['bg']};" if st.get("bg") else ""
                css += f"color:{st['fc']};" if st.get("fc") else ""
                tds.append(f'<td style="{css}">{escape(display(v, st))}</td>')
            rows.append("<tr>" + "".join(tds) + "</tr>")
        html = ('<table border="1" cellspacing="0" cellpadding="4" style="border-collapse:collapse;font-size:9pt">'
                + "".join(rows) + "</table>")
        printer = QPrinter(QPrinter.HighResolution)
        if QPrintDialog(printer, self).exec():
            doc = QTextDocument()
            doc.setHtml(html)
            doc.print_(printer)

    # Onay alıp yeni boş bir tablo açar.
    def new_doc(self):
        if QMessageBox.question(
            self, APP, "Yeni boş tablo açılsın mı?\nMevcut tabloyu kaydetmediyseniz önce Kaydet'i kullanın."
        ) != QMessageBox.Yes:
            return
        self.book = new_book()
        self.title = "Adsız tablo"
        self.path = None
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.engine.ast.clear()
        self.refresh_tabs()
        self.apply_col_widths()
        self.changed()
        self.grid.setCurrentIndex(self.model.index(0, 0))

    # Kısayol ve fonksiyon rehberini gösterir.
    def show_help(self):
        QMessageBox.information(
            self, f"{APP} — yardım",
            """<h3>Kısa rehber</h3>
<p>Bir hücreye yazmaya başlayın. Formül için <b>=</b> ile başlayın:
<code>=A1+B1</code>, <code>=TOPLA(A1:A10)</code>.
Bağımsız değişkenleri <b>;</b> veya <b>,</b> ile ayırın. Başka sayfa: <code>=Sayfa2!A1</code>.</p>
<p>Çalışmanız otomatik saklanır. Dosya olarak saklamak için <b>Kaydet</b> (.htab).</p>
<h4>Kısayollar</h4>
<p>Enter/Tab: onayla ve ilerle · F2: düzenle · Delete: temizle<br>
Ctrl+C/X/V: kopyala/kes/yapıştır · Ctrl+D: aşağı doldur · Ctrl+Z/Y: geri al/yinele<br>
Ctrl+B/I/U: kalın/italik/altı çizili · Ctrl+S/O: kaydet/aç · Alt+=: otomatik toplam</p>
<h4>Fonksiyonlar</h4>
<p>TOPLA, ORTALAMA, MIN, MAK, BAĞ_DEĞ_SAY, BAĞ_DEĞ_DOLU_SAY, EĞER, EĞERHATA, ETOPLA, EĞERSAY,
DÜŞEYARA, YUVARLA, MUTLAK, KAREKÖK, KUVVET, TAMSAYI, MOD, PI, BİRLEŞTİR, UZUNLUK, BÜYÜKHARF,
KÜÇÜKHARF, VE, YADA, DEĞİL, BUGÜN, ŞİMDİ (İngilizce adları da çalışır).</p>""",
        )

    # Pencere kapanırken son durumu kaydeder.
    def closeEvent(self, e):
        self.save_timer.stop()
        self.autosave()
        super().closeEvent(e)

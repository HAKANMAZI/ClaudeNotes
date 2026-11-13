"""Hesap Tablom başlatıcı."""
import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from hesaptablom.window import MainWindow


# Paketlenmiş EXE içinde de çalışan dosya yolu üretir.
def resource(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


# Uygulamayı başlatır.
def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("HesapTablom.App")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName("HesapTablom")
    app.setOrganizationName("HesapTablom")
    icon = resource(os.path.join("assets", "icon.ico"))
    if os.path.exists(icon):
        app.setWindowIcon(QIcon(icon))
    win = MainWindow()
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        win.open_path(sys.argv[1])
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

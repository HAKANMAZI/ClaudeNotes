"""Komut satırı arayüzü (REPL)."""
import sys
from .errors import DBError
from .engine import Database

def fmt(v):
    if v is None: return "NULL"
    if isinstance(v, float): return f"{v:.4g}" if abs(v) < 1e6 else f"{v:.2f}"
    return str(v)


def print_result(r):
    if isinstance(r, str):
        print(r); return
    headers, rows = r
    cells = [[fmt(v) for v in row] for row in rows]
    w = [max([len(h)] + [len(c[i]) for c in cells]) for i, h in enumerate(headers)]
    line = "+" + "+".join("-" * (x + 2) for x in w) + "+"
    print(line)
    print("| " + " | ".join(h.ljust(w[i]) for i, h in enumerate(headers)) + " |")
    print(line)
    for c in cells:
        print("| " + " | ".join(v.ljust(w[i]) for i, v in enumerate(c)) + " |")
    print(line)
    print(f"({len(rows)} satır)")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "veritabanim"
    db = Database(path)
    print(f"HakEngine — veritabanı: {path}. Komutları ';' ile bitir. Çıkış: .exit, tablolar: .tables")
    buf = ""
    while True:
        try:
            line = input("hakengine> " if not buf else "      ...> ")
        except (EOFError, KeyboardInterrupt):
            break
        s = line.strip()
        if not buf and s in (".exit", ".quit"):
            break
        if not buf and s == ".tables":
            for t in db.tables.values():
                print(f"{t.name} ({', '.join(c['name'] + ' ' + c['type'] for c in t.schema['columns'])})")
            continue
        buf += line + "\n"
        if not s.endswith(";"):
            continue
        try:
            for r in db.execute(buf):
                print_result(r)
        except DBError as e:
            print("HATA:", e)
        buf = ""
    db.close()



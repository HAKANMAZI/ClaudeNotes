"""Komut satırı arayüzü (REPL)."""
import sys, time
from .errors import DBError
from .engine import Database

HELP = """Komutlar:
  .tables            tabloları listeler
  .schema [tablo]    tablo yapısını CREATE TABLE olarak gösterir
  .indexes           indeksleri listeler
  .views             view'ları listeler
  .read dosya.sql    bir SQL dosyasını çalıştırır
  .timer on|off      her komutun süresini gösterir
  .help              bu yardım
  .exit              çıkış
SQL komutlarını ';' ile bitirin. Örnek: SELECT * FROM sys.tables;"""


def fmt(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e15:
            return str(int(v))
        return f"{v:.10g}"
    return str(v)


def print_result(r, out=None):
    out = out or sys.stdout
    if isinstance(r, str):
        print(r, file=out)
        return
    headers, rows = r
    cells = [[fmt(v) for v in row] for row in rows]
    w = [max([len(h)] + [len(c[i]) for c in cells]) for i, h in enumerate(headers)]
    line = "+" + "+".join("-" * (x + 2) for x in w) + "+"
    print(line, file=out)
    print("| " + " | ".join(h.ljust(w[i]) for i, h in enumerate(headers)) + " |", file=out)
    print(line, file=out)
    for c in cells:
        print("| " + " | ".join(v.ljust(w[i]) for i, v in enumerate(c)) + " |", file=out)
    print(line, file=out)
    print(f"({len(rows)} satır)", file=out)


def schema_sql(t):
    parts = []
    for c in t.columns:
        s = f"    {c['name']} {c.get('decl', c['type'])}"
        if c.get("identity"):
            s += f" IDENTITY({c.get('seed', 1)},{c.get('step', 1)})"
        if c.get("pk"):
            s += " PRIMARY KEY"
        elif c.get("notnull"):
            s += " NOT NULL"
        if c.get("unique"):
            s += " UNIQUE"
        if c.get("default"):
            s += f" DEFAULT {c['default']}"
        parts.append(s)
    sql = f"CREATE TABLE {t.name} (\n" + ",\n".join(parts) + "\n);"
    for i in t.indexes:
        if not i.primary and not i.name.startswith("UQ_"):
            sql += f"\nCREATE {'UNIQUE ' if i.unique else ''}INDEX {i.name} ON {t.name} ({i.column});"
    return sql


def run_sql(db, text, timer=False):
    try:
        for st_res in _iter(db, text, timer):
            pass
    except DBError as e:
        print("HATA:", e)


def _iter(db, text, timer):
    from .sql import Parser
    for st in Parser(text).statements():
        t0 = time.perf_counter()
        r = db._execute_one(st)
        print_result(r)
        if timer:
            print(f"Süre: {(time.perf_counter() - t0) * 1000:.1f} ms")
        yield r


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    path = argv[0] if argv else "veritabanim"
    try:
        db = Database(path)
    except DBError as e:
        print("HATA:", e)
        return 1
    if len(argv) > 1:                                  # python hakengine.py vt dosya.sql
        run_sql(db, open(argv[1], encoding="utf-8").read())
        db.close()
        return 0
    print(f"HakEngine v2 — veritabanı: {path}. Yardım: .help  Çıkış: .exit")
    buf, timer = "", False
    while True:
        try:
            line = input("hakengine> " if not buf else "      ...> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        s = line.strip()
        if not buf and s.startswith("."):
            cmd, _, arg = s.partition(" ")
            arg = arg.strip()
            if cmd in (".exit", ".quit"):
                break
            elif cmd == ".help":
                print(HELP)
            elif cmd == ".tables":
                for t in db.tables.values():
                    print(f"{t.name} ({', '.join(c['name'] + ' ' + c['type'] for c in t.columns)})")
            elif cmd == ".schema":
                for t in db.tables.values():
                    if not arg or t.name.lower() == arg.lower():
                        print(schema_sql(t))
            elif cmd == ".indexes":
                run_sql(db, "SELECT * FROM sys.indexes;")
            elif cmd == ".views":
                run_sql(db, "SELECT * FROM sys.views;")
            elif cmd == ".read":
                try:
                    run_sql(db, open(arg, encoding="utf-8").read(), timer)
                except OSError as e:
                    print("HATA:", e)
            elif cmd == ".timer":
                timer = arg.lower() == "on"
                print("Zamanlayıcı", "açık" if timer else "kapalı")
            else:
                print("Bilinmeyen komut. .help yazın")
            continue
        buf += line + "\n"
        if not s.endswith(";"):
            continue
        run_sql(db, buf, timer)
        buf = ""
    db.close()
    return 0

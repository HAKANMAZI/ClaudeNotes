"""Database: katalog, transaction ve sorgu yürütücü (executor)."""
import os, json
from ..errors import DBError
from ..sql import Parser
from ..storage import Table
from .evaluator import evaluate, has_agg, expr_name, sort_key

class Database:
    def __init__(self, path):
        self.path = path
        os.makedirs(path, exist_ok=True)
        self.cat_path = os.path.join(path, "catalog.json")
        self.catalog = json.load(open(self.cat_path)) if os.path.exists(self.cat_path) else {}
        self.tables = {n.lower(): Table(self, s) for n, s in self.catalog.items()}
        self.in_tx = False

    def save_catalog(self):
        tmp = self.cat_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.catalog, f, indent=2)
        os.replace(tmp, self.cat_path)

    def table(self, name):
        t = self.tables.get(name.lower())
        if not t:
            raise DBError(f"Tablo bulunamadı: {name}")
        return t

    def commit(self):
        for t in self.tables.values():
            t.pager.commit()

    def rollback(self):
        for t in self.tables.values():
            t.pager.rollback()
            t.rebuild_index()

    def execute(self, sql):
        results = []
        for st in Parser(sql).statements():
            try:
                results.append(self.run(st))
                if not self.in_tx:
                    self.commit()
            except Exception:
                if not self.in_tx:
                    self.rollback()
                raise
        return results

    def rows_matching(self, t, where):
        # Sorgu iyileştirici: "pk = sabit" varsa indeks kullan, yoksa tam tarama
        if where and where[0] == "bin" and where[1] == "=" and t.pk is not None:
            l, r = where[2], where[3]
            for c, v in ((l, r), (r, l)):
                if c[0] == "col" and c[1].lower() == t.cols[t.pk].lower() and v[0] == "lit":
                    return t.lookup(v[1])
        return [(rid, row) for rid, row in t.scan()
                if where is None or evaluate(where, row, t.cols) is True]

    def run(self, st):
        kind = st[0]
        if kind == "begin":
            if self.in_tx: raise DBError("Zaten açık bir transaction var")
            self.in_tx = True; return "Transaction başladı"
        if kind == "commit":
            self.commit(); self.in_tx = False; return "Commit edildi"
        if kind == "rollback":
            self.rollback(); self.in_tx = False; return "Geri alındı"

        if kind == "create":
            _, name, cols = st
            if name.lower() in self.tables:
                raise DBError(f"Tablo zaten var: {name}")
            if sum(1 for c in cols if c.get("pk")) > 1:
                raise DBError("Tek primary key destekleniyor")
            schema = {"name": name, "columns": cols}
            self.catalog[name] = schema; self.save_catalog()
            self.tables[name.lower()] = Table(self, schema)
            return f"Tablo oluşturuldu: {name}"

        if kind == "drop":
            t = self.table(st[1]); t.pager.close()
            os.remove(t.pager.path)
            del self.tables[t.name.lower()]; del self.catalog[t.name]; self.save_catalog()
            return f"Tablo silindi: {t.name}"

        if kind == "insert":
            _, name, cols, rows = st
            t = self.table(name)
            for r in rows:
                vals = [evaluate(e, [], []) for e in r]
                if cols:
                    if len(cols) != len(vals): raise DBError("Kolon ve değer sayısı uyuşmuyor")
                    full = [None] * len(t.cols)
                    lower = [c.lower() for c in t.cols]
                    for c, v in zip(cols, vals):
                        if c.lower() not in lower: raise DBError(f"Bilinmeyen kolon: {c}")
                        full[lower.index(c.lower())] = v
                    vals = full
                elif len(vals) != len(t.cols):
                    raise DBError(f"{len(t.cols)} değer bekleniyordu")
                t.insert(vals)
            return f"{len(rows)} satır eklendi"

        if kind == "update":
            _, name, sets, where = st
            t = self.table(name)
            lower = [c.lower() for c in t.cols]
            targets = self.rows_matching(t, where)
            for rid, row in targets:
                new = list(row)
                for c, e in sets:
                    if c.lower() not in lower: raise DBError(f"Bilinmeyen kolon: {c}")
                    new[lower.index(c.lower())] = evaluate(e, row, t.cols)
                t.delete(rid, row)
                t.insert(new)
            return f"{len(targets)} satır güncellendi"

        if kind == "delete":
            _, name, where = st
            t = self.table(name)
            targets = self.rows_matching(t, where)
            for rid, row in targets:
                t.delete(rid, row)
            return f"{len(targets)} satır silindi"

        if kind == "select":
            return self.select(st)

    def select(self, st):
        _, items, table, where, group, order, limit = st
        if table:
            t = self.table(table); cols = t.cols
            rows = [row for _, row in self.rows_matching(t, where)]
        else:
            cols, rows = [], [[]]
        exp = []
        for e, alias in items:
            if e == "*":
                exp += [(("col", c), c) for c in cols]
            else:
                exp.append((e, alias or expr_name(e)))
        headers = [a for _, a in exp]
        aggregate = group or any(has_agg(e) for e, _ in exp)

        if aggregate:
            groups = {}
            for r in rows:
                key = tuple(evaluate(g, r, cols) for g in group)
                groups.setdefault(key, []).append(r)
            if not group and not groups:
                groups[()] = []
            out = []
            for _, grp in groups.items():
                rep = grp[0] if grp else [None] * len(cols)
                out.append(([evaluate(e, rep, cols, grp) for e, _ in exp], rep, grp))
        else:
            out = [([evaluate(e, r, cols) for e, _ in exp], r, None) for r in rows]

        for e, desc in reversed(order):
            def key(item, e=e):
                vals, src, grp = item
                if e[0] == "col" and e[1] in headers:
                    return sort_key(vals[headers.index(e[1])])
                if e[0] == "lit" and isinstance(e[1], int):
                    return sort_key(vals[e[1] - 1])
                return sort_key(evaluate(e, src, cols, grp))
            out.sort(key=key, reverse=desc)
        result = [v for v, _, _ in out]
        if limit is not None:
            result = result[:int(limit)]
        return (headers, result)

    def close(self):
        for t in self.tables.values():
            t.pager.close()



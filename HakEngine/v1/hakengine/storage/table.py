"""Heap tablo ve primary key hash indeksi."""
import os
from ..errors import DBError
from .page import PAGE_SIZE
from .pager import Pager
from .row import encode_row, decode_row

class Table:
    def __init__(self, db, schema):
        self.db, self.schema = db, schema
        self.name = schema["name"]
        self.cols = [c["name"] for c in schema["columns"]]
        self.pk = next((i for i, c in enumerate(schema["columns"]) if c.get("pk")), None)
        self.pager = Pager(os.path.join(db.path, self.name + ".tbl"))
        self.rebuild_index()

    def rebuild_index(self):
        self.index = {}
        if self.pk is not None:
            for rid, row in self.scan():
                self.index[row[self.pk]] = rid

    def scan(self):
        for pno in range(self.pager.num_pages):
            for slot, rec in self.pager.get(pno).slots():
                yield (pno, slot), decode_row(rec)

    def coerce(self, vals):
        out = []
        for v, c in zip(vals, self.schema["columns"]):
            t = c["type"]
            if v is None:
                if c.get("pk") or c.get("notnull"):
                    raise DBError(f"'{c['name']}' NULL olamaz")
                out.append(None); continue
            try:
                if t == "INT":
                    out.append(int(v))
                elif t == "REAL":
                    out.append(float(v))
                else:
                    out.append(str(v))
            except (ValueError, TypeError):
                raise DBError(f"'{c['name']}' için geçersiz değer: {v!r}")
        return out

    def insert(self, vals):
        vals = self.coerce(vals)
        if self.pk is not None and vals[self.pk] in self.index:
            raise DBError(f"Primary key ihlali: {vals[self.pk]!r}")
        rec = encode_row(vals)
        if len(rec) > PAGE_SIZE - 64:
            raise DBError("Satır çok büyük")
        pno = self.pager.num_pages - 1
        slot = self.pager.get(pno).insert(rec) if pno >= 0 else None
        if slot is None:
            pno = self.pager.new_page()
            slot = self.pager.get(pno).insert(rec)
        self.pager.mark(pno)
        if self.pk is not None:
            self.index[vals[self.pk]] = (pno, slot)

    def delete(self, rid, row):
        self.pager.get(rid[0]).delete(rid[1])
        self.pager.mark(rid[0])
        if self.pk is not None:
            self.index.pop(row[self.pk], None)

    def lookup(self, key):
        rid = self.index.get(key)
        if rid is None:
            return []
        for slot, rec in self.pager.get(rid[0]).slots():
            if slot == rid[1]:
                return [(rid, decode_row(rec))]
        return []



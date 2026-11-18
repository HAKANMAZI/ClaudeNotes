"""Heap tablo ve indeksleri.

- Satırlar .tbl dosyasında sayfalara yazılır. Satır adresi rid = (sayfa_no, slot_no).
- Her indeks ayrı bir .idx dosyasında B+ ağacıdır.
- Silme olan sayfalar "boş yer ipucu" listesine girer; yeni satırlar oraya yerleşebilir.
"""
import os
from ..errors import DBError
from .pager import Pager
from .page import PAGE_SIZE
from .btree import BTree
from .row import encode_row, decode_row

TYPE_MAP = {
    "INT": "INT", "INTEGER": "INT", "BIGINT": "INT", "SMALLINT": "INT", "TINYINT": "INT", "BIT": "INT",
    "REAL": "REAL", "FLOAT": "REAL", "DOUBLE": "REAL", "DECIMAL": "REAL", "NUMERIC": "REAL",
    "NUMBER": "REAL", "MONEY": "REAL",
    "TEXT": "TEXT", "VARCHAR": "TEXT", "NVARCHAR": "TEXT", "CHAR": "TEXT", "NCHAR": "TEXT",
    "VARCHAR2": "TEXT", "NVARCHAR2": "TEXT", "CLOB": "TEXT", "DATE": "TEXT", "DATETIME": "TEXT",
    "DATETIME2": "TEXT", "TIMESTAMP": "TEXT",
}


def coerce_value(col, v):
    if v is None:
        return None
    t = col["type"]
    try:
        if t == "INT":
            if isinstance(v, str):
                v = v.strip()
                return int(float(v)) if any(ch in v for ch in ".eE") else int(v)
            return int(v)
        if t == "REAL":
            return float(v)
        if isinstance(v, float) and v == int(v):
            return str(int(v))
        return str(v)
    except (ValueError, TypeError, OverflowError):
        raise DBError(f"'{col['name']}' kolonu ({t}) için geçersiz değer: {v!r}")


class Index:
    def __init__(self, dirpath, table_name, meta, colidx):
        self.meta = meta
        self.name = meta["name"]
        self.column = meta["column"]
        self.unique = bool(meta.get("unique"))
        self.primary = bool(meta.get("primary"))
        self.colidx = colidx
        self.path = os.path.join(dirpath, f"{table_name}__{self.name}.idx")
        self.pager = Pager(self.path)
        self.tree = BTree(self.pager)


class Table:
    def __init__(self, dirpath, schema):
        self.dir = dirpath
        self.schema = schema
        self.name = schema["name"]
        self.path = os.path.join(dirpath, self.name + ".tbl")
        self.pager = Pager(self.path)
        self.free_hint = set()
        self.refresh_columns()
        self.indexes = [Index(dirpath, self.name, m, self.col_index(m["column"]))
                        for m in schema.get("indexes", [])]
        self.next_id = None
        if self.identity is not None:
            c = self.columns[self.identity]
            mx = max((r[self.identity] for _, r in self.scan() if r[self.identity] is not None), default=None)
            self.next_id = c.get("seed", 1) if mx is None else mx + c.get("step", 1)

    def refresh_columns(self):
        self.columns = self.schema["columns"]
        self.cols = [c["name"] for c in self.columns]
        self.lower = [c.lower() for c in self.cols]
        self.fill = [c.get("fill") for c in self.columns]
        self.identity = next((i for i, c in enumerate(self.columns) if c.get("identity")), None)

    def col_index(self, name):
        try:
            return self.lower.index(name.lower())
        except ValueError:
            raise DBError(f"'{self.name}' tablosunda '{name}' kolonu yok")

    def pagers(self):
        return [self.pager] + [i.pager for i in self.indexes]

    def index_on(self, colname):
        cands = [i for i in self.indexes if i.column.lower() == colname.lower()]
        cands.sort(key=lambda i: (not i.primary, not i.unique))
        return cands[0] if cands else None

    # ---- okuma
    def _decode(self, rec):
        row = decode_row(rec)
        if len(row) < len(self.cols):
            row += self.fill[len(row):]
        return row

    def scan(self):
        for pno in range(self.pager.num_pages):
            for slot, rec in self.pager.get(pno).slots():
                yield (pno, slot), self._decode(rec)

    def get(self, rid):
        rec = self.pager.get(rid[0]).get(rid[1])
        return self._decode(rec) if rec is not None else None

    def row_count(self):
        return sum(self.pager.get(p).live_count() for p in range(self.pager.num_pages))

    # ---- yazma
    def insert(self, vals):
        row = [coerce_value(c, v) for c, v in zip(self.columns, vals)]
        for c, v in zip(self.columns, row):
            if v is None and c.get("notnull"):
                raise DBError(f"'{c['name']}' kolonu NULL olamaz")
        for idx in self.indexes:
            v = row[idx.colidx]
            if idx.unique and v is not None and next(idx.tree.seek(v), None) is not None:
                if idx.primary:
                    raise DBError(f"Primary key ihlali ({idx.name}): {v!r} zaten var")
                raise DBError(f"Benzersizlik ihlali ({idx.name}): {v!r} zaten var")
        rec = encode_row(row)
        if len(rec) > PAGE_SIZE - 64:
            raise DBError("Satır çok büyük (en fazla yaklaşık dört bin bayt)")
        rid = self._place(rec)
        for idx in self.indexes:
            idx.tree.insert(row[idx.colidx], rid)
        return rid

    def _place(self, rec):
        cands = []
        if self.pager.num_pages:
            cands.append(self.pager.num_pages - 1)
        cands += sorted(self.free_hint)
        for pno in cands:
            if self.pager.get(pno).can_fit(rec):
                return pno, self.pager.write(pno).insert(rec)
            self.free_hint.discard(pno)
        pno = self.pager.new_page()
        return pno, self.pager.write(pno).insert(rec)

    def delete(self, rid, row):
        self.pager.write(rid[0]).delete(rid[1])
        self.free_hint.add(rid[0])
        for idx in self.indexes:
            idx.tree.delete(row[idx.colidx], rid)

    def after_rollback(self):
        self.free_hint.clear()
        for idx in self.indexes:
            idx.tree.reset_cache()

    def close(self):
        for p in self.pagers():
            p.close()

    def remove_files(self):
        self.close()
        for p in self.pagers():
            if os.path.exists(p.path):
                os.remove(p.path)

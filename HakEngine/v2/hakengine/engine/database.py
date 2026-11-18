"""Database: katalog, DDL, DML, transaction, sistem tabloları ve kilit.

Klasör yapısı:
  catalog.json          tablolar, kolonlar, indeksler, view'lar (sys.* karşılığı)
  <tablo>.tbl           tablo verisi (heap)
  <tablo>__<indeks>.idx B+ ağacı indeksi
  hakengine.journal     sadece commit sırasında var olur (çökme kurtarma)
  hakengine.lock        aynı veritabanının iki programda açılmasını engeller
"""
import os, json
from ..errors import DBError
from ..sql import Parser
from ..storage import Table, Index, journal
from ..storage.table import coerce_value
from .evaluator import Env, evaluate, is_const
from .executor import Executor

JOURNAL = "hakengine.journal"
DDL = {"create_table", "create_index", "create_view", "drop_table", "drop_index", "drop_view",
       "alter_add", "truncate"}
MISSING = object()


class Database:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        os.makedirs(self.path, exist_ok=True)
        self._lock()
        try:
            journal.recover(self.path, JOURNAL)
            self.cat_path = os.path.join(self.path, "catalog.json")
            if os.path.exists(self.cat_path):
                with open(self.cat_path, encoding="utf-8") as f:
                    self.catalog = json.load(f)
                if self.catalog.get("version") != 2:
                    raise DBError("Bu klasör HakEngine v1 veritabanı. v2 ile yeni bir klasör kullanın.")
            else:
                self.catalog = {"version": 2, "tables": {}, "views": {}}
            self.tables = {}
            for schema in self.catalog["tables"].values():
                self._open_table(schema)
        except Exception:
            self._unlock()
            raise
        self.in_tx = False
        self.ex = Executor(self)

    # ---- kilit
    def _lock(self):
        self._lockf = open(os.path.join(self.path, "hakengine.lock"), "a+b")
        try:
            if os.name == "nt":
                import msvcrt
                self._lockf.seek(0)
                msvcrt.locking(self._lockf.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._lockf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._lockf.close()
            raise DBError("Veritabanı başka bir program tarafından kullanılıyor")

    def _unlock(self):
        try:
            if os.name == "nt":
                import msvcrt
                self._lockf.seek(0)
                msvcrt.locking(self._lockf.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._lockf.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        self._lockf.close()

    def close(self):
        if self.in_tx:
            self.rollback_all()
        for t in self.tables.values():
            t.close()
        self._unlock()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ---- katalog
    def _save_catalog(self):
        tmp = self.cat_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.catalog, f, indent=2, ensure_ascii=False)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, self.cat_path)

    def _open_table(self, schema):
        t = Table(self.path, schema)
        t.default_ast = {i: Parser(c["default"]).expression()
                         for i, c in enumerate(t.columns) if c.get("default")}
        self.tables[t.name.lower()] = t
        return t

    def table(self, name):
        t = self.tables.get(name.lower())
        if t is None:
            if self.view_sql(name) is not None:
                raise DBError(f"'{name}' bir view; bu işlem sadece tablolarda yapılır")
            raise DBError(f"Tablo bulunamadı: {name}")
        return t

    def view_sql(self, name):
        for k, v in self.catalog["views"].items():
            if k.lower() == name.lower():
                return v
        return None

    def _find_index(self, name):
        for t in self.tables.values():
            for idx in t.indexes:
                if idx.name.lower() == name.lower():
                    return t, idx
        return None, None

    # ---- transaction
    def all_pagers(self):
        return [p for t in self.tables.values() for p in t.pagers()]

    def commit(self):
        try:
            journal.commit(self.path, JOURNAL, self.all_pagers())
        except Exception:
            # Commit yarıda kaldı: journal'dan eski hâli geri yükle, belleği diskle eşitle
            journal.recover(self.path, JOURNAL)
            for p in self.all_pagers():
                p.reload()
            for t in self.tables.values():
                t.after_rollback()
            raise

    def rollback_all(self):
        for p in self.all_pagers():
            p.rollback()
        for t in self.tables.values():
            t.after_rollback()
        self.in_tx = False

    # ---- çalıştırma
    def execute(self, sql):
        return [self._execute_one(st) for st in Parser(sql).statements()]

    def query(self, sql):
        """Tek SELECT için kolaylık: (başlıklar, satırlar) döndürür."""
        return self.execute(sql)[-1]

    def _execute_one(self, st):
        self.ex.reset()
        kind = st[0]
        if kind in DDL and self.in_tx:
            raise DBError("DDL komutları (CREATE, DROP, ALTER, TRUNCATE) transaction içinde kullanılamaz")
        if self.in_tx and kind == "commit":
            try:
                return self.run(st)
            except Exception:
                self.in_tx = False
                raise
        if self.in_tx and kind not in ("begin", "commit", "rollback"):
            pagers = self.all_pagers()
            for p in pagers:
                p.begin_statement()
            try:
                return self.run(st)
            except Exception:
                for p in pagers:
                    p.rollback_statement()
                for t in self.tables.values():
                    t.after_rollback()
                raise
            finally:
                for p in pagers:
                    p.end_statement()
        try:
            res = self.run(st)
            if not self.in_tx:
                self.commit()
            return res
        except Exception:
            if not self.in_tx:
                self.rollback_all()
            raise

    def run(self, st):
        kind = st[0]
        if kind == "begin":
            if self.in_tx:
                raise DBError("Zaten açık bir transaction var")
            self.in_tx = True
            return "Transaction başladı"
        if kind == "commit":
            if not self.in_tx:
                raise DBError("Açık transaction yok")
            self.commit(); self.in_tx = False
            return "Commit edildi"
        if kind == "rollback":
            if not self.in_tx:
                raise DBError("Açık transaction yok")
            self.rollback_all()
            return "Geri alındı"
        if kind == "select":
            return self.ex.run_select(st[1])
        if kind == "explain":
            self.ex.run_select(st[1])
            return (["adım", "işlem"], self.ex.explain_rows())
        return getattr(self, "_" + kind)(*st[1:])

    # ---- DML
    def _const_env(self):
        return Env(None, [], None, None, self.ex)

    def _prepare(self, t, full):
        for i, v in enumerate(full):
            if v is MISSING:
                if i == t.identity:
                    full[i] = t.next_id
                    t.next_id += t.columns[i].get("step", 1)
                elif i in t.default_ast:
                    full[i] = evaluate(t.default_ast[i], self._const_env())
                else:
                    full[i] = None
            elif i == t.identity and v is not None:
                step = t.columns[i].get("step", 1)
                v = int(v)
                if (step > 0 and v >= t.next_id) or (step < 0 and v <= t.next_id):
                    t.next_id = v + step
        return full

    def _insert(self, name, cols, source):
        t = self.table(name)
        if cols:
            idxs = [t.col_index(c) for c in cols]
            if len(set(idxs)) != len(idxs):
                raise DBError("Aynı kolon birden fazla yazılmış")
        else:
            idxs = list(range(len(t.cols)))
        if source[0] == "values":
            env = self._const_env()
            rows = [[evaluate(e, env) for e in r] for r in source[1]]
        else:
            _, rows = self.ex.run_select(source[1])
        for vals in rows:
            if len(vals) != len(idxs):
                raise DBError(f"{len(idxs)} değer bekleniyordu, {len(vals)} verildi")
            full = [MISSING] * len(t.cols)
            for i, v in zip(idxs, vals):
                full[i] = v
            t.insert(self._prepare(t, full))
        return f"{len(rows)} satır eklendi"

    def _targets(self, t, where):
        from .planner import choose_access, access
        from .evaluator import conjuncts
        scope = self.ex.table_scope(t, None)
        plan = choose_access(t, scope, conjuncts(where))
        rows = access(t, plan)
        if where is not None:
            rows = [(rid, r) for rid, r in rows
                    if evaluate(where, Env(scope, r, None, None, self.ex)) is True]
        return scope, rows

    def _update(self, name, sets, where):
        t = self.table(name)
        scope, targets = self._targets(t, where)
        assigns = [(t.col_index(c), e) for c, e in sets]
        new_rows = []
        for _, row in targets:
            env = Env(scope, row, None, None, self.ex)
            new = list(row)
            for i, e in assigns:
                new[i] = evaluate(e, env)
            new_rows.append(new)
        for rid, row in targets:
            t.delete(rid, row)
        for new in new_rows:
            t.insert(new)
        return f"{len(targets)} satır güncellendi"

    def _delete(self, name, where):
        t = self.table(name)
        _, targets = self._targets(t, where)
        for rid, row in targets:
            t.delete(rid, row)
        return f"{len(targets)} satır silindi"

    # ---- DDL
    def _check_new_name(self, name):
        if name.lower().startswith("sys."):
            raise DBError("'sys' şeması sisteme ayrılmıştır")
        if name.lower() in self.tables or self.view_sql(name) is not None:
            raise DBError(f"Bu isimde tablo veya view zaten var: {name}")

    def _check_default(self, col):
        if col.get("default"):
            ast = Parser(col["default"]).expression()
            if not is_const(ast):
                raise DBError(f"'{col['name']}' için DEFAULT sabit bir değer olmalı")
            return ast
        return None

    def _create_table(self, name, cols, table_pk, if_not_exists):
        if if_not_exists and name.lower() in self.tables:
            return f"Tablo zaten var: {name}"
        self._check_new_name(name)
        names = [c["name"].lower() for c in cols]
        if len(set(names)) != len(names):
            raise DBError("Aynı isimde iki kolon var")
        if table_pk:
            if table_pk.lower() not in names:
                raise DBError(f"Primary key kolonu bulunamadı: {table_pk}")
            cols[names.index(table_pk.lower())]["pk"] = True
        pks = [c for c in cols if c.get("pk")]
        if len(pks) > 1:
            raise DBError("Tek kolonlu primary key destekleniyor")
        ids = [c for c in cols if c.get("identity")]
        if len(ids) > 1 or any(c["type"] != "INT" for c in ids):
            raise DBError("Tabloda en fazla bir IDENTITY olur ve tipi tam sayı olmalı")
        indexes = []
        for c in cols:
            self._check_default(c)
            if c.get("pk"):
                c["notnull"] = True
                indexes.append({"name": f"PK_{name}", "column": c["name"], "unique": True, "primary": True})
            elif c.get("unique"):
                indexes.append({"name": f"UQ_{name}_{c['name']}", "column": c["name"], "unique": True})
        schema = {"name": name, "columns": cols, "indexes": indexes}
        self.catalog["tables"][name] = schema
        self._save_catalog()
        self._open_table(schema)
        return f"Tablo oluşturuldu: {name}"

    def _drop_table(self, name, if_exists):
        t = self.tables.get(name.lower())
        if t is None:
            if if_exists:
                return f"Tablo yok: {name}"
            raise DBError(f"Tablo bulunamadı: {name}")
        t.remove_files()
        del self.tables[t.name.lower()]
        del self.catalog["tables"][t.name]
        self._save_catalog()
        return f"Tablo silindi: {t.name}"

    def _build_index(self, t, meta):
        idx = Index(self.path, t.name, meta, t.col_index(meta["column"]))
        try:
            for rid, row in t.scan():
                v = row[idx.colidx]
                if idx.unique and v is not None and next(idx.tree.seek(v), None) is not None:
                    raise DBError(f"Tekrarlanan değer var, UNIQUE indeks oluşturulamadı: {v!r}")
                idx.tree.insert(v, rid)
        except Exception:
            idx.pager.close()
            os.remove(idx.path)
            raise
        t.indexes.append(idx)
        t.schema["indexes"].append(meta)
        return idx

    def _create_index(self, name, table, col, unique):
        t = self.table(table)
        if self._find_index(name)[1] is not None:
            raise DBError(f"Bu isimde indeks zaten var: {name}")
        t.col_index(col)
        self._build_index(t, {"name": name, "column": t.cols[t.col_index(col)], "unique": unique})
        self._save_catalog()
        return f"İndeks oluşturuldu: {name}"

    def _drop_index(self, name, if_exists):
        t, idx = self._find_index(name)
        if idx is None:
            if if_exists:
                return f"İndeks yok: {name}"
            raise DBError(f"İndeks bulunamadı: {name}")
        if idx.primary:
            raise DBError("Primary key indeksi silinemez")
        idx.pager.close()
        os.remove(idx.path)
        t.indexes.remove(idx)
        t.schema["indexes"] = [m for m in t.schema["indexes"] if m["name"] != idx.name]
        self._save_catalog()
        return f"İndeks silindi: {idx.name}"

    def _create_view(self, name, text, replace):
        existing = self.view_sql(name)
        if existing is not None and not replace:
            raise DBError(f"View zaten var: {name}")
        if existing is None:
            self._check_new_name(name)
        for k in list(self.catalog["views"]):
            if k.lower() == name.lower():
                del self.catalog["views"][k]
        self.catalog["views"][name] = text
        self._save_catalog()
        return f"View oluşturuldu: {name}"

    def _drop_view(self, name, if_exists):
        for k in list(self.catalog["views"]):
            if k.lower() == name.lower():
                del self.catalog["views"][k]
                self._save_catalog()
                return f"View silindi: {k}"
        if if_exists:
            return f"View yok: {name}"
        raise DBError(f"View bulunamadı: {name}")

    def _alter_add(self, name, col):
        t = self.table(name)
        if col["name"].lower() in t.lower:
            raise DBError(f"Kolon zaten var: {col['name']}")
        if col.get("pk") or col.get("identity"):
            raise DBError("Sonradan PRIMARY KEY veya IDENTITY kolon eklenemez")
        ast = self._check_default(col)
        fill = coerce_value(col, evaluate(ast, self._const_env())) if ast else None
        if col.get("notnull") and fill is None and t.row_count():
            raise DBError("Dolu tabloya NOT NULL kolon eklemek için DEFAULT gerekir")
        col["fill"] = fill
        t.schema["columns"].append(col)
        t.refresh_columns()
        if ast:
            t.default_ast[len(t.cols) - 1] = ast
        if col.get("unique"):
            self._build_index(t, {"name": f"UQ_{t.name}_{col['name']}", "column": col["name"], "unique": True})
        self._save_catalog()
        return f"Kolon eklendi: {t.name}.{col['name']}"

    def _truncate(self, name):
        t = self.table(name)
        t.remove_files()
        self._open_table(t.schema)
        return f"Tablo boşaltıldı: {t.name}"

    # ---- sistem tabloları
    def system_table(self, name):
        if name == "sys.tables":
            return (["name", "columns", "rows", "pages", "indexes"],
                    [[t.name, len(t.cols), t.row_count(), t.pager.num_pages, len(t.indexes)]
                     for t in self.tables.values()])
        if name == "sys.columns":
            rows = []
            for t in self.tables.values():
                for i, c in enumerate(t.columns):
                    rows.append([t.name, c["name"], i + 1, c["type"], c.get("decl", c["type"]),
                                 0 if c.get("notnull") else 1, 1 if c.get("pk") else 0,
                                 1 if c.get("identity") else 0, c.get("default")])
            return (["table_name", "column_name", "ordinal", "type", "declared_type",
                     "is_nullable", "is_primary_key", "is_identity", "default_value"], rows)
        if name == "sys.indexes":
            return (["index_name", "table_name", "column_name", "is_unique", "is_primary_key",
                     "pages", "depth"],
                    [[i.name, t.name, i.column, int(i.unique), int(i.primary), i.pager.num_pages,
                      i.tree.height()] for t in self.tables.values() for i in t.indexes])
        if name == "sys.views":
            return (["name", "definition"], [[k, v] for k, v in self.catalog["views"].items()])
        raise DBError(f"Bilinmeyen sistem tablosu: {name} (sys.tables, sys.columns, sys.indexes, sys.views)")

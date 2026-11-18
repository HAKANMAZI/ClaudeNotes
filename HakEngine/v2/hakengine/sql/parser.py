"""Parser: tokenlardan sözdizimi ağacı (AST) üretir. Recursive descent yöntemi.

İfade düğümleri (tuple):
  ('lit', değer)                     ('col', tablo|None, kolon)
  ('star', tablo|None)               ('bin', op, sol, sağ)
  ('not', e)  ('neg', e)             ('isnull', e)
  ('in', e, [liste])                 ('insub', e, select)
  ('exists', select)                 ('subq', select)
  ('between', e, alt, üst)           ('case', taban|None, [(koşul, sonuç)], değilse)
  ('func', AD, [argümanlar], distinct)

SELECT bir sözlüktür: distinct, top, items, from, where, group, having, order, limit, offset.
FROM kaynakları: ('table', ad, takma_ad) | ('subquery', select, takma_ad)
                 | ('join', tür, sol, sağ, on_koşulu)
"""
from ..errors import DBError
from .tokenizer import tokenize


class Parser:
    def __init__(self, sql):
        self.sql = sql
        self.t = tokenize(sql)
        self.i = 0

    # ---- yardımcılar
    def peek(self, k=0):
        return self.t[min(self.i + k, len(self.t) - 1)]

    def at(self, kind, val=None, k=0):
        tok = self.peek(k)
        return tok[0] == kind and (val is None or tok[1] == val)

    def next(self):
        tok = self.t[self.i]
        self.i += 1
        return tok

    def accept(self, kind, val=None):
        if self.at(kind, val):
            return self.next()
        return None

    def expect(self, kind, val=None):
        tok = self.accept(kind, val)
        if not tok:
            got = self.peek()
            raise DBError(f"Beklenen: {val or kind}, bulunan: {got[1] if got[0] != 'eof' else 'komut sonu'}")
        return tok

    def word(self, *words):
        """Anahtar kelime olmayan sözcükler (ROWS, FETCH, TRAN ...)."""
        tok = self.peek()
        if tok[0] in ("id", "kw") and str(tok[1]).upper() in words:
            self.i += 1
            return tok[1].upper()
        return None

    def ident(self):
        tok = self.next()
        if tok[0] == "id":
            return tok[1]
        raise DBError(f"İsim bekleniyordu, bulunan: {tok[1] if tok[0] != 'eof' else 'komut sonu'}")

    def table_name(self):
        name = self.ident()
        if self.accept("op", "."):
            second = self.ident()
            if name.lower() == "sys":
                return "sys." + second.lower()
            return second                         # dbo.tablo -> tablo
        return name

    def text_from(self, start):
        return self.sql[start:self.peek()[2]].strip()

    # ---- giriş noktaları
    def statements(self):
        out = []
        while not self.at("eof"):
            if self.accept("op", ";") or self.word("GO"):
                continue
            out.append(self.statement())
            if not self.at("eof"):
                self.expect("op", ";")
        return out

    def expression(self):
        e = self.expr()
        self.expect("eof")
        return e

    def statement(self):
        tok = self.peek()
        if tok[0] != "kw":
            raise DBError(f"Bilinmeyen komut: {tok[1]!r}")
        k = tok[1]
        if k == "SELECT":
            return ("select", self.select())
        if k == "EXPLAIN":
            self.next()
            return ("explain", self.select())
        if k == "INSERT":
            return self.insert()
        if k == "CREATE":
            return self.create()
        if k == "DROP":
            return self.drop()
        if k == "ALTER":
            return self.alter()
        if k == "TRUNCATE":
            self.next(); self.expect("kw", "TABLE")
            return ("truncate", self.table_name())
        if k == "UPDATE":
            return self.update()
        if k == "DELETE":
            return self.delete()
        if k in ("BEGIN", "COMMIT", "ROLLBACK"):
            self.next()
            if not self.accept("kw", "TRANSACTION"):
                self.word("TRAN", "WORK")
            return (k.lower(),)
        raise DBError(f"Bilinmeyen komut: {k}")

    # ---- DDL
    def create(self):
        self.next()
        if self.accept("kw", "OR"):
            self.word("REPLACE")
            self.expect("kw", "VIEW")
            return self.create_view(True)
        unique = bool(self.accept("kw", "UNIQUE"))
        self.word("CLUSTERED", "NONCLUSTERED")
        if self.accept("kw", "INDEX"):
            name = self.ident()
            self.expect("kw", "ON")
            table = self.table_name()
            self.expect("op", "(")
            col = self.ident()
            self.accept("kw", "ASC") or self.accept("kw", "DESC")
            self.expect("op", ")")
            return ("create_index", name, table, col, unique)
        if unique:
            raise DBError("UNIQUE sonrası INDEX bekleniyordu")
        if self.accept("kw", "VIEW"):
            return self.create_view(False)
        self.expect("kw", "TABLE")
        ine = False
        if self.accept("kw", "IF"):
            self.expect("kw", "NOT"); self.expect("kw", "EXISTS"); ine = True
        name = self.table_name()
        self.expect("op", "(")
        cols, table_pk = [], None
        while True:
            if self.word("CONSTRAINT"):
                self.ident()
            if self.accept("kw", "PRIMARY"):
                self.expect("kw", "KEY"); self.word("CLUSTERED", "NONCLUSTERED")
                self.expect("op", "(")
                table_pk = self.ident()
                if self.accept("op", ","):
                    raise DBError("Birden çok kolonlu primary key desteklenmiyor")
                self.expect("op", ")")
            else:
                cols.append(self.column_def())
            if not self.accept("op", ","):
                break
        self.expect("op", ")")
        return ("create_table", name, cols, table_pk, ine)

    def column_def(self):
        from ..storage.table import TYPE_MAP
        name = self.ident()
        decl = self.ident().upper()
        if decl not in TYPE_MAP:
            raise DBError(f"Desteklenmeyen tip: {decl}")
        if self.accept("op", "("):
            while not self.accept("op", ")"):
                if self.at("eof"):
                    raise DBError("')' bekleniyordu")
                self.next()
            decl_full = decl
        else:
            decl_full = decl
        col = {"name": name, "type": TYPE_MAP[decl], "decl": decl_full}
        while True:
            if self.accept("kw", "PRIMARY"):
                self.expect("kw", "KEY"); col["pk"] = True
            elif self.accept("kw", "NOT"):
                self.expect("kw", "NULL"); col["notnull"] = True
            elif self.accept("kw", "NULL"):
                pass
            elif self.accept("kw", "UNIQUE"):
                col["unique"] = True
            elif self.accept("kw", "DEFAULT"):
                start = self.peek()[2]
                self.add_expr()
                col["default"] = self.text_from(start)
            elif self.accept("kw", "IDENTITY"):
                col["identity"], col["seed"], col["step"] = True, 1, 1
                if self.accept("op", "("):
                    col["seed"] = self.signed_int()
                    self.expect("op", ",")
                    col["step"] = self.signed_int()
                    self.expect("op", ")")
            elif self.word("AUTO_INCREMENT", "AUTOINCREMENT"):
                col["identity"], col["seed"], col["step"] = True, 1, 1
            else:
                break
        return col

    def signed_int(self):
        neg = bool(self.accept("op", "-"))
        v = self.expect("lit")[1]
        if not isinstance(v, int):
            raise DBError("Tam sayı bekleniyordu")
        return -v if neg else v

    def create_view(self, replace):
        name = self.ident()
        self.expect("kw", "AS")
        start = self.peek()[2]
        self.select()
        return ("create_view", name, self.text_from(start), replace)

    def drop(self):
        self.next()
        kind = self.next()
        if kind[1] not in ("TABLE", "INDEX", "VIEW"):
            raise DBError("DROP sonrası TABLE, INDEX veya VIEW bekleniyordu")
        ie = False
        if self.accept("kw", "IF"):
            self.expect("kw", "EXISTS"); ie = True
        name = self.table_name() if kind[1] == "TABLE" else self.ident()
        if kind[1] == "INDEX" and self.accept("kw", "ON"):
            self.table_name()
        return ("drop_" + kind[1].lower(), name, ie)

    def alter(self):
        self.next(); self.expect("kw", "TABLE")
        name = self.table_name()
        self.expect("kw", "ADD")
        self.word("COLUMN")
        return ("alter_add", name, self.column_def())

    # ---- DML
    def insert(self):
        self.next(); self.expect("kw", "INTO")
        name, cols = self.table_name(), None
        if self.at("op", "(") and not self.at("kw", "SELECT", 1):
            self.next()
            cols = [self.ident()]
            while self.accept("op", ","):
                cols.append(self.ident())
            self.expect("op", ")")
        if self.at("kw", "SELECT"):
            return ("insert", name, cols, ("select", self.select()))
        self.expect("kw", "VALUES")
        rows = []
        while True:
            self.expect("op", "(")
            r = [self.expr()]
            while self.accept("op", ","):
                r.append(self.expr())
            self.expect("op", ")")
            rows.append(r)
            if not self.accept("op", ","):
                break
        return ("insert", name, cols, ("values", rows))

    def update(self):
        self.next()
        name = self.table_name()
        self.expect("kw", "SET")
        sets = []
        while True:
            c = self.ident()
            if self.accept("op", "."):
                c = self.ident()
            self.expect("op", "=")
            sets.append((c, self.expr()))
            if not self.accept("op", ","):
                break
        where = self.expr() if self.accept("kw", "WHERE") else None
        return ("update", name, sets, where)

    def delete(self):
        self.next()
        self.accept("kw", "FROM")
        name = self.table_name()
        where = self.expr() if self.accept("kw", "WHERE") else None
        return ("delete", name, where)

    # ---- SELECT
    def select(self):
        self.expect("kw", "SELECT")
        q = {"distinct": False, "top": None, "items": [], "from": None, "where": None,
             "group": [], "having": None, "order": [], "limit": None, "offset": None}
        if self.accept("kw", "DISTINCT"):
            q["distinct"] = True
        if self.accept("kw", "TOP"):
            if self.accept("op", "("):
                q["top"] = self.count_value(); self.expect("op", ")")
            else:
                q["top"] = self.count_value()
        while True:
            if self.accept("op", "*"):
                q["items"].append((("star", None), None))
            elif self.at("id") and self.at("op", ".", 1) and self.at("op", "*", 2):
                qual = self.ident(); self.next(); self.next()
                q["items"].append((("star", qual), None))
            else:
                e = self.expr()
                alias = None
                if self.accept("kw", "AS"):
                    alias = self.ident() if not self.at("lit") else str(self.next()[1])
                elif self.at("id"):
                    alias = self.ident()
                q["items"].append((e, alias))
            if not self.accept("op", ","):
                break
        if self.accept("kw", "FROM"):
            q["from"] = self.from_clause()
        if self.accept("kw", "WHERE"):
            q["where"] = self.expr()
        if self.accept("kw", "GROUP"):
            self.expect("kw", "BY")
            q["group"] = [self.expr()]
            while self.accept("op", ","):
                q["group"].append(self.expr())
        if self.accept("kw", "HAVING"):
            q["having"] = self.expr()
        if self.accept("kw", "ORDER"):
            self.expect("kw", "BY")
            while True:
                e = self.expr()
                desc = bool(self.accept("kw", "DESC"))
                if not desc:
                    self.accept("kw", "ASC")
                q["order"].append((e, desc))
                if not self.accept("op", ","):
                    break
        if self.accept("kw", "LIMIT"):
            q["limit"] = self.count_value()
            if self.accept("kw", "OFFSET"):
                q["offset"] = self.count_value()
        elif self.accept("kw", "OFFSET"):
            q["offset"] = self.count_value()
            self.word("ROWS", "ROW")
            if self.word("FETCH"):
                self.word("NEXT", "FIRST")
                q["limit"] = self.count_value()
                self.word("ROWS", "ROW"); self.word("ONLY")
        if q["top"] is not None and q["limit"] is None:
            q["limit"] = q["top"]
        return q

    def count_value(self):
        v = self.expect("lit")[1]
        if not isinstance(v, int) or v < 0:
            raise DBError("Pozitif tam sayı bekleniyordu")
        return v

    def from_clause(self):
        left = self.table_primary()
        while True:
            if self.accept("op", ","):
                left = ("join", "CROSS", left, self.table_primary(), None)
                continue
            if self.accept("kw", "CROSS"):
                self.expect("kw", "JOIN")
                left = ("join", "CROSS", left, self.table_primary(), None)
                continue
            kind = None
            if self.accept("kw", "INNER"):
                self.expect("kw", "JOIN"); kind = "INNER"
            elif self.accept("kw", "LEFT"):
                self.accept("kw", "OUTER"); self.expect("kw", "JOIN"); kind = "LEFT"
            elif self.accept("kw", "RIGHT"):
                self.accept("kw", "OUTER"); self.expect("kw", "JOIN"); kind = "RIGHT"
            elif self.accept("kw", "FULL"):
                self.accept("kw", "OUTER"); self.expect("kw", "JOIN"); kind = "FULL"
            elif self.accept("kw", "JOIN"):
                kind = "INNER"
            if not kind:
                return left
            right = self.table_primary()
            self.expect("kw", "ON")
            left = ("join", kind, left, right, self.expr())

    def table_primary(self):
        if self.accept("op", "("):
            sel = self.select()
            self.expect("op", ")")
            alias = self.alias_opt()
            if not alias:
                raise DBError("Alt sorgu için takma ad gerekli: (SELECT ...) AS x")
            return ("subquery", sel, alias)
        name = self.table_name()
        return ("table", name, self.alias_opt())

    def alias_opt(self):
        if self.accept("kw", "AS"):
            return self.ident()
        if self.at("id"):
            return self.ident()
        return None

    # ---- ifadeler
    def expr(self):
        left = self.and_expr()
        while self.accept("kw", "OR"):
            left = ("bin", "OR", left, self.and_expr())
        return left

    def and_expr(self):
        left = self.not_expr()
        while self.accept("kw", "AND"):
            left = ("bin", "AND", left, self.not_expr())
        return left

    def not_expr(self):
        if self.accept("kw", "NOT"):
            return ("not", self.not_expr())
        return self.predicate()

    def predicate(self):
        left = self.add_expr()
        tok = self.peek()
        if tok[0] == "op" and tok[1] in ("=", "<>", "!=", "<", ">", "<=", ">="):
            self.next()
            return ("bin", "<>" if tok[1] == "!=" else tok[1], left, self.add_expr())
        if self.accept("kw", "IS"):
            neg = bool(self.accept("kw", "NOT"))
            self.expect("kw", "NULL")
            return ("not", ("isnull", left)) if neg else ("isnull", left)
        neg = bool(self.accept("kw", "NOT"))
        e = None
        if self.accept("kw", "LIKE"):
            e = ("bin", "LIKE", left, self.add_expr())
        elif self.accept("kw", "BETWEEN"):
            lo = self.add_expr()
            self.expect("kw", "AND")
            e = ("between", left, lo, self.add_expr())
        elif self.accept("kw", "IN"):
            self.expect("op", "(")
            if self.at("kw", "SELECT"):
                e = ("insub", left, self.select())
            else:
                vals = [self.expr()]
                while self.accept("op", ","):
                    vals.append(self.expr())
                e = ("in", left, vals)
            self.expect("op", ")")
        elif neg:
            raise DBError("NOT sonrası LIKE, IN veya BETWEEN bekleniyordu")
        else:
            return left
        return ("not", e) if neg else e

    def add_expr(self):
        left = self.mul_expr()
        while self.at("op", "+") or self.at("op", "-") or self.at("op", "||"):
            op = self.next()[1]
            left = ("bin", op, left, self.mul_expr())
        return left

    def mul_expr(self):
        left = self.unary()
        while self.at("op", "*") or self.at("op", "/") or self.at("op", "%"):
            op = self.next()[1]
            left = ("bin", op, left, self.unary())
        return left

    def unary(self):
        if self.accept("op", "-"):
            return ("neg", self.unary())
        if self.accept("op", "+"):
            return self.unary()
        return self.primary()

    def primary(self):
        tok = self.next()
        kind, val = tok[0], tok[1]
        if kind == "lit":
            return ("lit", val)
        if tok[:2] == ("kw", "NULL"):
            return ("lit", None)
        if tok[:2] == ("op", "("):
            if self.at("kw", "SELECT"):
                sel = self.select(); self.expect("op", ")")
                return ("subq", sel)
            e = self.expr(); self.expect("op", ")")
            return e
        if tok[:2] == ("kw", "CASE"):
            return self.case_expr()
        if tok[:2] == ("kw", "EXISTS"):
            self.expect("op", "(")
            sel = self.select(); self.expect("op", ")")
            return ("exists", sel)
        if kind == "kw" and val in ("LEFT", "RIGHT") and self.at("op", "("):
            return self.func_call(val)
        if kind == "id":
            up = val.upper()
            if self.at("op", "("):
                return self.func_call(up)
            if up in ("SYSDATE", "CURRENT_TIMESTAMP", "CURRENT_DATE"):
                return ("func", "GETDATE" if up != "CURRENT_DATE" else "CURRENT_DATE", [], False)
            if self.accept("op", "."):
                return ("col", val, self.ident())
            return ("col", None, val)
        raise DBError(f"Beklenmeyen: {val if kind != 'eof' else 'komut sonu'}")

    def func_call(self, name):
        self.expect("op", "(")
        if name == "CAST":
            e = self.expr(); self.expect("kw", "AS")
            t = self.ident().upper()
            if self.accept("op", "("):
                while not self.accept("op", ")"):
                    self.next()
            self.expect("op", ")")
            return ("func", "CAST", [e, ("lit", t)], False)
        if name == "CONVERT":
            t = self.ident().upper()
            if self.accept("op", "("):
                while not self.accept("op", ")"):
                    self.next()
            self.expect("op", ",")
            e = self.expr(); self.expect("op", ")")
            return ("func", "CAST", [e, ("lit", t)], False)
        distinct = bool(self.accept("kw", "DISTINCT"))
        args = []
        if self.accept("op", "*"):
            args = [("star", None)]
        elif not self.at("op", ")"):
            args = [self.expr()]
            while self.accept("op", ","):
                args.append(self.expr())
        self.expect("op", ")")
        return ("func", name, args, distinct)

    def case_expr(self):
        base = None
        if not self.at("kw", "WHEN"):
            base = self.expr()
        whens = []
        while self.accept("kw", "WHEN"):
            cond = self.expr()
            self.expect("kw", "THEN")
            whens.append((cond, self.expr()))
        if not whens:
            raise DBError("CASE içinde en az bir WHEN gerekli")
        other = self.expr() if self.accept("kw", "ELSE") else ("lit", None)
        self.expect("kw", "END")
        return ("case", base, whens, other)

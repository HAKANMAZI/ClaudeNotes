"""Parser: tokenlardan sözdizimi ağacı (AST) üretir."""
from ..errors import DBError
from .tokenizer import tokenize

class Parser:
    def __init__(self, sql):
        self.t, self.i = tokenize(sql), 0

    def peek(self, k=0):
        return self.t[self.i + k]

    def next(self):
        tok = self.t[self.i]; self.i += 1; return tok

    def accept(self, kind, val=None):
        tok = self.peek()
        if tok[0] == kind and (val is None or tok[1] == val):
            self.i += 1; return tok
        return None

    def expect(self, kind, val=None):
        tok = self.accept(kind, val)
        if not tok:
            raise DBError(f"Beklenen: {val or kind}, bulunan: {self.peek()[1]!r}")
        return tok

    def ident(self):
        tok = self.next()
        if tok[0] == "id":
            return tok[1]
        raise DBError(f"İsim bekleniyordu, bulunan: {tok[1]!r}")

    def statements(self):
        out = []
        while self.peek()[0] != "eof":
            if self.accept("op", ";"):
                continue
            out.append(self.statement())
            if self.peek()[0] != "eof":
                self.expect("op", ";")
        return out

    def statement(self):
        kw = self.peek()[1]
        if kw == "SELECT": return self.select()
        if kw == "INSERT": return self.insert()
        if kw == "CREATE": return self.create()
        if kw == "DROP":
            self.next(); self.expect("kw", "TABLE"); return ("drop", self.ident())
        if kw == "UPDATE": return self.update()
        if kw == "DELETE": return self.delete()
        if kw in ("BEGIN", "COMMIT", "ROLLBACK"):
            self.next(); self.accept("kw", "TRANSACTION"); return (kw.lower(),)
        raise DBError(f"Bilinmeyen komut: {kw!r}")

    def create(self):
        self.next(); self.expect("kw", "TABLE")
        name = self.ident(); self.expect("op", "(")
        cols = []
        while True:
            cname = self.ident()
            t = self.ident().upper()
            t = {"INTEGER": "INT", "BIGINT": "INT", "FLOAT": "REAL", "DECIMAL": "REAL",
                 "NUMBER": "REAL", "VARCHAR": "TEXT", "NVARCHAR": "TEXT",
                 "VARCHAR2": "TEXT", "CHAR": "TEXT"}.get(t, t)
            if t not in ("INT", "REAL", "TEXT"):
                raise DBError(f"Desteklenmeyen tip: {t}")
            if self.accept("op", "("):        # VARCHAR(50) gibi
                self.next(); self.expect("op", ")")
            col = {"name": cname, "type": t}
            while True:
                if self.accept("kw", "PRIMARY"):
                    self.expect("kw", "KEY"); col["pk"] = True
                elif self.accept("kw", "NOT"):
                    self.expect("kw", "NULL"); col["notnull"] = True
                else:
                    break
            cols.append(col)
            if not self.accept("op", ","):
                break
        self.expect("op", ")")
        return ("create", name, cols)

    def insert(self):
        self.next(); self.expect("kw", "INTO")
        name, cols = self.ident(), None
        if self.accept("op", "("):
            cols = [self.ident()]
            while self.accept("op", ","):
                cols.append(self.ident())
            self.expect("op", ")")
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
        return ("insert", name, cols, rows)

    def select(self):
        self.next()
        top = None
        if self.accept("kw", "TOP"):
            top = self.expect("lit")[1]
        items = []
        while True:
            if self.accept("op", "*"):
                items.append(("*", None))
            else:
                e = self.expr()
                alias = self.ident() if self.accept("kw", "AS") else None
                items.append((e, alias))
            if not self.accept("op", ","):
                break
        table = None
        if self.accept("kw", "FROM"):
            table = self.ident()
        where = self.expr() if self.accept("kw", "WHERE") else None
        group = []
        if self.accept("kw", "GROUP"):
            self.expect("kw", "BY")
            group = [self.expr()]
            while self.accept("op", ","):
                group.append(self.expr())
        order = []
        if self.accept("kw", "ORDER"):
            self.expect("kw", "BY")
            while True:
                e = self.expr()
                desc = bool(self.accept("kw", "DESC"))
                if not desc:
                    self.accept("kw", "ASC")
                order.append((e, desc))
                if not self.accept("op", ","):
                    break
        limit = top
        if self.accept("kw", "LIMIT"):
            limit = self.expect("lit")[1]
        return ("select", items, table, where, group, order, limit)

    def update(self):
        self.next(); name = self.ident(); self.expect("kw", "SET")
        sets = []
        while True:
            c = self.ident(); self.expect("op", "="); sets.append((c, self.expr()))
            if not self.accept("op", ","):
                break
        where = self.expr() if self.accept("kw", "WHERE") else None
        return ("update", name, sets, where)

    def delete(self):
        self.next(); self.expect("kw", "FROM"); name = self.ident()
        where = self.expr() if self.accept("kw", "WHERE") else None
        return ("delete", name, where)

    # İfadeler: OR < AND < NOT < karşılaştırma < + - < * / % < birim
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
        return self.cmp_expr()

    def cmp_expr(self):
        left = self.add_expr()
        tok = self.peek()
        if tok[0] == "op" and tok[1] in ("=", "<>", "!=", "<", ">", "<=", ">="):
            self.next()
            return ("bin", "<>" if tok[1] == "!=" else tok[1], left, self.add_expr())
        if self.accept("kw", "IS"):
            neg = bool(self.accept("kw", "NOT")); self.expect("kw", "NULL")
            e = ("isnull", left)
            return ("not", e) if neg else e
        neg = bool(self.accept("kw", "NOT"))
        if self.accept("kw", "LIKE"):
            e = ("bin", "LIKE", left, self.add_expr())
            return ("not", e) if neg else e
        if self.accept("kw", "IN"):
            self.expect("op", "(")
            vals = [self.expr()]
            while self.accept("op", ","):
                vals.append(self.expr())
            self.expect("op", ")")
            e = ("in", left, vals)
            return ("not", e) if neg else e
        if neg:
            raise DBError("NOT sonrası LIKE veya IN bekleniyordu")
        return left

    def add_expr(self):
        left = self.mul_expr()
        while self.peek() in (("op", "+"), ("op", "-")):
            op = self.next()[1]; left = ("bin", op, left, self.mul_expr())
        return left

    def mul_expr(self):
        left = self.unary()
        while self.peek() in (("op", "*"), ("op", "/"), ("op", "%")):
            op = self.next()[1]; left = ("bin", op, left, self.unary())
        return left

    def unary(self):
        if self.accept("op", "-"):
            return ("bin", "-", ("lit", 0), self.unary())
        tok = self.next()
        if tok[0] == "lit":
            return ("lit", tok[1])
        if tok == ("kw", "NULL"):
            return ("lit", None)
        if tok == ("op", "("):
            e = self.expr(); self.expect("op", ")"); return e
        if tok[0] == "id":
            if self.accept("op", "("):
                fname = tok[1].upper()
                if self.accept("op", "*"):
                    args = [("star",)]
                else:
                    args = [self.expr()]
                    while self.accept("op", ","):
                        args.append(self.expr())
                self.expect("op", ")")
                return ("func", fname, args)
            if self.accept("op", "."):          # tablo.kolon
                return ("col", self.ident())
            return ("col", tok[1])
        raise DBError(f"Beklenmeyen: {tok[1]!r}")



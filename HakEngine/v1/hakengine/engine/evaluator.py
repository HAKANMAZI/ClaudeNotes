"""İfade değerlendirme: WHERE, SELECT ifadeleri ve fonksiyonlar."""
import re
from ..errors import DBError

AGGS = {"COUNT", "SUM", "AVG", "MIN", "MAX"}


def like_to_re(p):
    return re.compile("^" + "".join(".*" if ch == "%" else "." if ch == "_" else re.escape(ch)
                                    for ch in p) + "$", re.I | re.S)


def evaluate(e, row, cols, group=None):
    k = e[0]
    if k == "lit":
        return e[1]
    if k == "col":
        try:
            return row[cols.index(e[1])]
        except ValueError:
            lower = [c.lower() for c in cols]
            if e[1].lower() in lower:
                return row[lower.index(e[1].lower())]
            raise DBError(f"Bilinmeyen kolon: {e[1]}")
    if k == "not":
        v = evaluate(e[1], row, cols, group)
        return None if v is None else not v
    if k == "isnull":
        return evaluate(e[1], row, cols, group) is None
    if k == "in":
        v = evaluate(e[1], row, cols, group)
        return v in [evaluate(x, row, cols, group) for x in e[2]]
    if k == "func":
        name, args = e[1], e[2]
        if name in AGGS:
            if group is None:
                raise DBError(f"{name} burada kullanılamaz")
            if args[0] == ("star",):
                return len(group)
            vals = [evaluate(args[0], r, cols) for r in group]
            vals = [v for v in vals if v is not None]
            if name == "COUNT": return len(vals)
            if not vals: return None
            if name == "SUM": return sum(vals)
            if name == "AVG": return sum(vals) / len(vals)
            if name == "MIN": return min(vals)
            if name == "MAX": return max(vals)
        vals = [evaluate(a, row, cols, group) for a in args]
        if name in ("UPPER", "UCASE"): return None if vals[0] is None else str(vals[0]).upper()
        if name in ("LOWER", "LCASE"): return None if vals[0] is None else str(vals[0]).lower()
        if name in ("LEN", "LENGTH"): return None if vals[0] is None else len(str(vals[0]))
        if name == "ABS": return None if vals[0] is None else abs(vals[0])
        if name == "ROUND": return None if vals[0] is None else round(vals[0], int(vals[1]) if len(vals) > 1 else 0)
        if name in ("ISNULL", "NVL", "COALESCE"):
            return next((v for v in vals if v is not None), None)
        raise DBError(f"Bilinmeyen fonksiyon: {name}")
    if k == "bin":
        op = e[1]
        a = evaluate(e[2], row, cols, group)
        if op == "AND" and a is False: return False
        if op == "OR" and a is True: return True
        b = evaluate(e[3], row, cols, group)
        if op == "AND": return None if a is None or b is None else bool(a and b)
        if op == "OR": return None if a is None or b is None else bool(a or b)
        if a is None or b is None:
            return None
        try:
            if op == "+": return a + b if not (isinstance(a, str) or isinstance(b, str)) else str(a) + str(b)
            if op == "-": return a - b
            if op == "*": return a * b
            if op == "/":
                if b == 0: raise DBError("Sıfıra bölme hatası")
                return a // b if isinstance(a, int) and isinstance(b, int) else a / b
            if op == "%": return a % b
            if op == "=": return a == b
            if op == "<>": return a != b
            if op == "<": return a < b
            if op == ">": return a > b
            if op == "<=": return a <= b
            if op == ">=": return a >= b
            if op == "LIKE": return bool(like_to_re(str(b)).match(str(a)))
        except TypeError:
            raise DBError(f"Uyumsuz tipler: {a!r} {op} {b!r}")
    raise DBError(f"Değerlendirilemeyen ifade: {e}")


def has_agg(e):
    if e[0] == "func" and e[1] in AGGS:
        return True
    return any(has_agg(x) for x in e[1:] if isinstance(x, tuple)) or \
        any(has_agg(x) for x in (e[2] if e[0] in ("func", "in") else []) if isinstance(x, tuple))


def expr_name(e):
    if e[0] == "col": return e[1]
    if e[0] == "lit": return str(e[1])
    if e[0] == "func":
        return e[1] + "(" + ", ".join("*" if a == ("star",) else expr_name(a) for a in e[2]) + ")"
    if e[0] == "bin": return f"{expr_name(e[2])} {e[1]} {expr_name(e[3])}"
    return "ifade"


def sort_key(v):
    return (0, 0) if v is None else (1, v) if not isinstance(v, str) else (2, v)



"""İfade değerlendirme.

Scope : Bir satırdaki kolonların listesi. (tablo_takma_adı, kolon) -> konum.
Env   : Değerlendirme ortamı: scope + satır + (gruplamada) grup satırları
        + dış sorgu ortamı (ilişkili alt sorgular için) + executor.
"""
import re, math, datetime
from ..errors import DBError
from ..storage.table import TYPE_MAP

AGGS = {"COUNT", "SUM", "AVG", "MIN", "MAX"}
_AMBIG = -1


class Scope:
    def __init__(self, cols):
        self.cols = cols                        # [(qual, name, görünen_ad)] küçük harf
        self.by_q, self.by_n = {}, {}
        for i, (q, n, _) in enumerate(cols):
            self.by_q.setdefault((q, n), i)
            self.by_n[n] = i if n not in self.by_n else _AMBIG

    def __add__(self, other):
        return Scope(self.cols + other.cols)

    def has(self, q, n):
        if q:
            return (q.lower(), n.lower()) in self.by_q
        return n.lower() in self.by_n

    def find(self, q, n):
        if q:
            return self.by_q.get((q.lower(), n.lower()))
        i = self.by_n.get(n.lower())
        if i == _AMBIG:
            raise DBError(f"Belirsiz kolon: '{n}'. Tablo adıyla yazın, örneğin t.{n}")
        return i


class Env:
    __slots__ = ("scope", "row", "group", "outer", "ex")

    def __init__(self, scope, row, group=None, outer=None, ex=None):
        self.scope, self.row, self.group, self.outer, self.ex = scope, row, group, outer, ex


# ---------------------------------------------------------------- ağaç yardımcıları
def walk(e):
    """İfade düğümlerini gezer. Alt sorgu SELECT'lerinin içine girmez."""
    if isinstance(e, tuple):
        if e and isinstance(e[0], str):
            yield e
        for x in e[1:] if e and isinstance(e[0], str) else e:
            yield from walk(x)
    elif isinstance(e, list):
        for x in e:
            yield from walk(x)


def has_agg(e):
    return any(n[0] == "func" and n[1] in AGGS for n in walk(e))


def col_refs(e):
    return [n for n in walk(e) if n[0] == "col"]


def has_subquery(e):
    return any(n[0] in ("subq", "insub", "exists") for n in walk(e))


def is_const(e):
    return not any(n[0] in ("col", "subq", "insub", "exists", "star") or
                   (n[0] == "func" and n[1] in AGGS) for n in walk(e))


def conjuncts(e):
    if e is None:
        return []
    if e[0] == "bin" and e[1] == "AND":
        return conjuncts(e[2]) + conjuncts(e[3])
    return [e]


def expr_name(e):
    k = e[0]
    if k == "col":
        return e[2] if not e[1] else f"{e[1]}.{e[2]}"
    if k == "lit":
        return "NULL" if e[1] is None else repr(e[1]) if isinstance(e[1], str) else str(e[1])
    if k == "func":
        inner = ", ".join("*" if a[0] == "star" else expr_name(a) for a in e[2])
        return f"{e[1]}({'DISTINCT ' if e[3] else ''}{inner})"
    if k == "bin":
        return f"{expr_name(e[2])} {e[1]} {expr_name(e[3])}"
    if k == "neg":
        return f"-{expr_name(e[1])}"
    if k == "not":
        return f"NOT {expr_name(e[1])}"
    if k == "isnull":
        return f"{expr_name(e[1])} IS NULL"
    if k == "between":
        return f"{expr_name(e[1])} BETWEEN {expr_name(e[2])} AND {expr_name(e[3])}"
    if k == "in":
        return f"{expr_name(e[1])} IN ({', '.join(expr_name(x) for x in e[2])})"
    if k == "insub":
        return f"{expr_name(e[1])} IN (alt sorgu)"
    if k == "exists":
        return "EXISTS (alt sorgu)"
    if k == "subq":
        return "(alt sorgu)"
    if k == "case":
        return "CASE"
    return "ifade"


_TR_ALPHABET = "aâbcçdefgğhıiîjklmnoöprsştuüûvwxqyz"
_TR_RANK = {ch: i for i, ch in enumerate(_TR_ALPHABET)}
_TR_LOWER = str.maketrans({"I": "ı", "İ": "i"})


def tr_key(s):
    """Türkçe alfabe sırası, büyük/küçük harf duyarsız (SQL Server'daki Turkish_CI_AS gibi)."""
    low = s.translate(_TR_LOWER).lower()
    return tuple(_TR_RANK.get(ch, 100 + ord(ch)) for ch in low), s


def sort_key(v):
    if v is None:
        return (0, 0)
    if isinstance(v, str):
        return (2, tr_key(v))
    return (1, v)


def header_name(e):
    return e[2] if e[0] == "col" else expr_name(e)


# ---------------------------------------------------------------- değerlendirme
_like_cache = {}


def _like(pattern):
    r = _like_cache.get(pattern)
    if r is None:
        r = re.compile("^" + "".join(".*" if ch == "%" else "." if ch == "_" else re.escape(ch)
                                     for ch in pattern) + "$", re.I | re.S)
        _like_cache[pattern] = r
    return r


def _num(v):
    if isinstance(v, str):
        try:
            return float(v) if any(c in v for c in ".eE") else int(v)
        except ValueError:
            raise DBError(f"Metin sayıya çevrilemedi: {v!r}")
    return v


def _align(a, b):
    if isinstance(a, str) != isinstance(b, str):
        return _num(a), _num(b)
    return a, b


def evaluate(e, env):
    k = e[0]
    if k == "lit":
        return e[1]
    if k == "col":
        i = env.scope.find(e[1], e[2]) if env.scope is not None else None
        if i is not None:
            return env.row[i]
        if env.outer is not None:
            if env.ex is not None:
                env.ex.outer_hits += 1
            return evaluate(e, env.outer)
        raise DBError(f"Bilinmeyen kolon: {expr_name(e)}")
    if k == "bin":
        return _binary(e, env)
    if k == "not":
        v = evaluate(e[1], env)
        return None if v is None else not v
    if k == "neg":
        v = evaluate(e[1], env)
        return None if v is None else -_num(v)
    if k == "isnull":
        return evaluate(e[1], env) is None
    if k == "between":
        v, lo, hi = evaluate(e[1], env), evaluate(e[2], env), evaluate(e[3], env)
        if v is None or lo is None or hi is None:
            return None
        v1, lo = _align(v, lo)
        v2, hi = _align(v, hi)
        return lo <= v1 and v2 <= hi
    if k == "in":
        v = evaluate(e[1], env)
        if v is None:
            return None
        vals = [evaluate(x, env) for x in e[2]]
        return any(x is not None and _eq(v, x) for x in vals)
    if k == "insub":
        v = evaluate(e[1], env)
        if v is None:
            return None
        _, rows = env.ex.subquery(e[2], env)
        return any(r[0] is not None and _eq(v, r[0]) for r in rows)
    if k == "exists":
        _, rows = env.ex.subquery(e[1], env)
        return len(rows) > 0
    if k == "subq":
        _, rows = env.ex.subquery(e[1], env)
        if not rows:
            return None
        if len(rows) > 1:
            raise DBError("Alt sorgu birden fazla satır döndürdü")
        return rows[0][0]
    if k == "case":
        base = evaluate(e[1], env) if e[1] is not None else None
        for cond, res in e[2]:
            if e[1] is not None:
                c = evaluate(cond, env)
                if base is not None and c is not None and _eq(base, c):
                    return evaluate(res, env)
            elif evaluate(cond, env) is True:
                return evaluate(res, env)
        return evaluate(e[3], env)
    if k == "func":
        return _func(e, env)
    if k == "star":
        raise DBError("'*' burada kullanılamaz")
    raise DBError(f"Değerlendirilemeyen ifade: {k}")


def _eq(a, b):
    a, b = _align(a, b)
    return a == b


def _binary(e, env):
    op = e[1]
    a = evaluate(e[2], env)
    if op == "AND":
        if a is False:
            return False
        b = evaluate(e[3], env)
        if b is False:
            return False
        return None if a is None or b is None else True
    if op == "OR":
        if a is True:
            return True
        b = evaluate(e[3], env)
        if b is True:
            return True
        return None if a is None or b is None else False
    b = evaluate(e[3], env)
    if op == "||":
        return ("" if a is None else _text(a)) + ("" if b is None else _text(b))
    if a is None or b is None:
        return None
    if op == "+" and (isinstance(a, str) or isinstance(b, str)):
        if isinstance(a, str) and isinstance(b, str):
            return a + b
        a, b = _num(a), _num(b)
    if op == "LIKE":
        return bool(_like(_text(b)).match(_text(a)))
    a, b = _align(a, b)
    try:
        if op == "+": return a + b
        if op == "-": return a - b
        if op == "*": return a * b
        if op == "/":
            if b == 0:
                raise DBError("Sıfıra bölme hatası")
            return int(a / b) if isinstance(a, int) and isinstance(b, int) else a / b
        if op == "%":
            if b == 0:
                raise DBError("Sıfıra bölme hatası")
            return math.fmod(a, b) if isinstance(a, float) or isinstance(b, float) else int(math.fmod(a, b))
        if op == "=": return a == b
        if op == "<>": return a != b
        if op == "<": return a < b
        if op == ">": return a > b
        if op == "<=": return a <= b
        if op == ">=": return a >= b
    except TypeError:
        raise DBError(f"Uyumsuz tipler: {a!r} {op} {b!r}")
    raise DBError(f"Bilinmeyen operatör: {op}")


def _text(v):
    if isinstance(v, float) and v == int(v) and abs(v) < 1e15:
        return str(int(v))
    return str(v)


def _date_part(v, i):
    if v is None:
        return None
    try:
        return int(str(v)[:10].split("-")[i])
    except (ValueError, IndexError):
        raise DBError(f"Tarih anlaşılamadı: {v!r} (beklenen biçim YYYY-AA-GG)")


def _aggregate(e, env):
    name, args, distinct = e[1], e[2], e[3]
    if env.group is None:
        raise DBError(f"{name} burada kullanılamaz (WHERE veya ON içinde toplama fonksiyonu olmaz)")
    if args and args[0][0] == "star":
        return len(env.group)
    if len(args) != 1:
        raise DBError(f"{name} tek argüman alır")
    vals = []
    for r in env.group:
        v = evaluate(args[0], Env(env.scope, r, None, env.outer, env.ex))
        if v is not None:
            vals.append(v)
    if distinct:
        seen, uniq = set(), []
        for v in vals:
            if v not in seen:
                seen.add(v); uniq.append(v)
        vals = uniq
    if name == "COUNT":
        return len(vals)
    if not vals:
        return None
    if name in ("SUM", "AVG"):
        vals = [_num(v) for v in vals]
        s = sum(vals)
        return s if name == "SUM" else s / len(vals)
    try:
        return min(vals) if name == "MIN" else max(vals)
    except TypeError:
        return (min if name == "MIN" else max)(vals, key=sort_key)


def _func(e, env):
    name = e[1]
    if name in AGGS:
        return _aggregate(e, env)
    a = [evaluate(x, env) for x in e[2]]
    n = len(a)

    def need(k):
        if n < k:
            raise DBError(f"{name} en az {k} argüman alır")

    if name in ("ISNULL", "NVL", "COALESCE", "IFNULL"):
        return next((v for v in a if v is not None), None)
    if name == "NULLIF":
        need(2); return None if a[0] is not None and a[1] is not None and _eq(a[0], a[1]) else a[0]
    if name == "IIF":
        need(3); return a[1] if a[0] is True else a[2]
    if name == "CONCAT":
        return "".join("" if v is None else _text(v) for v in a)
    if name in ("GETDATE", "NOW", "SYSDATETIME"):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if name == "CURRENT_DATE":
        return datetime.date.today().isoformat()
    if name == "CAST":
        t = TYPE_MAP.get(a[1])
        if t is None:
            raise DBError(f"Bilinmeyen tip: {a[1]}")
        if a[0] is None:
            return None
        try:
            if t == "INT":
                return int(float(a[0])) if isinstance(a[0], str) else int(a[0])
            if t == "REAL":
                return float(a[0])
            return _text(a[0])
        except ValueError:
            raise DBError(f"{a[0]!r} değeri {a[1]} tipine çevrilemedi")
    need(1)
    v = a[0]
    if v is None:
        return None
    if name in ("UPPER", "UCASE"): return _text(v).upper()
    if name in ("LOWER", "LCASE"): return _text(v).lower()
    if name in ("LEN", "LENGTH"): return len(_text(v))
    if name == "TRIM": return _text(v).strip()
    if name == "LTRIM": return _text(v).lstrip()
    if name == "RTRIM": return _text(v).rstrip()
    if name == "REVERSE": return _text(v)[::-1]
    if name in ("SUBSTRING", "SUBSTR"):
        need(2)
        start = max(int(a[1]) - 1, 0)
        return _text(v)[start:start + int(a[2])] if n > 2 else _text(v)[start:]
    if name == "LEFT": need(2); return _text(v)[:int(a[1])]
    if name == "RIGHT": need(2); return _text(v)[-int(a[1]):] if int(a[1]) > 0 else ""
    if name == "REPLACE": need(3); return _text(v).replace(_text(a[1]), _text(a[2]))
    if name == "CHARINDEX": need(2); return _text(a[1]).find(_text(v)) + 1
    if name == "INSTR": need(2); return _text(v).find(_text(a[1])) + 1
    if name == "ABS": return abs(_num(v))
    if name == "ROUND":
        r = round(_num(v), int(a[1]) if n > 1 else 0)
        return float(r) if isinstance(v, float) else r
    if name == "FLOOR": return math.floor(_num(v))
    if name in ("CEILING", "CEIL"): return math.ceil(_num(v))
    if name == "SQRT": return math.sqrt(_num(v))
    if name in ("POWER", "POW"): need(2); return _num(v) ** _num(a[1])
    if name == "SIGN": x = _num(v); return (x > 0) - (x < 0)
    if name == "YEAR": return _date_part(v, 0)
    if name == "MONTH": return _date_part(v, 1)
    if name == "DAY": return _date_part(v, 2)
    raise DBError(f"Bilinmeyen fonksiyon: {name}")

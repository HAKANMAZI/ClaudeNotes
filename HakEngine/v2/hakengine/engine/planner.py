"""Sorgu planlayıcı: bir tabloya en hızlı nasıl erişileceğini seçer.

WHERE koşulu AND ile parçalara ayrılır. İndeksli bir kolonla sabit karşılaştırma varsa:
  kolon = sabit                 -> Index Seek          (en iyi; unique ise tek satır)
  kolon IN (sabit, ...)         -> Index Seek (çoklu)
  kolon > < >= <= / BETWEEN     -> Index Range Scan
Hiçbiri yoksa                   -> Table Scan

Seçilen yol sadece okunacak satırları azaltır. Tam WHERE koşulu yine de her satıra uygulanır;
bu yüzden plan yanlış seçilse bile sonuç hep doğrudur.
"""
from ..errors import DBError
from ..storage.table import coerce_value
from ..storage.btree import sort_key
from .evaluator import Env, evaluate, is_const, expr_name

FLIP = {"=": "=", "<": ">", ">": "<", "<=": ">=", ">=": "<="}


def _const(e):
    return evaluate(e, Env(None, []))


def _col_index(t, scope, e):
    if e[0] != "col" or not scope.has(e[1], e[2]):
        return None
    return t.index_on(e[2])


def _val(t, idx, v):
    try:
        return coerce_value(t.columns[idx.colidx], v)
    except DBError:
        return None


def choose_access(t, scope, conj):
    info = {}                                   # indeks adı -> {idx, eq, lo, hi}

    def slot(idx):
        return info.setdefault(idx.name, {"idx": idx, "eq": None, "lo": None, "hi": None})

    for c in conj:
        if c[0] == "bin" and c[1] in FLIP:
            op, a, b = c[1], c[2], c[3]
            idx = _col_index(t, scope, a) if is_const(b) else None
            if idx is None and is_const(a):
                idx = _col_index(t, scope, b)
                if idx is not None:
                    a, b, op = b, a, FLIP[op]
            if idx is None:
                continue
            v = _val(t, idx, _const(b))
            if v is None:
                continue
            s = slot(idx)
            if op == "=":
                s["eq"] = [v]
            elif op in (">", ">="):
                if s["lo"] is None or sort_key(v) > sort_key(s["lo"][0]):
                    s["lo"] = (v, op == ">=")
            else:
                if s["hi"] is None or sort_key(v) < sort_key(s["hi"][0]):
                    s["hi"] = (v, op == "<=")
        elif c[0] == "between" and is_const(c[2]) and is_const(c[3]):
            idx = _col_index(t, scope, c[1])
            if idx is None:
                continue
            lo, hi = _val(t, idx, _const(c[2])), _val(t, idx, _const(c[3]))
            if lo is None or hi is None:
                continue
            s = slot(idx)
            s["lo"], s["hi"] = (lo, True), (hi, True)
        elif c[0] == "in" and all(is_const(x) for x in c[2]):
            idx = _col_index(t, scope, c[1])
            if idx is None:
                continue
            vals = [_val(t, idx, _const(x)) for x in c[2]]
            vals = [v for v in vals if v is not None]
            s = slot(idx)
            if s["eq"] is None:
                s["eq"] = vals

    best = None
    for s in info.values():
        idx = s["idx"]
        if s["eq"] is not None:
            score = (0 if idx.unique and len(s["eq"]) == 1 else 1, len(s["eq"]))
        elif s["lo"] or s["hi"]:
            score = (2 if s["lo"] and s["hi"] else 3, 0)
        else:
            continue
        if best is None or score < best[0]:
            best = (score, s)
    if best is None:
        return {"kind": "scan"}
    s = best[1]
    if s["eq"] is not None:
        return {"kind": "seek", "index": s["idx"], "values": s["eq"]}
    return {"kind": "range", "index": s["idx"], "lo": s["lo"], "hi": s["hi"]}


def describe(t, plan):
    if plan["kind"] == "scan":
        return f"Table Scan [{t.name}]"
    idx = plan["index"]
    if plan["kind"] == "seek":
        vals = plan["values"]
        cond = f"{idx.column} = {vals[0]!r}" if len(vals) == 1 else f"{idx.column} IN {tuple(vals)!r}"
        return f"Index Seek [{t.name}].[{idx.name}] ({cond})"
    parts = []
    if plan["lo"]:
        parts.append(f"{idx.column} {'>=' if plan['lo'][1] else '>'} {plan['lo'][0]!r}")
    if plan["hi"]:
        parts.append(f"{idx.column} {'<=' if plan['hi'][1] else '<'} {plan['hi'][0]!r}")
    return f"Index Range Scan [{t.name}].[{idx.name}] ({' AND '.join(parts)})"


def access(t, plan):
    """Plana göre (rid, satır) listesi döndürür."""
    if plan["kind"] == "scan":
        return list(t.scan())
    tree = plan["index"].tree
    if plan["kind"] == "seek":
        out, seen = [], set()
        for v in plan["values"]:
            for rid in tree.seek(v):
                if rid not in seen:
                    seen.add(rid)
                    out.append((rid, t.get(rid)))
        return out
    lo, hi = plan["lo"], plan["hi"]
    return [(rid, t.get(rid)) for rid, _ in tree.range(
        lo[0] if lo else None, hi[0] if hi else None,
        lo[1] if lo else True, hi[1] if hi else True)]

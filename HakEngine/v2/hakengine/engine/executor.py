"""SELECT yürütücü.

Adımlar (SQL'in mantıksal işlem sırası):
  FROM / JOIN  ->  WHERE  ->  GROUP BY  ->  HAVING  ->  SELECT  ->  DISTINCT  ->  ORDER BY  ->  OFFSET / TOP

JOIN stratejileri (SQL Server'daki operatörlerin karşılığı):
  Index Nested Loops : sağ tabloda ON kolonunda indeks varsa, sol her satır için indeks araması
  Hash Match         : eşitlikli ON koşulu var ama indeks yoksa, sağ taraf belleğe hash tablosu olarak alınır
  Nested Loops       : diğer durumlar (her sol satır x her sağ satır)

Her adım plan listesine yazılır. EXPLAIN bu listeyi gösterir.
"""
from collections import defaultdict
from ..errors import DBError
from ..sql import Parser
from .evaluator import (Scope, Env, evaluate, has_agg, col_refs, has_subquery, conjuncts,
                        expr_name, header_name, sort_key)
from .planner import choose_access, describe, access


class Executor:
    def __init__(self, db):
        self.db = db
        self.reset()

    def reset(self):
        self.cache, self.plan = {}, {}
        self.outer_hits, self.depth = 0, 0
        self._view_ast = {}

    # ---- plan kaydı
    def note(self, node, text):
        key = (id(node), text)
        if key not in self.plan:
            self.plan[key] = self.depth

    def explain_rows(self):
        return [[i + 1, "    " * (d - 1) + text] for i, ((_, text), d) in enumerate(self.plan.items())]

    # ---- alt sorgu
    def subquery(self, sel, env):
        key = id(sel)
        if key in self.cache:
            return self.cache[key]
        before = self.outer_hits
        res = self.run_select(sel, env)
        if self.outer_hits == before:            # dış sorguya bağlı değil: bir kez çalıştır
            self.cache[key] = res
        return res

    # ---- FROM kaynakları
    def table_scope(self, t, alias):
        q = (alias or t.name).lower()
        return Scope([(q, c.lower(), c) for c in t.cols])

    def source(self, src, outer, conj=None):
        kind = src[0]
        if kind == "join":
            return self.join(src, outer, conj)
        if kind == "subquery":
            self.note(src, f"Alt sorgu [{src[2]}]")
            self.depth += 1
            try:
                headers, rows = self.run_select(src[1], outer)
            finally:
                self.depth -= 1
            return self._scope_from(headers, src[2]), rows
        name, alias = src[1], src[2]
        if name.startswith("sys."):
            headers, rows = self.db.system_table(name)
            self.note(src, f"System Table [{name}]")
            return self._scope_from(headers, alias or name[4:]), rows
        view = self.db.view_sql(name)
        if view is not None:
            ast = self._view_ast.get(name.lower())
            if ast is None:
                ast = self._view_ast[name.lower()] = Parser(view).select()
            self.note(src, f"View [{name}]")
            self.depth += 1
            try:
                headers, rows = self.run_select(ast, None)
            finally:
                self.depth -= 1
            return self._scope_from(headers, alias or name), rows
        t = self.db.table(name)
        scope = self.table_scope(t, alias)
        plan = choose_access(t, scope, conj or [])
        self.note(src, describe(t, plan))
        return scope, [row for _, row in access(t, plan)]

    def _scope_from(self, headers, alias):
        q = alias.lower()
        return Scope([(q, h.lower(), h) for h in headers])

    def _base_table(self, src):
        if src[0] != "table" or src[1].startswith("sys.") or self.db.view_sql(src[1]) is not None:
            return None
        return self.db.table(src[1])

    @staticmethod
    def _side(e, ls, rs):
        if has_subquery(e):
            return None
        sides = set()
        for c in col_refs(e):
            inl, inr = ls.has(c[1], c[2]), rs.has(c[1], c[2])
            if inl and inr:
                return None
            if not inl and not inr:
                return None
            sides.add("L" if inl else "R")
        return sides

    def join(self, src, outer, conj):
        _, kind, left, right, on = src
        ls, lrows = self.source(left, outer, conj)
        rt = self._base_table(right)
        rs = self.table_scope(rt, right[2]) if rt else None
        rrows = None
        if rs is None:
            rs, rrows = self.source(right, outer)
        scope = ls + rs
        nulls_l, nulls_r = [None] * len(ls.cols), [None] * len(rs.cols)
        out = []

        def on_ok(row):
            return on is None or evaluate(on, Env(scope, row, None, outer, self)) is True

        pairs = []
        if on is not None and kind in ("INNER", "LEFT"):
            for c in conjuncts(on):
                if c[0] == "bin" and c[1] == "=":
                    sa, sb = self._side(c[2], ls, rs), self._side(c[3], ls, rs)
                    if sa == {"L"} and sb == {"R"}:
                        pairs.append((c[2], c[3]))
                    elif sa == {"R"} and sb == {"L"}:
                        pairs.append((c[3], c[2]))

        # 1) Index Nested Loops
        if rt is not None and pairs:
            for lexpr, rexpr in pairs:
                idx = rt.index_on(rexpr[2]) if rexpr[0] == "col" else None
                if idx is None:
                    continue
                self.note(src, f"Index Nested Loops ({kind} JOIN) -> Index Seek "
                               f"[{rt.name}].[{idx.name}] ({expr_name(rexpr)} = {expr_name(lexpr)})")
                col = rt.columns[idx.colidx]
                for l in lrows:
                    v = evaluate(lexpr, Env(ls, l, None, outer, self))
                    matched = False
                    if v is not None:
                        try:
                            from ..storage.table import coerce_value
                            v = coerce_value(col, v)
                        except DBError:
                            v = None
                    if v is not None:
                        for rid in list(idx.tree.seek(v)):
                            row = l + rt.get(rid)
                            if on_ok(row):
                                out.append(row); matched = True
                    if not matched and kind == "LEFT":
                        out.append(l + nulls_r)
                return scope, out

        if rrows is None:
            rs2, rrows = self.source(right, outer)

        # 2) Hash Match
        if pairs:
            lexpr, rexpr = pairs[0]
            self.note(src, f"Hash Match ({kind} JOIN) ({expr_name(lexpr)} = {expr_name(rexpr)})")
            buckets = defaultdict(list)
            for r in rrows:
                k = evaluate(rexpr, Env(rs, r, None, outer, self))
                if k is not None:
                    buckets[k].append(r)
            for l in lrows:
                k = evaluate(lexpr, Env(ls, l, None, outer, self))
                matched = False
                for r in (buckets.get(k, ()) if k is not None else ()):
                    row = l + r
                    if on_ok(row):
                        out.append(row); matched = True
                if not matched and kind == "LEFT":
                    out.append(l + nulls_r)
            return scope, out

        # 3) Nested Loops
        self.note(src, f"Nested Loops ({kind} JOIN)" + (f" ON {expr_name(on)}" if on is not None else ""))
        hit_r = [False] * len(rrows)
        for l in lrows:
            matched = False
            for j, r in enumerate(rrows):
                row = l + r
                if on_ok(row):
                    out.append(row); matched = True; hit_r[j] = True
            if not matched and kind in ("LEFT", "FULL"):
                out.append(l + nulls_r)
        if kind in ("RIGHT", "FULL"):
            for j, r in enumerate(rrows):
                if not hit_r[j]:
                    out.append(nulls_l + r)
        return scope, out

    # ---- SELECT
    def run_select(self, q, outer=None):
        self.depth += 1
        try:
            return self._select(q, outer)
        finally:
            self.depth -= 1

    def _select(self, q, outer):
        where = q["where"]
        if q["from"] is not None:
            scope, rows = self.source(q["from"], outer, conjuncts(where))
        else:
            scope, rows = Scope([]), [[]]

        if where is not None:
            self.note(q, f"Filter (WHERE {expr_name(where)})")
            rows = [r for r in rows if evaluate(where, Env(scope, r, None, outer, self)) is True]

        items = []
        for e, alias in q["items"]:
            if e[0] == "star":
                qual = e[1].lower() if e[1] else None
                cols = [(i, c) for i, c in enumerate(scope.cols) if qual is None or c[0] == qual]
                if qual and not cols:
                    raise DBError(f"Bilinmeyen tablo: {e[1]}")
                items += [(("idx", i), c[2]) for i, c in cols]
            else:
                items.append((e, alias or header_name(e)))
        headers = [h for _, h in items]

        def value(e, env):
            if e[0] == "idx":
                return env.row[e[1]]
            return evaluate(e, env)

        group, having = q["group"], q["having"]
        aggregate = bool(group) or having is not None or \
            any(e[0] != "idx" and has_agg(e) for e, _ in items)
        results = []
        if aggregate:
            self.note(q, "Aggregate" + (f" (GROUP BY {', '.join(expr_name(g) for g in group)})" if group else " (skaler)"))
            groups = {}
            for r in rows:
                env = Env(scope, r, None, outer, self)
                key = tuple(evaluate(g, env) for g in group)
                groups.setdefault(key, []).append(r)
            if not group and not groups:
                groups[()] = []
            if having is not None:
                self.note(having, f"Filter (HAVING {expr_name(having)})")
            for grp in groups.values():
                rep = grp[0] if grp else [None] * len(scope.cols)
                env = Env(scope, rep, grp, outer, self)
                if having is not None and evaluate(having, env) is not True:
                    continue
                results.append(([value(e, env) for e, _ in items], env))
        else:
            for r in rows:
                env = Env(scope, r, None, outer, self)
                results.append(([value(e, env) for e, _ in items], env))

        if q["distinct"]:
            self.note(q["items"], "Distinct")
            seen, uniq = set(), []
            for vals, env in results:
                k = tuple(vals)
                if k not in seen:
                    seen.add(k); uniq.append((vals, env))
            results = uniq

        if q["order"]:
            self.note(q["order"], "Sort (ORDER BY " + ", ".join(
                expr_name(e) + (" DESC" if d else "") for e, d in q["order"]) + ")")
            lower = [h.lower() for h in headers]
            for e, desc in reversed(q["order"]):
                if e[0] == "col" and e[1] is None and e[2].lower() in lower:
                    pos = lower.index(e[2].lower())
                    keyf = lambda it, p=pos: sort_key(it[0][p])
                elif e[0] == "lit" and isinstance(e[1], int):
                    if not 1 <= e[1] <= len(headers):
                        raise DBError(f"ORDER BY {e[1]}: geçersiz kolon sırası")
                    keyf = lambda it, p=e[1] - 1: sort_key(it[0][p])
                else:
                    keyf = lambda it, e=e: sort_key(evaluate(e, it[1]))
                results.sort(key=keyf, reverse=desc)

        off, lim = q["offset"] or 0, q["limit"]
        if off or lim is not None:
            self.note(q["items"], f"Top ({lim if lim is not None else 'hepsi'}" + (f", atla {off}" if off else "") + ")")
            results = results[off:off + lim] if lim is not None else results[off:]
        return headers, [vals for vals, _ in results]

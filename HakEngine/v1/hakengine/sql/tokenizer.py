"""Tokenizer: SQL metnini parçalara (token) ayırır."""
import re
from ..errors import DBError

TOKEN_RE = re.compile(r"""
    \s+|--[^\n]*|
    (?P<num>\d+\.\d*|\d+)|
    (?P<str>'(?:[^']|'')*')|
    (?P<id>[A-Za-z_][A-Za-z0-9_]*)|
    (?P<op><>|!=|<=|>=|[=<>+\-*/%(),;.])
""", re.X)
KEYWORDS = {"SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES", "CREATE", "TABLE",
            "DROP", "UPDATE", "SET", "DELETE", "AND", "OR", "NOT", "NULL", "IS",
            "ORDER", "BY", "ASC", "DESC", "LIMIT", "PRIMARY", "KEY", "BEGIN",
            "COMMIT", "ROLLBACK", "LIKE", "AS", "GROUP", "TRANSACTION", "TOP", "IN"}


def tokenize(sql):
    toks, pos = [], 0
    while pos < len(sql):
        m = TOKEN_RE.match(sql, pos)
        if not m:
            raise DBError(f"Beklenmeyen karakter: {sql[pos]!r}")
        pos = m.end()
        if m.group("num"):
            s = m.group("num")
            toks.append(("lit", float(s) if "." in s else int(s)))
        elif m.group("str"):
            toks.append(("lit", m.group("str")[1:-1].replace("''", "'")))
        elif m.group("id"):
            w = m.group("id")
            toks.append(("kw", w.upper()) if w.upper() in KEYWORDS else ("id", w))
        elif m.group("op"):
            toks.append(("op", m.group("op")))
    toks.append(("eof", None))
    return toks



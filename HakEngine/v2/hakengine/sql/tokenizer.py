"""Tokenizer: SQL metnini parçalara (token) ayırır.

Her token: (tür, değer, konum)
  tür: 'kw' anahtar kelime, 'id' isim, 'lit' sayı/metin, 'op' operatör, 'eof' son
v2: [köşeli] ve "çift tırnaklı" isimler, N'metin', /* blok yorum */, || operatörü.
"""
import re
from ..errors import DBError

TOKEN_RE = re.compile(r"""
    (?P<ws>\s+|--[^\n]*|/\*.*?\*/)|
    (?P<num>\d+\.\d*(?:[eE][+-]?\d+)?|\.\d+|\d+(?:[eE][+-]?\d+)?)|
    (?P<str>[Nn]?'(?:[^']|'')*')|
    (?P<qid>\[[^\]]+\]|"[^"]+")|
    (?P<id>[A-Za-z_À-￿][A-Za-z0-9_$#À-￿]*)|
    (?P<op><>|!=|<=|>=|\|\||[=<>+\-*/%(),;.])
""", re.X | re.S)

KEYWORDS = {
    "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES", "CREATE", "TABLE", "DROP", "UPDATE",
    "SET", "DELETE", "AND", "OR", "NOT", "NULL", "IS", "ORDER", "BY", "ASC", "DESC", "LIMIT",
    "OFFSET", "PRIMARY", "KEY", "BEGIN", "COMMIT", "ROLLBACK", "LIKE", "AS", "GROUP", "HAVING",
    "TRANSACTION", "TOP", "IN", "DISTINCT", "JOIN", "INNER", "LEFT", "RIGHT", "FULL", "OUTER",
    "CROSS", "ON", "INDEX", "UNIQUE", "VIEW", "ALTER", "ADD", "DEFAULT", "IDENTITY", "BETWEEN",
    "CASE", "WHEN", "THEN", "ELSE", "END", "EXISTS", "EXPLAIN", "TRUNCATE", "IF",
}


def tokenize(sql):
    toks, pos = [], 0
    while pos < len(sql):
        m = TOKEN_RE.match(sql, pos)
        if not m:
            raise DBError(f"Beklenmeyen karakter: {sql[pos]!r} (konum {pos})")
        start, pos = pos, m.end()
        if m.group("ws"):
            continue
        if m.group("num"):
            s = m.group("num")
            toks.append(("lit", float(s) if any(c in s for c in ".eE") else int(s), start))
        elif m.group("str"):
            s = m.group("str")
            if s[0] in "Nn":
                s = s[1:]
            toks.append(("lit", s[1:-1].replace("''", "'"), start))
        elif m.group("qid"):
            toks.append(("id", m.group("qid")[1:-1], start))
        elif m.group("id"):
            w = m.group("id")
            toks.append(("kw", w.upper(), start) if w.upper() in KEYWORDS else ("id", w, start))
        else:
            toks.append(("op", m.group("op"), start))
    toks.append(("eof", None, len(sql)))
    return toks

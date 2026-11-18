# sql — Tokenizer ve Parser

SQL metnini motorun anlayacağı ağaç yapısına (AST) çevirir.

| Dosya | Görev |
|---|---|
| `tokenizer.py` | Metni parçalara ayırır. Her parça: `(tür, değer, konum)` |
| `parser.py` | Parçalardan komut ağacı kurar (recursive descent) |

## v2 yenilikleri

- `[köşeli]` ve `"tırnaklı"` isimler, `N'metin'`, `/* blok yorum */`, `||` operatörü.
- JOIN türleri, alt sorgular, CASE, BETWEEN, CAST, CONVERT.
- `CREATE INDEX`, `CREATE VIEW`, `ALTER TABLE ADD`, `TRUNCATE`, `IF [NOT] EXISTS`.
- `OFFSET ... ROWS FETCH NEXT ... ROWS ONLY` (SQL Server ve Oracle yazımı).
- Konum bilgisi sayesinde VIEW ve DEFAULT tanımlarının metni saklanır.

## Operatör önceliği

En düşükten en yükseğe:

```
OR → AND → NOT → (= <> < > <= >= LIKE IN BETWEEN IS NULL) → (+ - ||) → (* / %) → (-x) → değer
```

## AST düğümleri

| Düğüm | Örnek SQL |
|---|---|
| `('lit', 5)` | `5` |
| `('col', 'm', 'ad')` | `m.ad` |
| `('bin', '>', sol, sağ)` | `fiyat > 10` |
| `('between', e, alt, üst)` | `x BETWEEN 1 AND 5` |
| `('in', e, [..])` / `('insub', e, select)` | `x IN (1,2)` / `x IN (SELECT ...)` |
| `('exists', select)` / `('subq', select)` | `EXISTS (...)` / `(SELECT MAX(x) ...)` |
| `('case', taban, [(koşul, sonuç)], değilse)` | `CASE WHEN ... THEN ... END` |
| `('func', 'COUNT', [('star', None)], False)` | `COUNT(*)` |

FROM kaynakları: `('table', ad, takma_ad)`, `('subquery', select, takma_ad)`, `('join', tür, sol, sağ, on)`.

## Kullanım örnekleri

### Tokenizer

```python
from hakengine.sql import tokenize

for tok in tokenize("SELECT [ad soyad] FROM t WHERE x >= 10"):
    print(tok)
# ('kw', 'SELECT', 0)
# ('id', 'ad soyad', 7)
# ('kw', 'FROM', 18)
# ('id', 't', 23)
# ('kw', 'WHERE', 25)
# ('id', 'x', 31)
# ('op', '>=', 33)
# ('lit', 10, 36)
# ('eof', None, 38)
```

### Parser

```python
from hakengine.sql import Parser

st = Parser("SELECT m.ad FROM musteri m LEFT JOIN siparis s ON s.mid = m.id").statements()[0]
print(st[1]["from"])
# ('join', 'LEFT', ('table', 'musteri', 'm'), ('table', 'siparis', 's'),
#  ('bin', '=', ('col', 's', 'mid'), ('col', 'm', 'id')))

print(Parser("fiyat * 2 + 1").expression())
# ('bin', '+', ('bin', '*', ('col', None, 'fiyat'), ('lit', 2)), ('lit', 1))
```

## Yeni komut eklemek

1. Gerekirse anahtar kelimeyi `tokenizer.py` içindeki `KEYWORDS` kümesine ekle.
   Sık kullanılan kolon adlarını anahtar kelime yapma; onun yerine `word()` yardımcısını kullan.
2. `parser.py` içindeki `statement()` metoduna yeni dal ekle ve bir tuple döndür, örneğin `("rename_table", eski, yeni)`.
3. `engine/database.py` içine aynı adla `_rename_table(self, eski, yeni)` metodunu yaz. `run()` onu otomatik bulur.

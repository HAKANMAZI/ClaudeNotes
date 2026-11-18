# sql — Tokenizer ve Parser

SQL metnini motorun anlayacağı ağaç yapısına (AST) çevirir.
SQL Server'daki "parse" aşamasının karşılığıdır.

| Dosya | Görev |
|---|---|
| `tokenizer.py` | Metni parçalara ayırır: anahtar kelime, isim, sayı, metin, operatör |
| `parser.py` | Parçalardan komut ağacı kurar (recursive descent yöntemi) |

## Operatör önceliği

En düşükten en yükseğe:

```
OR  →  AND  →  NOT  →  = <> < > LIKE IN IS NULL  →  + -  →  * / %  →  sayı, kolon, fonksiyon, ( )
```

## Kullanım örnekleri

### Tokenizer

```python
from hakengine.sql import tokenize

print(tokenize("SELECT ad FROM urun WHERE fiyat > 10;"))
# [('kw','SELECT'), ('id','ad'), ('kw','FROM'), ('id','urun'),
#  ('kw','WHERE'), ('id','fiyat'), ('op','>'), ('lit',10), ('op',';'), ('eof',None)]
```

### Parser

```python
from hakengine.sql import Parser

agac = Parser("SELECT ad FROM urun WHERE fiyat > 10;").statements()
print(agac)
# [('select', [(('col','ad'), None)], 'urun',
#   ('bin','>',('col','fiyat'),('lit',10)), [], [], None)]
```

## Yeni komut eklemek

1. Anahtar kelimeyi `tokenizer.py` içindeki `KEYWORDS` kümesine ekle.
2. `parser.py` içindeki `statement()` metoduna yeni dal ekle.
3. Komutu `engine/database.py` içindeki `run()` metodunda çalıştır.

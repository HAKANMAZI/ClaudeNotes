# engine — Yürütücü (Executor)

Parser'dan gelen ağacı çalıştırır. Katalog ve transaction yönetimi de burada.
SQL Server'daki "query processor" katmanının karşılığıdır.

| Dosya | Görev |
|---|---|
| `database.py` | `Database` sınıfı: katalog, transaction, komutların çalıştırılması |
| `evaluator.py` | İfadeleri hesaplar: WHERE koşulları, aritmetik, LIKE, fonksiyonlar, toplamalar |

## Sorgu planı

- WHERE koşulu `primary_key = sabit` ise **indeks araması** yapılır (SQL Server'da index seek).
- Diğer durumlarda **tam tarama** yapılır (table scan).

## Transaction

- `BEGIN` yoksa her komut kendi başına commit edilir (autocommit).
- `BEGIN` ile başlayan değişiklikler `COMMIT` gelene kadar sadece bellekte durur.
- `ROLLBACK` bellekteki değişiklikleri atar ve indeksi yeniden kurar.

## Kullanım örnekleri

### Transaction

```python
from hakengine import Database

db = Database("veritabanim")
db.execute("CREATE TABLE hesap (id INT PRIMARY KEY, bakiye REAL);")
db.execute("INSERT INTO hesap VALUES (1, 100), (2, 50);")

db.execute("BEGIN;")
db.execute("UPDATE hesap SET bakiye = bakiye - 30 WHERE id = 1;")
db.execute("UPDATE hesap SET bakiye = bakiye + 30 WHERE id = 2;")
db.execute("COMMIT;")      # ya da ROLLBACK;
db.close()
```

### İfade hesaplama

```python
from hakengine.engine.evaluator import evaluate

satir, kolonlar = [12.5, "Elma"], ["fiyat", "ad"]
ifade = ("bin", ">", ("col", "fiyat"), ("lit", 10))
print(evaluate(ifade, satir, kolonlar))   # True
```

### Gruplama

```sql
SELECT kategori, COUNT(*) AS adet, MAX(fiyat) AS en_pahali
FROM urun
GROUP BY kategori
ORDER BY adet DESC;
```

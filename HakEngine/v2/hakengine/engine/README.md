# engine — Planlayıcı ve yürütücü

Parser'dan gelen ağacı çalıştırır. SQL Server'daki "relational engine" katmanının karşılığıdır.

| Dosya | Görev |
|---|---|
| `database.py` | `Database`: katalog, DDL, DML, transaction, sistem tabloları, kilit |
| `planner.py` | Tabloya erişim yolunu seçer: Table Scan, Index Seek, Index Range Scan |
| `executor.py` | SELECT'i çalıştırır: JOIN stratejileri, gruplama, sıralama, plan kaydı |
| `evaluator.py` | İfadeleri hesaplar, fonksiyonlar, Türkçe sıralama |

## Planlayıcı

WHERE koşulu AND ile parçalara ayrılır. İndeksli kolonla sabit karşılaştırma aranır:

| Koşul | Seçilen yol |
|---|---|
| `id = 5` (unique indeks) | Index Seek, en fazla bir satır |
| `kategori = 7` | Index Seek |
| `kategori IN (1, 2)` | Index Seek (çoklu) |
| `fiyat > 10 AND fiyat <= 50`, `BETWEEN` | Index Range Scan |
| Diğer | Table Scan |

Plan sadece okunacak satırları azaltır. Tam WHERE her satıra yine uygulanır. Bu yüzden sonuç hep doğrudur.

## JOIN stratejileri

| Strateji | Ne zaman | Maliyet |
|---|---|---|
| Index Nested Loops | Sağ tabloda ON kolonunda indeks var | Sol satır sayısı × log(sağ) |
| Hash Match | Eşitlikli ON var, indeks yok | Sol + sağ |
| Nested Loops | Eşitsizlik (`>`, `<`), RIGHT, FULL, CROSS | Sol × sağ |

## Transaction davranışı

- `BEGIN` yoksa her komut otomatik commit edilir (autocommit). Hata olursa komut tamamen geri alınır.
- `BEGIN` içinde bir komut hata verirse sadece o komut geri alınır, transaction açık kalır.
- Commit yarıda kalırsa (disk hatası) journal hemen geri yüklenir.
- DDL komutları transaction içinde kullanılamaz.

## Kullanım örnekleri

### Plan görme

```sql
EXPLAIN SELECT * FROM siparis WHERE tutar BETWEEN 100 AND 500;
-- 1 | Index Range Scan [siparis].[IX_tutar] (tutar >= 100.0 AND tutar <= 500.0)
-- 2 | Filter (WHERE tutar BETWEEN 100 AND 500)

EXPLAIN SELECT * FROM musteri m JOIN siparis s ON s.musteri_id = m.id;
-- 1 | Table Scan [musteri]
-- 2 | Table Scan [siparis]
-- 3 | Hash Match (INNER JOIN) (m.id = s.musteri_id)     -- indeks yoksa
```

### İlişkili alt sorgu

```sql
-- Departmanının ortalamasından fazla kazananlar
SELECT c.ad, c.maas FROM calisan c
WHERE c.maas > (SELECT AVG(x.maas) FROM calisan x WHERE x.departman_id = c.departman_id);
```

Alt sorgu dış sorguya bağlı değilse bir kez çalıştırılıp önbelleğe alınır. Bağlıysa her satır için çalışır.

### Statement rollback

```python
db.execute("BEGIN")
db.execute("UPDATE hesap SET bakiye = bakiye - 30 WHERE id = 1")
try:
    db.execute("INSERT INTO hesap VALUES (1, 0)")     # PK hatası: sadece bu komut geri alınır
except DBError:
    pass
db.execute("COMMIT")                                  # UPDATE kalıcı olur
```

### Python'dan planlayıcıyı doğrudan kullanma

```python
from hakengine.engine.planner import choose_access, describe
from hakengine.engine.evaluator import conjuncts
from hakengine.sql import Parser

t = db.table("siparis")
scope = db.ex.table_scope(t, None)
where = Parser("musteri_id = 3 AND tutar > 10").expression()
print(describe(t, choose_access(t, scope, conjuncts(where))))
# Index Seek [siparis].[IX_siparis_musteri] (musteri_id = 3)
```

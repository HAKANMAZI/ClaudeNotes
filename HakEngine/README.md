# HakEngine

HakEngine, eğitim amaçlı yazılmış küçük bir ilişkisel veritabanı motorudur.
Mimarisi SQL Server ve Oracle'daki temel katmanların sade bir karşılığıdır.

## Sürümler

| Klasör | Durum | İçerik |
|---|---|---|
| [v1](v1/) | Hazır | SQL ayrıştırıcı, sayfa tabanlı depolama, transaction, çökme kurtarma, primary key indeksi |

## Hızlı başlangıç

```bash
cd v1
python hakengine.py veritabanim
```

```sql
hakengine> CREATE TABLE urun (id INT PRIMARY KEY, ad TEXT, fiyat REAL);
hakengine> INSERT INTO urun VALUES (1, 'Elma', 12.5), (2, 'Çay', 80);
hakengine> SELECT * FROM urun ORDER BY fiyat DESC;
```

Gereksinim: Python 3.8 veya üstü. Ek paket gerekmez.

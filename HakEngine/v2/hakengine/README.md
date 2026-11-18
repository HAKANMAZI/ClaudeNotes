# hakengine (paket)

Motorun kaynak kodu.

| Dosya / Klasör | Görev |
|---|---|
| `__init__.py` | Dışarıya açılanlar: `Database`, `DBError`, `print_result` |
| `__main__.py` | `python -m hakengine` ile çalıştırma |
| `cli.py` | Komut satırı (REPL), `.schema`, `.read`, `.timer` komutları, tablo çıktısı |
| `errors.py` | `DBError` hata sınıfı |
| [`sql/`](sql/) | SQL metnini ağaç yapısına çevirir |
| [`engine/`](engine/) | Planlar ve çalıştırır |
| [`storage/`](storage/) | Diske yazar, okur, korur |

## API

| Metot | Döndürdüğü |
|---|---|
| `Database(klasor)` | Veritabanını açar veya oluşturur. Kilitler. |
| `db.execute(sql)` | Her komut için bir sonuç listesi |
| `db.query(sql)` | Son komutun sonucu. SELECT için `(başlıklar, satırlar)` |
| `db.close()` | Açık transaction'ı geri alır, dosyaları ve kilidi bırakır |
| `with Database(...) as db:` | Blok bitince otomatik kapatır |

SELECT ve EXPLAIN sonucu `(başlıklar, satırlar)` ikilisidir. Diğer komutlar mesaj metni döndürür, örneğin `"3 satır eklendi"`.

## Kullanım örneği

```python
from hakengine import Database, DBError, print_result

with Database("veritabanim") as db:
    db.execute("CREATE TABLE IF NOT EXISTS urun (id INT IDENTITY PRIMARY KEY, ad TEXT, fiyat REAL)")
    db.execute("INSERT INTO urun (ad, fiyat) VALUES ('Elma', 12.5), ('Çay', 80)")

    basliklar, satirlar = db.query("SELECT ad, fiyat FROM urun WHERE fiyat > 10 ORDER BY fiyat")
    print(basliklar)      # ['ad', 'fiyat']
    print(satirlar)       # [['Elma', 12.5], ['Çay', 80.0]]

    print_result(db.query("EXPLAIN SELECT * FROM urun WHERE id = 1"))

    try:
        db.execute("INSERT INTO urun (id, ad) VALUES (1, 'tekrar')")
    except DBError as hata:
        print("Hata:", hata)  # Primary key ihlali (PK_urun): 1 zaten var
```

## Komut satırından

```bash
python -m hakengine veritabanim
python -m hakengine veritabanim dosya.sql
```

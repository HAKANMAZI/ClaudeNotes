# hakengine (paket)

Motorun kaynak kodu. Üç alt katmandan oluşur.

| Dosya / Klasör | Görev |
|---|---|
| `__init__.py` | Dışarıya açılan sınıflar: `Database`, `DBError`, `print_result` |
| `__main__.py` | `python -m hakengine` ile çalıştırmayı sağlar |
| `cli.py` | Komut satırı (REPL) ve tablo biçiminde çıktı |
| `errors.py` | `DBError` hata sınıfı |
| [`sql/`](sql/) | SQL metnini ağaç yapısına çevirir |
| [`engine/`](engine/) | Sorguyu çalıştırır |
| [`storage/`](storage/) | Veriyi diske yazar ve okur |

## Kullanım örneği

```python
from hakengine import Database, DBError, print_result

db = Database("veritabanim")
try:
    db.execute("CREATE TABLE urun (id INT PRIMARY KEY, ad TEXT, fiyat REAL);")
    db.execute("INSERT INTO urun VALUES (1, 'Elma', 12.5);")
except DBError as hata:
    print("Hata:", hata)

basliklar, satirlar = db.execute("SELECT ad, fiyat FROM urun;")[0]
print(basliklar)   # ['ad', 'fiyat']
print(satirlar)    # [['Elma', 12.5]]
db.close()
```

`execute` her komut için bir sonuç döndürür:
- SELECT için `(basliklar, satirlar)` ikilisi.
- Diğer komutlar için bir mesaj metni, örneğin `"1 satır eklendi"`.

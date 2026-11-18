# examples — Örnekler

| Dosya | Açıklama |
|---|---|
| `ornek.sql` | Tablo oluşturma, ekleme, sorgu, gruplama, güncelleme ve transaction örneği |
| `sql_calistir.py` | Herhangi bir `.sql` dosyasını HakEngine'de çalıştırır |
| `ornek_python.py` | HakEngine'i Python kodundan kullanma ve hata yakalama |

## Kullanım

Komutları `v1` klasöründen çalıştır.

### SQL dosyası çalıştırma

```bash
python examples/sql_calistir.py examples/ornek.sql veritabanim
```

Örnek çıktı:

```
+----+-------+-------+----------+
| id | ad    | fiyat | kategori |
+----+-------+-------+----------+
| 4  | Çay   | 80    | İçecek   |
| 3  | Süt   | 30    | İçecek   |
| 2  | Armut | 15    | Meyve    |
+----+-------+-------+----------+
(3 satır)
```

### Python örneği

```bash
python examples/ornek_python.py
```

### Komut satırında elle deneme

```bash
python hakengine.py veritabanim
```

```sql
hakengine> SELECT kategori, COUNT(*) AS adet FROM urun GROUP BY kategori;
hakengine> .tables
hakengine> .exit
```

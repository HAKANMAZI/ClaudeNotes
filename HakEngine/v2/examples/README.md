# examples — Örnekler

| Dosya | Açıklama |
|---|---|
| `sirket.sql` | Departman, çalışan, görev tabloları. JOIN, self join, alt sorgu, EXISTS, CASE, VIEW, transaction, EXPLAIN, sys tabloları |
| `indeks_hizi.py` | Yirmi bin satırda Table Scan ile Index Seek hız karşılaştırması |
| `ornek_python.py` | Python kodundan kullanım: `with`, `query`, hata yakalama, transaction |

Komutları `v2` klasöründen çalıştır.

## Şirket örneği

```bash
python hakengine.py sirket_db examples/sirket.sql
```

Örnek çıktı (departman başına kişi ve ortalama maaş):

```
+-----------+------+----------+
| departman | kisi | ort_maas |
+-----------+------+----------+
| Yazılım   | 3    | 76000    |
| Satış     | 2    | 53000    |
| Muhasebe  | 1    | 48000    |
| Ar-Ge     | 0    | NULL     |
+-----------+------+----------+
```

Sonra elle denemek için:

```bash
python hakengine.py sirket_db
```

```sql
hakengine> SELECT * FROM calisan_ozet ORDER BY maas DESC;
hakengine> .schema calisan
hakengine> .timer on
hakengine> SELECT c.ad, y.ad AS yonetici FROM calisan c LEFT JOIN calisan y ON y.id = c.yonetici_id;
```

## İndeks hızı

```bash
python examples/indeks_hizi.py
```

Örnek çıktı:

```
20000 satır eklendi: 4.1 sn

Primary key ile arama                  0.06 ms   Index Seek [urun].[PK_urun] (id = 12345)
İndekssiz kolonla arama               55.51 ms   Table Scan [urun]
İndeksli kolonla arama                 1.56 ms   Index Seek [urun].[IX_urun_kategori] (kategori = 7)
Aralık taraması                        0.39 ms   Index Range Scan [urun].[PK_urun] (id >= 1000 AND id <= 1100)
```

İndeks eklenince aynı sorgu yaklaşık otuz beş kat hızlandı.

## Python örneği

```bash
python examples/ornek_python.py
```

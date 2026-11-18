# tests — Birim testleri

Python'un kendi `unittest` modülü kullanılır. Ek paket gerekmez. Otuz test vardır.

| Test sınıfı | Neyi kontrol eder |
|---|---|
| `TemelTest` | IDENTITY, DEFAULT, NOT NULL, UNIQUE, primary key, anahtar kaydıran UPDATE, Türkçe sıralama, fonksiyonlar, CASE, BETWEEN, LIKE, IN, DISTINCT, HAVING, OFFSET/FETCH, TOP |
| `JoinTest` | INNER, LEFT, RIGHT, FULL, CROSS, virgüllü join, join ile gruplama, strateji seçimi, belirsiz kolon hatası |
| `AltSorguTest` | IN (SELECT), EXISTS, skaler ve ilişkili alt sorgu, türetilmiş tablo, VIEW, INSERT ... SELECT |
| `IndeksTest` | Plan seçimi, UNIQUE indeks, üç bin satır ve silme, rastgele B+ ağacı testi |
| `TransactionTest` | ROLLBACK, komut seviyesi geri alma, autocommit hatası, DDL yasağı |
| `KalicilikTest` | Kapat-aç, ALTER sonrası veri, kilit, çökme kurtarma (anında ve açılışta), TRUNCATE, DROP |
| `SistemTest` | sys.tables, sys.columns, sys.indexes |

## Kullanım

`v2` klasöründen:

```bash
python -m unittest discover tests
python -m unittest discover tests -v                                  # ayrıntılı
python -m unittest tests.test_hakengine.JoinTest                      # tek sınıf
python -m unittest tests.test_hakengine.KalicilikTest.test_kilit      # tek test
```

Beklenen çıktı:

```
..............................
----------------------------------------------------------------------
Ran 30 tests in 1.8s

OK
```

## Çökme testi nasıl çalışır

`test_cokme_kurtarma_*` testleri `Pager.flush` metodunu geçici olarak değiştirir.
İkinci dosya yazılırken hata fırlatır, yani commit yarıda kalır.
Ardından verinin commit öncesi hâline döndüğü kontrol edilir.

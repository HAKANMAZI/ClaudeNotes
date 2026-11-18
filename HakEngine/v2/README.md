# HakEngine v2

HakEngine'in ikinci sürümü. Saf Python ile yazıldı, dış bağımlılığı yok.
v1'in üzerine JOIN, diskte B+ ağacı indeksleri, sorgu planlayıcı, alt sorgular ve daha güvenli transaction eklendi.

## v1 ile farklar

| Özellik | v1 | v2 |
|---|---|---|
| JOIN | Yok | INNER, LEFT, RIGHT, FULL, CROSS, kendine join |
| İndeks | Sadece primary key, bellekte | Diskte B+ ağacı, `CREATE [UNIQUE] INDEX` |
| Sorgu planı | Sadece `pk = sabit` | Index Seek, Range Scan, Hash Match, Index Nested Loops, `EXPLAIN` |
| Alt sorgu | Yok | `IN (SELECT)`, `EXISTS`, skaler, ilişkili, `FROM (SELECT) AS x` |
| VIEW | Yok | `CREATE VIEW`, `CREATE OR REPLACE VIEW`, `DROP VIEW` |
| Kolon özellikleri | PRIMARY KEY, NOT NULL | + IDENTITY, DEFAULT, UNIQUE |
| SQL | WHERE, ORDER BY, GROUP BY, TOP | + HAVING, DISTINCT, CASE, BETWEEN, OFFSET/FETCH, INSERT ... SELECT |
| Şema değişikliği | Yok | `ALTER TABLE ADD`, `TRUNCATE TABLE`, `DROP INDEX` |
| Commit | Dosya başına journal | Tüm dosyalar için tek journal, atomik commit |
| Hata yönetimi | Hatalı komut transaction'ı bozabilir | Sadece hatalı komut geri alınır (statement rollback) |
| Eşzamanlılık | Koruma yok | Kilit dosyası: aynı veritabanını iki program açamaz |
| Sistem tabloları | Yok | `sys.tables`, `sys.columns`, `sys.indexes`, `sys.views` |
| Sıralama | Unicode sırası | Türkçe alfabe sırası (İstanbul, Kerkük'ten önce gelir) |

> v1 veritabanı klasörleri v2 ile açılmaz. v2 için yeni bir klasör kullanın.

## Klasör yapısı

```
v2/
├── hakengine.py              Başlatıcı
├── hakengine/
│   ├── cli.py                Komut satırı (REPL)
│   ├── sql/                  Tokenizer ve Parser
│   ├── engine/               Planlayıcı, yürütücü, veritabanı
│   └── storage/              Sayfa, pager, journal, B+ ağacı, tablo
├── examples/                 Şirket veritabanı, hız ölçümü, Python örneği
└── tests/                    Otuz birim testi
```

## Mimari

```
SQL metni
   │
   ▼
[sql]       Tokenizer → Parser → AST
   │
   ▼
[engine]    Database ── DDL / DML / transaction
              │
              ├─ Planner   : Table Scan | Index Seek | Index Range Scan
              └─ Executor  : JOIN (Index Nested Loops | Hash Match | Nested Loops)
                             → WHERE → GROUP BY → HAVING → SELECT → DISTINCT → ORDER BY → TOP
   │
   ▼
[storage]   Table (heap .tbl) + Index (B+ ağacı .idx)
              → Pager (buffer pool + savepoint)
              → Journal (atomik commit, çökme kurtarma)
              → Page (4096 bayt slotted page)
```

SQL Server karşılıkları:

| HakEngine | SQL Server |
|---|---|
| `catalog.json`, `sys.*` | Sistem katalog görünümleri |
| `Page` (4 KB) | Veri sayfası (8 KB) |
| `Pager` | Buffer pool |
| `journal.py` | Transaction log (burada rollback journal) |
| B+ ağacı `.idx` | Nonclustered index |
| `EXPLAIN` | Tahmini yürütme planı |
| Statement rollback | `XACT_ABORT OFF` davranışı |

## Hızlı başlangıç

```bash
cd v2
python hakengine.py veritabanim                       # etkileşimli
python hakengine.py sirket_db examples/sirket.sql     # dosyadan çalıştır
python -m unittest discover tests                     # testler
```

```sql
hakengine> CREATE TABLE musteri (id INT IDENTITY PRIMARY KEY, ad NVARCHAR(50) NOT NULL, sehir TEXT DEFAULT 'Kerkük');
hakengine> CREATE TABLE siparis (id INT IDENTITY PRIMARY KEY, musteri_id INT, tutar DECIMAL(10,2));
hakengine> CREATE INDEX IX_siparis_musteri ON siparis (musteri_id);
hakengine> INSERT INTO musteri (ad) VALUES ('Ali'), ('Ayşe');
hakengine> INSERT INTO siparis (musteri_id, tutar) VALUES (1, 100), (1, 250), (2, 75);
hakengine> SELECT m.ad, COUNT(s.id) AS adet, SUM(s.tutar) AS toplam
      ...> FROM musteri m LEFT JOIN siparis s ON s.musteri_id = m.id
      ...> GROUP BY m.ad ORDER BY toplam DESC;
+------+------+--------+
| ad   | adet | toplam |
+------+------+--------+
| Ali  | 2    | 350    |
| Ayşe | 1    | 75     |
+------+------+--------+
(2 satır)
hakengine> EXPLAIN SELECT * FROM musteri m JOIN siparis s ON s.musteri_id = m.id WHERE m.id = 1;
+------+---------------------------------------------------------------------------------------------------+
| adım | işlem                                                                                             |
+------+---------------------------------------------------------------------------------------------------+
| 1    | Index Seek [musteri].[PK_musteri] (id = 1)                                                        |
| 2    | Index Nested Loops (INNER JOIN) -> Index Seek [siparis].[IX_siparis_musteri] (s.musteri_id = m.id) |
| 3    | Filter (WHERE m.id = 1)                                                                           |
+------+---------------------------------------------------------------------------------------------------+
```

## Komut satırı komutları

| Komut | Açıklama |
|---|---|
| `.tables` | Tabloları listeler |
| `.schema [tablo]` | Tablo yapısını `CREATE TABLE` olarak gösterir |
| `.indexes` | İndeksleri listeler |
| `.views` | View'ları listeler |
| `.read dosya.sql` | SQL dosyası çalıştırır |
| `.timer on` | Her komutun süresini gösterir |
| `.help`, `.exit` | Yardım, çıkış |

## Desteklenen SQL

**DDL**
```sql
CREATE TABLE [IF NOT EXISTS] t (
    id INT IDENTITY(1,1) PRIMARY KEY,
    ad NVARCHAR(50) NOT NULL UNIQUE,
    durum TEXT DEFAULT 'açık'
);
CREATE [UNIQUE] INDEX IX_ad ON t (kolon);
CREATE [OR REPLACE] VIEW v AS SELECT ...;
ALTER TABLE t ADD [COLUMN] yeni TEXT DEFAULT 'x';
DROP TABLE|INDEX|VIEW [IF EXISTS] ad;
TRUNCATE TABLE t;
```

**DML**
```sql
INSERT INTO t (a, b) VALUES (1, 'x'), (2, 'y');
INSERT INTO arsiv SELECT * FROM t WHERE ...;
UPDATE t SET a = a + 1 WHERE b IN (SELECT ...);
DELETE FROM t WHERE NOT EXISTS (SELECT ...);
```

**SELECT**
```sql
SELECT [DISTINCT] [TOP n] ifade [AS takma_ad], ...
FROM t1 a
  [INNER | LEFT | RIGHT | FULL] JOIN t2 b ON ...
  CROSS JOIN t3
  JOIN (SELECT ...) AS x ON ...
WHERE ...
GROUP BY ...  HAVING ...
ORDER BY ifade [ASC|DESC] | takma_ad | sıra_no
LIMIT n [OFFSET m]  |  OFFSET m ROWS FETCH NEXT n ROWS ONLY
```

**Transaction**: `BEGIN [TRAN|TRANSACTION]`, `COMMIT`, `ROLLBACK`

**Tipler**: INT, REAL, TEXT. Şu isimler otomatik eşlenir: INTEGER, BIGINT, SMALLINT, TINYINT, BIT, FLOAT, DOUBLE, DECIMAL, NUMERIC, NUMBER, MONEY, VARCHAR, NVARCHAR, CHAR, NCHAR, VARCHAR2, NVARCHAR2, CLOB, DATE, DATETIME, DATETIME2, TIMESTAMP.

**Fonksiyonlar**

| Grup | Fonksiyonlar |
|---|---|
| Toplama | COUNT, SUM, AVG, MIN, MAX, `COUNT(DISTINCT x)` |
| Metin | UPPER, LOWER, LEN, LENGTH, TRIM, LTRIM, RTRIM, SUBSTRING, SUBSTR, LEFT, RIGHT, REPLACE, CONCAT, CHARINDEX, INSTR, REVERSE, `\|\|` |
| Sayı | ABS, ROUND, FLOOR, CEILING, CEIL, POWER, SQRT, SIGN |
| NULL | ISNULL, NVL, COALESCE, IFNULL, NULLIF |
| Koşul | CASE, IIF |
| Tip | CAST(x AS tip), CONVERT(tip, x) |
| Tarih | GETDATE, NOW, SYSDATE, CURRENT_TIMESTAMP, CURRENT_DATE, YEAR, MONTH, DAY |

**İsimler**: `[köşeli parantez]` ve `"çift tırnak"` ile boşluklu veya ayrılmış isimler yazılabilir. `dbo.tablo` yazımı kabul edilir.

## Sınırlar (v2)

- Tek kolonlu primary key ve indeks.
- `UNION`, pencere fonksiyonları (`ROW_NUMBER` vb.) ve `GROUP BY ROLLUP` yok.
- DDL komutları transaction içinde kullanılamaz.
- Aynı anda tek program erişebilir (kilit dosyası).
- IDENTITY değerleri ROLLBACK ile geri alınmaz (SQL Server'daki gibi).
- B+ ağacında silme sonrası düğüm birleştirme yapılmaz.
- Bir satır en fazla dört bin bayt olabilir.

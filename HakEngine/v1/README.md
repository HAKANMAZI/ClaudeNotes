# HakEngine v1

HakEngine'in ilk sürümü. Saf Python ile yazıldı, dış bağımlılığı yok.

## Klasör yapısı

```
v1/
├── hakengine.py          Başlatıcı (komut satırı)
├── hakengine/            Motorun kaynak kodu
│   ├── sql/              Tokenizer ve Parser
│   ├── engine/           Executor, katalog, transaction
│   └── storage/          Sayfa, pager, journal, tablo, indeks
├── examples/             Örnek SQL ve Python betikleri
└── tests/                Birim testleri
```

## Mimari

```
SQL metni
   │
   ▼
[sql]      Tokenizer → Parser → Sözdizimi ağacı (AST)
   │
   ▼
[engine]   Database.run → Evaluator (WHERE, fonksiyonlar, GROUP BY)
   │
   ▼
[storage]  Table → Pager (önbellek + journal) → Page (4096 bayt) → .tbl dosyası
```

SQL Server karşılıkları:

| HakEngine | SQL Server |
|---|---|
| `catalog.json` | `sys.tables`, `sys.columns` |
| `Page` (4 KB) | Veri sayfası (8 KB) |
| `Pager` + journal | Buffer pool + transaction log |
| Primary key indeksi | Clustered index |
| Tam tarama | Table scan |

## Desteklenen SQL

| Komut | Örnek |
|---|---|
| CREATE TABLE | `CREATE TABLE t (id INT PRIMARY KEY, ad VARCHAR(50) NOT NULL, fiyat DECIMAL);` |
| DROP TABLE | `DROP TABLE t;` |
| INSERT | `INSERT INTO t (id, ad) VALUES (1, 'a'), (2, 'b');` |
| SELECT | `SELECT TOP 5 ad, fiyat * 2 AS cift FROM t WHERE ad LIKE 'A%' ORDER BY fiyat DESC;` |
| GROUP BY | `SELECT kategori, COUNT(*), AVG(fiyat) FROM t GROUP BY kategori;` |
| UPDATE | `UPDATE t SET fiyat = fiyat + 1 WHERE id IN (1, 2);` |
| DELETE | `DELETE FROM t WHERE fiyat IS NULL;` |
| Transaction | `BEGIN TRANSACTION;` … `COMMIT;` veya `ROLLBACK;` |

- **Tipler:** INT, REAL, TEXT. VARCHAR, NVARCHAR, VARCHAR2, DECIMAL, NUMBER, FLOAT gibi isimler otomatik eşlenir.
- **Fonksiyonlar:** COUNT, SUM, AVG, MIN, MAX, UPPER, LOWER, LEN, ABS, ROUND, ISNULL, NVL, COALESCE.
- **Operatörler:** `= <> != < > <= >= + - * / %`, AND, OR, NOT, LIKE, IN, IS NULL.

## Kullanım

### Komut satırı

```bash
python hakengine.py veritabanim
```

- Her komutu `;` ile bitir.
- `.tables` tabloları listeler.
- `.exit` çıkış yapar.

### Python kodundan

```python
from hakengine import Database, print_result

db = Database("veritabanim")
db.execute("CREATE TABLE musteri (id INT PRIMARY KEY, ad TEXT);")
db.execute("INSERT INTO musteri VALUES (1, 'Ali');")
for sonuc in db.execute("SELECT * FROM musteri;"):
    print_result(sonuc)
db.close()
```

### Modül olarak

```bash
python -m hakengine veritabanim
```

## Testler

```bash
python -m unittest discover tests
```

## Sınırlar (v1)

- JOIN yok.
- İndeks yalnızca primary key için, bellekte tutuluyor.
- Tek kullanıcı. Eşzamanlı erişim ve kilitleme yok.
- Bir satır en fazla dört bin bayt olabilir.

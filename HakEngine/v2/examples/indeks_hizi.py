"""İndeksin etkisini ölçer: Table Scan ile Index Seek karşılaştırması.

Çalıştırma (v2 klasöründen):  python examples/indeks_hizi.py
"""
import os, sys, time, shutil, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from hakengine import Database, print_result

SATIR = 20000
yol = tempfile.mkdtemp()
db = Database(yol)
db.execute("CREATE TABLE urun (id INT PRIMARY KEY, kategori INT, ad TEXT, fiyat REAL)")

t0 = time.perf_counter()
db.execute("BEGIN")
for i in range(SATIR):
    db.execute(f"INSERT INTO urun VALUES ({i}, {i % 50}, 'Ürün {i}', {i % 997 * 1.5})")
db.execute("COMMIT")
print(f"{SATIR} satır eklendi: {time.perf_counter() - t0:.1f} sn")


def olc(baslik, sql, tekrar=20):
    t0 = time.perf_counter()
    for _ in range(tekrar):
        sonuc = db.query(sql)
    ms = (time.perf_counter() - t0) * 1000 / tekrar
    plan = db.query("EXPLAIN " + sql)[1][0][1]
    print(f"{baslik:<34} {ms:8.2f} ms   {plan}")
    return sonuc


print()
olc("Primary key ile arama", "SELECT * FROM urun WHERE id = 12345")
olc("İndekssiz kolonla arama", "SELECT COUNT(*) FROM urun WHERE kategori = 7")
db.execute("CREATE INDEX IX_urun_kategori ON urun (kategori)")
olc("İndeksli kolonla arama", "SELECT COUNT(*) FROM urun WHERE kategori = 7")
olc("Aralık taraması", "SELECT COUNT(*) FROM urun WHERE id BETWEEN 1000 AND 1100")

print()
print_result(db.query("SELECT index_name, pages, depth FROM sys.indexes"))
db.close()
shutil.rmtree(yol)

"""HakEngine v2'yi Python kodundan kullanma.

Çalıştırma (v2 klasöründen):  python examples/ornek_python.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from hakengine import Database, DBError, print_result

# 'with' bloğu bitince veritabanı otomatik kapanır ve kilit bırakılır
with Database("ornek_veritabani") as db:
    db.execute("""
        CREATE TABLE IF NOT EXISTS musteri (
            id    INT IDENTITY PRIMARY KEY,
            ad    TEXT NOT NULL,
            sehir TEXT DEFAULT 'Kerkük'
        )
    """)
    if db.query("SELECT COUNT(*) FROM musteri")[1][0][0] == 0:
        db.execute("INSERT INTO musteri (ad) VALUES ('Ali'), ('Mehmet')")
        db.execute("INSERT INTO musteri (ad, sehir) VALUES ('Ayşe', 'İstanbul')")

    # query: son SELECT'in (başlıklar, satırlar) sonucunu verir
    basliklar, satirlar = db.query("SELECT sehir, COUNT(*) AS kisi FROM musteri GROUP BY sehir ORDER BY sehir")
    print(basliklar)
    for sehir, kisi in satirlar:
        print(f"  {sehir}: {kisi} kişi")

    # Tablo görünümünde yazdırma
    print_result(db.query("SELECT * FROM musteri ORDER BY id"))

    # Hata yakalama
    try:
        db.execute("INSERT INTO musteri (ad) VALUES (NULL)")
    except DBError as hata:
        print("Beklenen hata:", hata)

    # Transaction
    db.execute("BEGIN")
    db.execute("DELETE FROM musteri")
    print("Silindikten sonra:", db.query("SELECT COUNT(*) FROM musteri")[1][0][0])
    db.execute("ROLLBACK")
    print("Geri alındıktan sonra:", db.query("SELECT COUNT(*) FROM musteri")[1][0][0])

"""HakEngine'i Python kodundan kullanma örneği.
Çalıştırma (v1 klasöründen):  python examples/ornek_python.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from hakengine import Database, DBError, print_result

db = Database("ornek_veritabani")
if "musteri" not in db.tables:
    db.execute("CREATE TABLE musteri (id INT PRIMARY KEY, ad TEXT, sehir TEXT);")
    db.execute("INSERT INTO musteri VALUES (1,'Ali','Kerkük'),(2,'Ayşe','İstanbul'),(3,'Mehmet','Kerkük');")

for sonuc in db.execute("SELECT sehir, COUNT(*) AS kisi FROM musteri GROUP BY sehir;"):
    print_result(sonuc)

try:
    db.execute("INSERT INTO musteri VALUES (1,'Tekrar','Ankara');")
except DBError as hata:
    print("Beklenen hata:", hata)

db.close()

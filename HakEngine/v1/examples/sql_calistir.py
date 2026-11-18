"""Bir .sql dosyasını HakEngine'de çalıştırır.
Kullanım (v1 klasöründen):  python examples/sql_calistir.py examples/ornek.sql veritabanim
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from hakengine import Database, DBError, print_result

dosya = sys.argv[1]
yol = sys.argv[2] if len(sys.argv) > 2 else "veritabanim"
db = Database(yol)
try:
    for sonuc in db.execute(open(dosya, encoding="utf-8").read()):
        print_result(sonuc)
except DBError as hata:
    print("HATA:", hata)
db.close()

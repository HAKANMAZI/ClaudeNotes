"""HakEngine testleri.  Çalıştırma (v1 klasöründen):  python -m unittest discover tests"""
import os, sys, shutil, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from hakengine import Database, DBError


class HakEngineTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.db = Database(self.dir)
        self.db.execute("CREATE TABLE t (id INT PRIMARY KEY, ad TEXT, fiyat REAL);"
                        "INSERT INTO t VALUES (1,'a',10),(2,'b',20),(3,'c',NULL);")

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.dir)

    def q(self, sql):
        return self.db.execute(sql)[-1]

    def test_select_where_order(self):
        h, rows = self.q("SELECT ad FROM t WHERE fiyat >= 10 ORDER BY fiyat DESC;")
        self.assertEqual(rows, [["b"], ["a"]])

    def test_aggregate(self):
        h, rows = self.q("SELECT COUNT(*), SUM(fiyat), AVG(fiyat) FROM t;")
        self.assertEqual(rows, [[3, 30.0, 15.0]])

    def test_primary_key(self):
        with self.assertRaises(DBError):
            self.db.execute("INSERT INTO t VALUES (1,'x',1);")

    def test_update_delete(self):
        self.db.execute("UPDATE t SET fiyat = fiyat * 2 WHERE id = 1; DELETE FROM t WHERE id = 2;")
        self.assertEqual(self.q("SELECT id, fiyat FROM t ORDER BY id;")[1], [[1, 20.0], [3, None]])

    def test_rollback(self):
        self.db.execute("BEGIN; DELETE FROM t; ROLLBACK;")
        self.assertEqual(self.q("SELECT COUNT(*) FROM t;")[1], [[3]])

    def test_persistence(self):
        self.db.close()
        self.db = Database(self.dir)
        self.assertEqual(self.q("SELECT COUNT(*) FROM t;")[1], [[3]])

    def test_many_rows(self):
        self.db.execute("BEGIN;")
        for i in range(10, 5010):
            self.db.tables["t"].insert([i, "satir", float(i)])
        self.db.execute("COMMIT;")
        self.assertEqual(self.q("SELECT ad FROM t WHERE id = 4000;")[1], [["satir"]])
        self.assertEqual(self.q("SELECT COUNT(*) FROM t;")[1], [[5003]])

    def test_crash_recovery(self):
        # Yarım kalan commit: journal dosyası var, veri dosyası bozuk
        t = self.db.tables["t"]
        path = t.pager.path
        self.db.close()
        orig = open(path, "rb").read()
        import struct
        with open(path + "-journal", "wb") as j:
            j.write(struct.pack("<I", len(orig) // 4096))
            j.write(struct.pack("<I", 0) + orig[:4096])
        with open(path, "r+b") as f:
            f.write(b"\xff" * 100)
        self.db = Database(self.dir)
        self.assertEqual(self.q("SELECT COUNT(*) FROM t;")[1], [[3]])


if __name__ == "__main__":
    unittest.main()

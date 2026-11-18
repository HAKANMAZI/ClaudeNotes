"""HakEngine v2 testleri.  Çalıştırma (v2 klasöründen):  python -m unittest discover tests -v"""
import os, sys, shutil, random, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from hakengine import Database, DBError
from hakengine.storage import Pager, BTree, journal


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.db = Database(self.dir)
        self.db.execute("""
            CREATE TABLE musteri (id INT IDENTITY PRIMARY KEY, ad TEXT NOT NULL,
                                  sehir TEXT DEFAULT 'Kerkük', email TEXT UNIQUE);
            CREATE TABLE siparis (id INT IDENTITY PRIMARY KEY, musteri_id INT, tutar REAL);
            INSERT INTO musteri (ad, email) VALUES ('Ali', 'a@x'), ('Ayşe', 'b@x');
            INSERT INTO musteri (ad, sehir) VALUES ('Mehmet', 'İstanbul'), ('Zeynep', 'Ankara');
            INSERT INTO siparis (musteri_id, tutar) VALUES (1, 100), (1, 250), (2, 75), (3, 1000), (99, 5);
        """)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.dir)

    def rows(self, sql):
        return self.db.query(sql)[1]

    def plan(self, sql):
        return " | ".join(r[1] for r in self.rows("EXPLAIN " + sql))


class TemelTest(Base):
    def test_identity_ve_default(self):
        self.assertEqual(self.rows("SELECT id, sehir FROM musteri ORDER BY id"),
                         [[1, "Kerkük"], [2, "Kerkük"], [3, "İstanbul"], [4, "Ankara"]])

    def test_not_null_ve_unique(self):
        with self.assertRaises(DBError):
            self.db.execute("INSERT INTO musteri (ad) VALUES (NULL)")
        with self.assertRaises(DBError):
            self.db.execute("INSERT INTO musteri (ad, email) VALUES ('X', 'a@x')")
        self.db.execute("INSERT INTO musteri (ad, email) VALUES ('Y', NULL)")   # NULL tekrar edebilir

    def test_primary_key(self):
        with self.assertRaises(DBError):
            self.db.execute("INSERT INTO musteri (id, ad) VALUES (1, 'tekrar')")

    def test_update_anahtar_kaydirma(self):
        self.db.execute("UPDATE musteri SET id = id + 1")
        self.assertEqual(self.rows("SELECT MIN(id), MAX(id) FROM musteri"), [[2, 5]])

    def test_turkce_siralama(self):
        self.assertEqual(self.rows("SELECT sehir FROM musteri GROUP BY sehir ORDER BY sehir"),
                         [["Ankara"], ["İstanbul"], ["Kerkük"]])

    def test_fonksiyonlar(self):
        r = self.rows("SELECT UPPER('abc'), LEN('merhaba'), SUBSTRING('HakEngine', 4, 6), "
                      "ROUND(2.567, 1), COALESCE(NULL, 5), 'a' || 'b', CAST('42' AS INT) + 1, "
                      "IIF(1 > 2, 'evet', 'hayır'), REPLACE('a-b', '-', '+')")
        self.assertEqual(r, [["ABC", 7, "Engine", 2.6, 5, "ab", 43, "hayır", "a+b"]])

    def test_case_between_like_in(self):
        r = self.rows("SELECT ad, CASE WHEN id BETWEEN 1 AND 2 THEN 'ilk' ELSE 'son' END "
                      "FROM musteri WHERE ad LIKE '%e%' OR id IN (1) ORDER BY id")
        self.assertEqual(r, [["Ali", "ilk"], ["Ayşe", "ilk"], ["Mehmet", "son"], ["Zeynep", "son"]])

    def test_distinct_having_offset(self):
        self.assertEqual(self.rows("SELECT DISTINCT musteri_id FROM siparis WHERE musteri_id < 10 ORDER BY 1"),
                         [[1], [2], [3]])
        self.assertEqual(self.rows("SELECT musteri_id, COUNT(*) FROM siparis GROUP BY musteri_id HAVING COUNT(*) > 1"),
                         [[1, 2]])
        self.assertEqual(self.rows("SELECT id FROM siparis ORDER BY id OFFSET 1 ROWS FETCH NEXT 2 ROWS ONLY"),
                         [[2], [3]])
        self.assertEqual(self.rows("SELECT TOP 1 id FROM siparis ORDER BY tutar DESC"), [[4]])


class JoinTest(Base):
    def test_inner_left_right_full(self):
        base = "SELECT m.id, s.id FROM musteri m {} JOIN siparis s ON s.musteri_id = m.id"
        self.assertEqual(len(self.rows(base.format("INNER"))), 4)
        self.assertEqual(len(self.rows(base.format("LEFT"))), 5)      # Zeynep eşleşmesiz
        self.assertEqual(len(self.rows(base.format("RIGHT"))), 5)     # 99 numaralı müşteri yok
        self.assertEqual(len(self.rows(base.format("FULL"))), 6)

    def test_cross_ve_virgul(self):
        self.assertEqual(self.rows("SELECT COUNT(*) FROM musteri, siparis"), [[20]])
        self.assertEqual(self.rows("SELECT COUNT(*) FROM musteri CROSS JOIN siparis"), [[20]])

    def test_join_gruplama(self):
        r = self.rows("SELECT m.ad, SUM(s.tutar) AS t FROM musteri m LEFT JOIN siparis s "
                      "ON s.musteri_id = m.id GROUP BY m.ad ORDER BY t DESC")
        self.assertEqual(r, [["Mehmet", 1000], ["Ali", 350], ["Ayşe", 75], ["Zeynep", None]])

    def test_join_stratejileri(self):
        sql = "SELECT * FROM musteri m JOIN siparis s ON s.musteri_id = m.id"
        self.assertIn("Hash Match", self.plan(sql))
        self.db.execute("CREATE INDEX IX_sip_mus ON siparis (musteri_id)")
        self.assertIn("Index Nested Loops", self.plan(sql))
        self.assertIn("Nested Loops (INNER JOIN) ON", self.plan(
            "SELECT * FROM musteri m JOIN siparis s ON s.tutar > m.id"))

    def test_belirsiz_kolon(self):
        with self.assertRaises(DBError):
            self.rows("SELECT id FROM musteri m JOIN siparis s ON s.musteri_id = m.id")


class AltSorguTest(Base):
    def test_in_exists_skaler(self):
        self.assertEqual(self.rows("SELECT ad FROM musteri WHERE id IN (SELECT musteri_id FROM siparis "
                                   "WHERE tutar > 200) ORDER BY id"), [["Ali"], ["Mehmet"]])
        self.assertEqual(self.rows("SELECT ad FROM musteri m WHERE NOT EXISTS "
                                   "(SELECT 1 FROM siparis s WHERE s.musteri_id = m.id)"), [["Zeynep"]])
        self.assertEqual(self.rows("SELECT ad, (SELECT COUNT(*) FROM siparis s WHERE s.musteri_id = m.id) "
                                   "FROM musteri m ORDER BY id"),
                         [["Ali", 2], ["Ayşe", 1], ["Mehmet", 1], ["Zeynep", 0]])

    def test_turetilmis_tablo_ve_view(self):
        self.assertEqual(self.rows("SELECT x.m, x.t FROM (SELECT musteri_id AS m, SUM(tutar) AS t "
                                   "FROM siparis GROUP BY musteri_id) AS x WHERE x.t > 500"), [[3, 1000]])
        self.db.execute("CREATE VIEW buyuk AS SELECT * FROM siparis WHERE tutar >= 100")
        self.assertEqual(self.rows("SELECT COUNT(*) FROM buyuk"), [[3]])
        self.db.execute("DROP VIEW buyuk")
        with self.assertRaises(DBError):
            self.rows("SELECT * FROM buyuk")

    def test_insert_select(self):
        self.db.execute("CREATE TABLE arsiv (id INT, tutar REAL)")
        self.db.execute("INSERT INTO arsiv SELECT id, tutar FROM siparis WHERE tutar < 100")
        self.assertEqual(self.rows("SELECT COUNT(*) FROM arsiv"), [[2]])


class IndeksTest(Base):
    def test_plan_secimi(self):
        self.assertIn("Index Seek [musteri].[PK_musteri] (id = 3)", self.plan("SELECT * FROM musteri WHERE id = 3"))
        self.assertIn("Table Scan", self.plan("SELECT * FROM siparis WHERE tutar = 5"))
        self.db.execute("CREATE INDEX IX_tutar ON siparis (tutar)")
        self.assertIn("Index Range Scan", self.plan("SELECT * FROM siparis WHERE tutar > 50 AND tutar <= 250"))
        self.assertIn("IN", self.plan("SELECT * FROM siparis WHERE tutar IN (5, 75)"))
        self.assertEqual(self.rows("SELECT id FROM siparis WHERE tutar > 50 AND tutar <= 250 ORDER BY id"),
                         [[1], [2], [3]])

    def test_unique_indeks(self):
        with self.assertRaises(DBError):
            self.db.execute("CREATE UNIQUE INDEX UX_mid ON siparis (musteri_id)")
        self.db.execute("CREATE UNIQUE INDEX UX_tutar ON siparis (tutar)")
        with self.assertRaises(DBError):
            self.db.execute("INSERT INTO siparis (musteri_id, tutar) VALUES (1, 100)")

    def test_cok_satir(self):
        self.db.execute("CREATE TABLE b (id INT PRIMARY KEY, g INT)")
        self.db.execute("CREATE INDEX IX_g ON b (g)")
        self.db.execute("BEGIN")
        for i in range(3000):
            self.db.execute(f"INSERT INTO b VALUES ({i}, {i % 10})")
        self.db.execute("COMMIT")
        self.db.execute("DELETE FROM b WHERE g = 3")
        self.assertEqual(self.rows("SELECT COUNT(*) FROM b WHERE g = 4"), [[300]])
        self.assertEqual(self.rows("SELECT COUNT(*) FROM b"), [[2700]])
        self.assertEqual(self.rows("SELECT g FROM b WHERE id = 2999"), [[9]])

    def test_btree_rastgele(self):
        p = Pager(os.path.join(self.dir, "t.idx"))
        t = BTree(p)
        ref = []
        for i in range(5000):
            v = random.randint(0, 300)
            t.insert(v, (i, 0)); ref.append((v, (i, 0)))
        for v, rid in random.sample(ref, 2000):
            t.delete(v, rid); ref.remove((v, rid))
        self.assertEqual(sorted((v, r) for r, v in t.range()), sorted(ref))
        self.assertEqual(sorted(t.seek(150)), sorted(r for v, r in ref if v == 150))
        p.close()


class TransactionTest(Base):
    def test_rollback(self):
        self.db.execute("BEGIN TRANSACTION; DELETE FROM siparis; UPDATE musteri SET ad = 'x'; ROLLBACK;")
        self.assertEqual(self.rows("SELECT COUNT(*) FROM siparis"), [[5]])
        self.assertEqual(self.rows("SELECT ad FROM musteri WHERE id = 1"), [["Ali"]])

    def test_komut_seviyesi_geri_alma(self):
        self.db.execute("BEGIN")
        self.db.execute("UPDATE siparis SET tutar = 0 WHERE id = 1")
        with self.assertRaises(DBError):
            self.db.execute("INSERT INTO musteri (ad, email) VALUES ('X', 'yeni@x'), ('Y', 'a@x')")
        self.db.execute("COMMIT")
        self.assertEqual(self.rows("SELECT tutar FROM siparis WHERE id = 1"), [[0]])
        self.assertEqual(self.rows("SELECT COUNT(*) FROM musteri"), [[4]])   # hatalı komutun ilk satırı da geri alındı

    def test_autocommit_hata(self):
        with self.assertRaises(DBError):
            self.db.execute("UPDATE siparis SET tutar = tutar / 0")
        self.assertEqual(self.rows("SELECT SUM(tutar) FROM siparis"), [[1430]])

    def test_ddl_transaction_icinde_olmaz(self):
        self.db.execute("BEGIN")
        with self.assertRaises(DBError):
            self.db.execute("CREATE TABLE z (a INT)")
        self.db.execute("ROLLBACK")


class KalicilikTest(Base):
    def test_kapat_ac(self):
        self.db.execute("ALTER TABLE musteri ADD telefon TEXT DEFAULT 'yok'")
        self.db.close()
        self.db = Database(self.dir)
        self.assertEqual(self.rows("SELECT telefon FROM musteri WHERE id = 2"), [["yok"]])
        self.db.execute("INSERT INTO musteri (ad) VALUES ('Yeni')")
        self.assertEqual(self.rows("SELECT id FROM musteri WHERE ad = 'Yeni'"), [[5]])

    def test_kilit(self):
        with self.assertRaises(DBError):
            Database(self.dir)

    def _bozuk_flush(self):
        flush, calls = Pager.flush, {"n": 0}

        def broken(self_):
            calls["n"] += 1
            if calls["n"] == 2:              # ikinci dosya yazılırken elektrik kesildi
                raise OSError("elektrik kesildi")
            flush(self_)
        return flush, broken

    def test_cokme_kurtarma_aninda(self):
        flush, broken = self._bozuk_flush()
        Pager.flush = broken
        try:
            with self.assertRaises(OSError):
                self.db.execute("UPDATE musteri SET ad = 'BOZUK'")
        finally:
            Pager.flush = flush
        self.assertFalse(os.path.exists(os.path.join(self.dir, "hakengine.journal")))
        self.assertEqual(self.rows("SELECT COUNT(*) FROM musteri WHERE ad = 'BOZUK'"), [[0]])
        self.assertEqual(self.rows("SELECT ad FROM musteri WHERE id = 1"), [["Ali"]])

    def test_cokme_kurtarma_acilista(self):
        flush, broken = self._bozuk_flush()
        recover = journal.recover
        Pager.flush, journal.recover = broken, lambda *a: False     # program o anda kapandı gibi
        try:
            with self.assertRaises(OSError):
                self.db.execute("UPDATE musteri SET ad = 'BOZUK'")
        finally:
            Pager.flush, journal.recover = flush, recover
        self.assertTrue(os.path.exists(os.path.join(self.dir, "hakengine.journal")))
        for t in self.db.tables.values():
            t.close()
        self.db._unlock()
        self.db = Database(self.dir)           # açılışta journal geri yüklenir
        self.assertEqual(self.rows("SELECT COUNT(*) FROM musteri WHERE ad = 'BOZUK'"), [[0]])
        self.assertEqual(self.rows("SELECT ad FROM musteri WHERE id = 1"), [["Ali"]])

    def test_truncate_ve_drop(self):
        self.db.execute("TRUNCATE TABLE siparis")
        self.assertEqual(self.rows("SELECT COUNT(*) FROM siparis"), [[0]])
        self.db.execute("INSERT INTO siparis (musteri_id) VALUES (1)")
        self.assertEqual(self.rows("SELECT id FROM siparis"), [[1]])
        self.db.execute("DROP TABLE siparis")
        self.assertEqual(self.rows("SELECT COUNT(*) FROM sys.tables"), [[1]])


class SistemTest(Base):
    def test_sys_tablolari(self):
        self.assertEqual(self.rows("SELECT name, rows FROM sys.tables ORDER BY name"),
                         [["musteri", 4], ["siparis", 5]])
        self.assertEqual(self.rows("SELECT column_name FROM sys.columns WHERE table_name = 'siparis' "
                                   "ORDER BY ordinal"), [["id"], ["musteri_id"], ["tutar"]])
        self.assertEqual(self.rows("SELECT COUNT(*) FROM sys.indexes WHERE is_primary_key = 1"), [[2]])


if __name__ == "__main__":
    unittest.main()

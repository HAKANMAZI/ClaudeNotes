-- HakEngine v2 örnek: küçük şirket veritabanı
-- Çalıştırma (v2 klasöründen):  python hakengine.py sirket_db examples/sirket.sql

DROP TABLE IF EXISTS gorev;
DROP TABLE IF EXISTS calisan;
DROP TABLE IF EXISTS departman;
DROP VIEW IF EXISTS calisan_ozet;

-- 1) Tablolar: IDENTITY, DEFAULT, UNIQUE, NOT NULL
CREATE TABLE departman (
    id    INT IDENTITY(1,1) PRIMARY KEY,
    ad    NVARCHAR(50) NOT NULL UNIQUE,
    sehir NVARCHAR(30) DEFAULT 'Kerkük'
);

CREATE TABLE calisan (
    id            INT IDENTITY(100,1) PRIMARY KEY,
    ad            NVARCHAR(50) NOT NULL,
    departman_id  INT,
    maas          DECIMAL(10,2),
    ise_giris     DATE,
    yonetici_id   INT
);

CREATE TABLE gorev (
    id          INT IDENTITY PRIMARY KEY,
    calisan_id  INT NOT NULL,
    baslik      TEXT,
    durum       TEXT DEFAULT 'açık'
);

-- 2) İndeks: JOIN ve WHERE için
CREATE INDEX IX_calisan_departman ON calisan (departman_id);
CREATE INDEX IX_gorev_calisan ON gorev (calisan_id);

-- 3) Veri
INSERT INTO departman (ad) VALUES ('Yazılım'), ('Muhasebe');
INSERT INTO departman (ad, sehir) VALUES ('Satış', 'İstanbul'), ('Ar-Ge', 'Ankara');

INSERT INTO calisan (ad, departman_id, maas, ise_giris, yonetici_id) VALUES
    ('Hasan',  1, 95000, '2015-03-01', NULL),
    ('Ali',    1, 62000, '2019-07-15', 100),
    ('Ayşe',   1, 71000, '2018-01-10', 100),
    ('Mehmet', 2, 48000, '2021-05-20', NULL),
    ('Zeynep', 3, 55000, '2020-09-01', NULL),
    ('Fatma',  3, 51000, '2022-02-14', 104),
    ('Can',   NULL, 40000, '2023-11-01', NULL);

INSERT INTO gorev (calisan_id, baslik) VALUES (101, 'Giriş ekranı'), (101, 'Raporlama'), (102, 'Veritabanı yedeği');
INSERT INTO gorev (calisan_id, baslik, durum) VALUES (103, 'Yıl sonu kapanışı', 'bitti'), (104, 'Bayi ziyareti', 'bitti');

-- 4) JOIN + GROUP BY: departman başına kişi ve ortalama maaş
SELECT d.ad AS departman, COUNT(c.id) AS kisi, ROUND(AVG(c.maas), 0) AS ort_maas
FROM departman d
LEFT JOIN calisan c ON c.departman_id = d.id
GROUP BY d.ad
ORDER BY kisi DESC, departman;

-- 5) Kendine JOIN (self join): çalışan ve yöneticisi
SELECT c.ad AS calisan, y.ad AS yonetici
FROM calisan c
JOIN calisan y ON y.id = c.yonetici_id
ORDER BY c.ad;

-- 6) Alt sorgu: departmanının ortalamasından fazla kazananlar (ilişkili alt sorgu)
SELECT c.ad, c.maas
FROM calisan c
WHERE c.maas > (SELECT AVG(x.maas) FROM calisan x WHERE x.departman_id = c.departman_id)
ORDER BY c.maas DESC;

-- 7) EXISTS: hiç görevi olmayanlar
SELECT ad FROM calisan c
WHERE NOT EXISTS (SELECT 1 FROM gorev g WHERE g.calisan_id = c.id)
ORDER BY ad;

-- 8) CASE ve tarih fonksiyonu
SELECT ad,
       YEAR(ise_giris) AS yil,
       CASE WHEN maas >= 70000 THEN 'yüksek'
            WHEN maas >= 50000 THEN 'orta'
            ELSE 'başlangıç' END AS seviye
FROM calisan
ORDER BY yil;

-- 9) VIEW
CREATE VIEW calisan_ozet AS
SELECT c.ad, d.ad AS departman, d.sehir, c.maas
FROM calisan c LEFT JOIN departman d ON d.id = c.departman_id;

SELECT * FROM calisan_ozet WHERE sehir = 'Kerkük' ORDER BY maas DESC;

-- 10) Transaction: zam yap, görevleri kapat, sonra geri al
BEGIN TRANSACTION;
UPDATE calisan SET maas = maas * 1.10 WHERE departman_id = 1;
UPDATE gorev SET durum = 'bitti';
SELECT SUM(maas) AS zamli_toplam FROM calisan;
ROLLBACK;
SELECT SUM(maas) AS gercek_toplam FROM calisan;

-- 11) Sorgu planı
EXPLAIN
SELECT c.ad, g.baslik
FROM calisan c
JOIN gorev g ON g.calisan_id = c.id
WHERE c.id = 101;

-- 12) Sistem tabloları
SELECT name, rows, pages, indexes FROM sys.tables ORDER BY name;
SELECT index_name, table_name, column_name, is_unique FROM sys.indexes ORDER BY table_name;

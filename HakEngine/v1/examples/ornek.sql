-- HakEngine örnek betiği
CREATE TABLE urun (id INT PRIMARY KEY, ad VARCHAR(50) NOT NULL, fiyat DECIMAL, kategori TEXT);
INSERT INTO urun VALUES (1,'Elma',12.5,'Meyve'),(2,'Armut',15,'Meyve'),(3,'Süt',30,'İçecek'),(4,'Çay',80,'İçecek');
INSERT INTO urun (id, ad) VALUES (5,'Ekmek');
SELECT * FROM urun WHERE fiyat > 13 ORDER BY fiyat DESC;
SELECT kategori, COUNT(*) AS adet, AVG(fiyat) AS ortalama FROM urun GROUP BY kategori;
SELECT TOP 2 ad FROM urun WHERE ad LIKE '%e%';
UPDATE urun SET fiyat = fiyat * 2 WHERE id = 1;
BEGIN TRANSACTION;
DELETE FROM urun WHERE kategori = 'Meyve';
ROLLBACK;
SELECT COUNT(*) AS toplam FROM urun;

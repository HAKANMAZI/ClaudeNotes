# Hesap Tablom

Windows için hafif, Türkçe bir hesap tablosu uygulaması. Python ve PySide6 (Qt) ile yazıldı.

## İndir

[HesapTablom.exe'yi indir](https://github.com/HAKANMAZI/ClaudeNotes/releases/download/hesap-tablom/HesapTablom.exe). Kurulum gerekmez; çift tıklayın, açılsın.

Windows ilk açılışta "Windows kişisel bilgisayarınızı korudu" uyarısı gösterebilir: **Ek bilgi → Yine de çalıştır**.

## Özellikler

- Formüller: `=A1+B1`, `=TOPLA(A1:A10)`, `=EĞER(A1>5;"Evet";"Hayır")`
- Türkçe ve İngilizce fonksiyon adları: TOPLA/SUM, ORTALAMA/AVERAGE, MIN, MAK/MAX, BAĞ_DEĞ_SAY/COUNT, EĞER/IF, EĞERHATA/IFERROR, ETOPLA/SUMIF, EĞERSAY/COUNTIF, DÜŞEYARA/VLOOKUP, YUVARLA/ROUND, BİRLEŞTİR, UZUNLUK, BÜYÜKHARF, KÜÇÜKHARF, VE, YADA, DEĞİL, BUGÜN, ŞİMDİ ve daha fazlası
- Birden çok sayfa ve sayfalar arası başvuru (`=Sayfa2!A1`)
- Kopyala, kes, yapıştır (formüller otomatik kayar), aşağı doldur
- Geri al / yinele
- Kalın, italik, altı çizili, yazı ve dolgu rengi, hizalama
- Sayı biçimleri: sayı, tam sayı, para (₺), yüzde
- Satır/sütun ekleme ve silme (formüller güncellenir), sıralama, otomatik toplam
- `.htab` dosya biçimi, CSV içe/dışa aktarma, yazdırma
- Otomatik saklama: uygulamayı kapatıp açtığınızda kaldığınız yerden devam eder

## Kısayollar

| Tuş | İşlev |
|---|---|
| Enter / Tab | Onayla, aşağı / sağa geç |
| F2 veya çift tık | Hücreyi düzenle |
| Delete | Seçimi temizle |
| Ctrl+C / X / V | Kopyala / kes / yapıştır |
| Ctrl+D | Aşağı doldur |
| Ctrl+Z / Y | Geri al / yinele |
| Ctrl+B / I / U | Kalın / italik / altı çizili |
| Ctrl+S / O / N | Kaydet / aç / yeni |
| Alt+= | Otomatik toplam |
| F1 | Yardım |

## Kaynaktan çalıştırma

```bat
python -m pip install -r requirements.txt
python app.py
```

## EXE derleme

`build.bat` dosyasını çalıştırın. Sonuç: `dist\HesapTablom.exe`.

`hesap-tablom/` klasörüne her gönderimde GitHub Actions EXE'yi otomatik derler ve yukarıdaki indirme linkini günceller.

## Testler

```bat
python -m pytest -q tests
```

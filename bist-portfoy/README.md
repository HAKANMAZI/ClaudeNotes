# BIST Portföy

Google Sheets üzerinde çalışan BIST hisse takip tablosu ve onu okuyan web uygulaması.

- **Google Sheet:** [BIST Sağlam 10 Hisse Takip](https://docs.google.com/spreadsheets/d/1JYXC2-b5fGWKfwlyzpFhlIs9-0edZW5zEjexRMlSVlY/edit) (gizli, yalnızca sahibi açabilir)
- **Web uygulaması:** [BIST Portföy Masası](https://claude.ai/artifact/LkvR34YvKy2C8UbrysNjdA) (claude.ai Artifact)

## Klasörler

| Yol | İçerik |
|---|---|
| `web-app/index.html` | Web uygulaması. Google Sheet'i claude.ai'deki Google Sheets bağlantısıyla okur ve alım/satım bilgilerini Sheet'e yazar. Yalnızca claude.ai içinde açıldığında veri gelir. |
| `excel/BIST_Saglam_10_Hisse_Takip.xlsx` | İlk sürüm tablo. Google Sheets'e içe aktarılınca GOOGLEFINANCE formülleri çalışır. |
| `scripts/build_xlsx.py` | Excel dosyasını üreten openpyxl betiği. |
| `haftalik-gorev.md` | Her pazartesi 07:41'de (İstanbul) çalışan Claude görevinin talimatı. |

## Google Sheet yapısı

**Takip** sekmesi, satır 6–35 (en fazla 30 hisse). A sütununa kod yazınca satır dolar.

| Bölüm | Sütunlar |
|---|---|
| Portföyüm | Alınan/satılan adet, ortalama fiyatlar, alış/satış tarihi, eldeki maliyet, güncel değer, gerçekleşen ve gerçekleşmemiş K/Z, enflasyon, reel K/Z |
| Performans | Gün, 5, 15, 30, 60, 240 işlem günü getirisi |
| Hacim | Günlük ve 10/20/50 gün ortalama hacim, yıllık hacim grafiği |
| Fiyat & Teknik | Fiyat, MA10/21/50/200, ▲▼, 52 hafta zirveden uzaklık, RSI (14) |
| Temel Analiz | F/K, piyasa değeri, HBK, kârlılık, borç, beklenti, Temel Not, Değerleme (F/K), PD/DD, Net Borç/FAVÖK, ROE, sonraki bilanço |
| KAP İş/İhale | Son 1 ay, son 3 ay, sipariş/iş bakiyesi |
| Ralli Takip | Giriş fiyatı/tarihi, max fiyat, hedef, stop, getiri, R/K, XU100'e göre, max kazanç |

Diğer sekmeler:

- **Veri:** BIST 100 ve BIST 30 endeksleri.
- **Enflasyon:** TÜİK aylık TÜFE ve zincir endeks (Ocak 2020'den).
- **Geçmiş (gizli):** GOOGLEFINANCE ile çekilen ~420 günlük fiyat geçmişi.

Sarı hücreler girdi: Hedef %, Stop %, ROE eşiği, Giriş Tarihi ve portföy alanları.

## Notlar

- Sheet `tr_TR` yerel ayarında. API ile formül yazarken yerel ayar geçici olarak `en_US` yapılıp sonra geri alındı.
- GOOGLEFINANCE geçmiş verisi yalnızca Sheet tarayıcıda açıkken hesaplanır. API ile okunduğunda bazı teknik hücreler boş gelebilir.
- Temel analiz metinleri ve KAP verileri elle ya da haftalık görevle güncellenir; yatırım tavsiyesi değildir.

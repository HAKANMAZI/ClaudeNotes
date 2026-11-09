# Haftalık görev: KAP İhale Güncelleme

Claude Code Routine. Her pazartesi 07:41 (Europe/Istanbul), Google Sheets bağlayıcısıyla yeni bir oturumda çalışır ve özeti telefona bildirim olarak gönderir.

- Cron: `CRON_TZ=Europe/Istanbul 41 7 * * 1`
- Bağlayıcı: Google Sheets

## Talimat

Görev: "BIST Sağlam 10 Hisse Takip" Google E-tablosunda (1) Enflasyon sayfasındaki TÜFE verisini, (2) Takip sayfasındaki temel oranları ve (3) KAP iş/ihale/sipariş sütunlarını güncelle. Kullanıcıyla Türkçe iletişim kur.

E-tablo: https://docs.google.com/spreadsheets/d/1JYXC2-b5fGWKfwlyzpFhlIs9-0edZW5zEjexRMlSVlY/edit (Google Sheets bağlayıcısını kullan; önce google-workspace skill'ini ve sheets referansını oku). Google Sheets araçları bu oturumda yoksa hiçbir şey yazma; kullanıcıya bağlayıcının bu görevde kullanılamadığını söyle ve bulduğun değerleri özet olarak ver.

GENEL KURAL: Yalnızca aşağıda adı geçen hücrelere yaz. Kullanıcının girdiği portföy hücrelerine (Takip C:H), sarı eşik hücrelerine, formüllere ve diğer sütunlara asla dokunma. Uydurma rakam yazma; teyit edemediğin değeri boş bırak/mevcut değeri koru ve özette belirt. Not: API üzerinden okurken GOOGLEFINANCE geçmiş verisi (Geçmiş sayfası) #N/A görünebilir; bu normaldir, düzeltmeye çalışma.
Sütunları her zaman Takip 5. satırdaki başlık adlarına göre bul (kullanıcı sütun ekleyebilir, satırları sıralayabilir). Hisse kodları A6:A35 (boş satırları atla). Önce Takip!A5:BN35'i oku.

### (1) Enflasyon
- Sayfa "Enflasyon": A4:A99 = ayın ilk günü (A4 = Ocak 2020), B4:B99 = TÜİK TÜFE aylık değişim oranı, C = formül (dokunma).
- TÜİK'in açıkladığı son aya kadar boş olan her ay için aylık TÜFE değişimini ondalık sayı olarak yaz (ör. %1,84 → 0.0184; JSON sayı). Mevcut değerleri değiştirme. 12 aylık zincirin açıklanan yıllık oranla tutarlı olduğunu kontrol et.

### (2) Temel oranlar (her hisse için zorunlu)
Başlıklar: "PD/DD", "Net Borç / FAVÖK", "ROE (Özkaynak Kârlılığı)", "Sonraki Bilanço".
- Yalnızca haber araması YAPMA. Her hisse kodu için WebFetch ile https://stockanalysis.com/quote/ist/<KOD>/statistics/ sayfasını aç.
  - PD/DD = "PB Ratio".
  - Net Borç / FAVÖK = (Total Debt − Cash) / EBITDA (son 12 ay). Net nakitse negatif. EBITDA negatif/yoksa veya banka/aracı kurumsa boş bırak.
  - ROE = "Return on Equity (ROE)" ondalık (ör. %25,3 → 0.253).
  - Sonraki Bilanço = "Earnings Date" (GG.AA.YYYY metni). Yoksa veya geçmişteyse boş bırak.
- stockanalysis açılmazsa sırasıyla fintables.com/sirketler/<KOD>, isyatirim şirket kartı, borsacoo.com/firma/<KOD> dene.
- TERA'da bedelsiz nedeniyle veriler tutarsızsa boş bırak.
- Sayıları JSON sayı olarak yaz.

### (3) KAP iş / ihale / sipariş
Başlıklar: "Son 1 Ay KAP İş/İhale", "Son 3 Ay KAP İş/İhale", "Toplam Sipariş / İş Bakiyesi".
- HER hisse için tara. 1 ay: son 30 gün KAP'a bildirilen yeni iş/sözleşme/ihale/sipariş toplamı; 3 ay: son 90 gün; bakiye: en son açıklanan sipariş/iş bakiyesi ve dönemi.
- Önce kap.org.tr'yi dene; olmazsa haber sitelerinden tara. Para birimlerini güncel kurla USD'ye çevir.
- Hücre biçimi: "≈4,7 Mr $ (6 bildirim)", "Bildirim yok", "Sipariş bazlı değil", "Açıklanmıyor".
- AÇIKLAMA bölümündeki "• KAP İş/İhale" satırını tarih, kaynak ve kur ile güncelle.

Her adımdan sonra get_values ile doğrula. Sonunda kısa bir Türkçe özet ver ve en sonuna tablonun linkini ekle. Bu yatırım tavsiyesi değildir.

# Play Kazanç

Google Play uygulamalarının indirme verisine göre **yaklaşık aylık kazancını** tahmin eden ve **trend uygulamaları** takip eden web uygulaması.

## Özellikler
- Kelimeyle uygulama arama, sonuçları tahmini kazanca göre sıralama
- Uygulama detayı: düşük / orta / yüksek aylık kazanç, reklam / uygulama içi satın alma / ücretli satış dağılımı
- Ülke seçimi (Türkiye, ABD, Almanya, İngiltere) – reklam gelirini etkiler
- Takip listesi: her güncellemede indirme sayısı kaydedilir, günlük indirme hızı ve büyüme hesaplanır
- Trendler sayfası: takip edilenleri hızına göre sıralar

## Kurulum
```bash
pip install -r requirements.txt
python app.py
```
Tarayıcıda: http://localhost:5000

İnternetsiz deneme (örnek veri):
```bash
DEMO=1 python app.py        # Windows: set DEMO=1 && python app.py
```

## Günlük otomatik güncelleme
Trendlerin doğru çıkması için takip listesi her gün güncellenmeli:
```bash
curl -X POST http://localhost:5000/guncelle
```
Bunu Windows Görev Zamanlayıcı veya cron ile günde bir çalıştırın.

## Tahmin nasıl yapılıyor?
`tahmin.py` içinde:
- **Aylık aktif kullanıcı** = toplam indirme × kategori oranı
- **Reklam** = günlük aktif × günlük gösterim × ülke eCPM
- **Uygulama içi satın alma** = aylık aktif × ödeme yapan oranı × harcama
- **Ücretli** = aylık indirme × fiyat
- Google komisyonu (yüzde otuz) düşülür

Varsayımları `tahmin.py` dosyasından değiştirebilirsiniz.

> Not: Google Play gerçek gelir paylaşmaz. Sonuçlar yaklaşıktır.

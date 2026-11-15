# Radyo

Tarayıcıda çalışan internet radyosu ve podcast uygulaması. Kurulum gerekmez; `index.html` dosyasını tarayıcıda açmanız yeterli.

## Sürümler

| Sürüm | Klasör | İçerik |
|---|---|---|
| v1 | [`v1/`](v1/index.html) | Radyo |
| v2 | [`v2/`](v2/index.html) | Radyo + Podcast |
| v3 | [`v3/`](v3/index.html) | Radyo + Podcast + Köşe Yazıları + yedek kaynaklar (en güncel) |

## v1 – Radyo

- Ülkeye ve türe göre istasyon listesi (Pop, Haber, Türkü, Arabesk, Klasik, Belgesel, Sohbet)
- Arama tüm radyolarda yapılır; yazdıkça sonuçlar gelir
- Favoriler (tarayıcıda saklanır)
- "Benim radyolarım": listede olmayan radyoyu ad, frekans ve yayın adresiyle elle ekleme
- Radyo Belgesel hazır ekli
- Yayın akışı için istasyonun web sitesine bağlantı
- Çal / durdur, ses ayarı

## v2 – Podcast

- Podcast arama (yazdıkça), "Tümü" sekmesi (en yeni bölümü olan en üstte) ve kategoriler: Belgesel, Tarih, Bilim, Haber, Ekonomi, İş dünyası, Spor, Komedi, Hikâye, Çocuk
- Bölüm listesi: tarih, süre, ne kadarının dinlendiği
- Kaldığın yerden devam ve "⏯ Devam et" listesi
- Abonelik (★ Aboneliklerim)
- 15 sn geri, 30 sn ileri, sarma çubuğu, hız (0,75x – 2x)
- ⬇ Bölümü indirip internetsiz dinleme
- ⏾ Kapanma zamanlayıcısı: 15, 30, 45 dakika, 1 saat veya istenen süre (radyo ve podcast)
- 🚫 Engellenenler: belirli kelime veya isimleri içeren podcastleri gizleme

## v3 – Köşe Yazıları ve yedek kaynaklar

- 📰 Köşe yazıları: Sabah, Sözcü, Cumhuriyet, Hürriyet, Milliyet, Habertürk
  - Yazar, başlık, tarih ve kısa özet; en yeni üstte
  - Yazıya dokununca gazetenin kendi sitesinde açılır
  - 🔊 Özeti sesli dinleme
  - Yazar/başlık arama
  - ➕ Gazete ekle: istediğiniz gazetenin veya yazarın RSS adresini ekleme
- Yedek kaynaklar (ücretsiz kaynak kapanırsa):
  - Radyo: beş liste sunucusu → son kaydedilen liste → uygulamanın içindeki yedek Türk radyoları listesi
  - Podcast: Apple → ikinci ücretsiz arşiv (fyyd) → son kaydedilen liste
  - Köşe yazıları: doğrudan RSS → iki ücretsiz çevirici → son kaydedilen yazılar
  - Kaynak değişince ekranda sarı uyarı çıkar

## Radyolar ve podcastler nereden geliyor?

- **Radyo listesi:** [Radio Browser](https://www.radio-browser.info), ücretsiz ve açık veritabanı.
- **Podcastler:** Apple'ın herkese açık ve ücretsiz podcast arşivi (iTunes Search API). Üyelik veya anahtar gerekmez.
- **Köşe yazıları:** Gazetelerin herkese açık RSS akışları. Yazının tamamı gazetenin sitesinde okunur.
- **Ses:** Uygulama sesi kendisi yayınlamaz; radyonun veya podcastin kendi sunucusundan doğrudan çalınır.

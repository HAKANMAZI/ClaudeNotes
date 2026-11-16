# Radyo ve podcast kaynakları

Araştırma tarihi: Kasım 2026. Uygulamada ⚙️ **Kaynaklar** panelinden her biri açılıp kapatılabilir.

## Radyo

| Kaynak | Anahtar | Ücret | Durum | Not |
|---|---|---|---|---|
| Radio Browser | Yok | Ücretsiz | ✅ Açık (ana kaynak) | Açık topluluk veritabanı. Ülke, şehir, dil, tür filtresi. Birden fazla sunucu, biri çökerse diğeri. |
| TuneIn | Yok | — | ⚙️ İsteğe bağlı, kapalı gelir | Herkese açık ama resmî olmayan servis (opml.radiotime.com). Resmî API ortaklık (partnerId) ister. Google Play sürümünde kapalı tutulması önerilir. |
| SHOUTcast | DevID gerekir | Başvuru ile | ⚙️ Anahtarla | Lisans sözleşmesi kabul edilip shoutcast.com/Developer üzerinden başvurulur. |
| Radio Garden | — | — | ❌ Eklenmedi | Resmî API yok; ayrıca 2022'den beri Türkiye'de erişime kapalı (RTÜK). |

## Podcast

| Kaynak | Anahtar | Ücret | Durum | Not |
|---|---|---|---|---|
| Apple Podcasts / iTunes | Yok | Ücretsiz | ✅ Açık | Arama, kategori (genreId), ülkeye göre popüler listeler, bölümler. |
| fyyd | Yok | Ücretsiz | ✅ Açık | İkinci arşiv; dil bilgisi var. |
| Podcast Index | Arama: yok · Diğerleri: key + secret | Tamamen ücretsiz | ✅ Açık | Anahtarsız "Apple yerine" arama ucu. Ücretsiz anahtarla dile ve kategoriye göre popüler (trending) listeler. |
| Listen Notes | Gerekir | Ücretsiz paket: ayda 300 istek | ⚙️ Anahtarla | Kotayı aşınca ay sonuna kadar durur. Sonuçların yanında "Powered by Listen Notes" yazması şart. |
| PodcastDataAPI | — | — | ❌ Eklenmedi | Bu adla resmî, belgelenmiş bir servis bulunamadı. Listen Notes'un API'si "PodcastAPI.com" adıyla da geçiyor. |
| RSS | Yok | Ücretsiz | ✅ Her zaman açık | "➕ RSS ekle" ile herhangi bir podcast eklenir. |
| Spotify for Creators | Yok | Ücretsiz | ✅ RSS ile | Spotify'ın API'si bölüm sesini çalmaya izin vermez. Spotify for Creators (Anchor) podcastlerinin RSS adresi kullanılır. |

## Nasıl çalışıyor

- **Tek katalog:** açık kaynaklar aynı anda sorulur, sonuçlar birleştirilir.
- **Tekilleştirme:** radyoda aynı ad veya aynı yayın adresi; podcastte aynı RSS adresi, aynı kimlik veya aynı ad bir kez gösterilir. Eksik bilgiler (kapak, RSS) diğer kaynaktan tamamlanır.
- **Çalışmayan yayınlar:** Radio Browser'ın kendi kontrolü (bozukları gizler) + uygulamanın denemesi. Çalmayan radyo bir gün işaretli kalır ve listenin sonuna iner.
- **Hata yedeği:** bir kaynak çökerse diğerleri gösterilir, ekranda sarı uyarı çıkar. Hepsi çökerse son kaydedilen liste gösterilir.
- **Veri tasarrufu:** radyo listesi on dakika, podcast ve bölüm listeleri otuz dakika, şehir listesi bir gün saklanır. Logolar ekrana gelince yüklenir.
- **Tarayıcı engeli (CORS):** bazı servisler tarayıcıdan doğrudan sorguya izin vermez. Android uygulaması bu istekleri kendisi yapar; web sürümü herkese açık aracı servisleri dener.
- **Anahtarlar** sadece cihazda saklanır, hiçbir yere gönderilmez (sadece ilgili servise).

# Radyo – v2 Android

**Ne:** v2 web sürümünün (Radyo + Podcast) Android uygulaması.

**İndir (telefona kur):** https://github.com/HAKANMAZI/ClaudeNotes/releases/download/radyo-android/Radyo.apk
Telefonda açın, "bilinmeyen kaynaklardan yüklemeye izin ver" deyip kurun.

## v2 web sürümünden farkları

- Ekran kapalıyken ve başka uygulamaya geçince yayın sürer; bildirimde "Çalıyor" ve **Durdur** düğmesi
- Podcast ⬇ indirme telefonun **Podcasts/Radyo** klasörüne yapılır (internetsiz dinlemek için)
- Telefonun geri tuşu sayfa içinde geri gider; son ekranda uygulama arka plana alınır, yayın kesilmez
- **Reklam yok, abonelik yok.** Sadece isteğe bağlı **❤️ Destek ol** düğmesi
  - Destek hiçbir özelliği açmaz
  - Google Play kuralı gereği ödeme Google Play üzerinden alınır
  - APK ile kurulunca destek bölümü çalışmaz; Google Play'den indirilince çalışır

## Klasör yapısı

| Dosya | Ne işe yarar |
|---|---|
| `app/src/main/assets/www/index.html` | Uygulamanın ekranı (v2 sayfası + Android eklemeleri) |
| `app/src/main/java/.../MainActivity.kt` | Sayfayı açar, indirme, geri tuşu, bağlantılar |
| `app/src/main/java/.../PlaybackService.kt` | Arka planda çalma ve bildirim |
| `app/src/main/java/.../Destek.kt` | Gönüllü destek (Google Play ödeme sistemi) |
| `.github/workflows/radyo-android.yml` | GitHub'da otomatik derleme |

## Google Play'e yükleme adımları

1. **Yükleme anahtarı:** GitHub > Settings > Secrets and variables > Actions bölümüne dört gizli değer ekleyin:
   `UPLOAD_KEYSTORE_BASE64`, `UPLOAD_STORE_PASSWORD`, `UPLOAD_KEY_ALIAS`, `UPLOAD_KEY_PASSWORD`.
   Eklendikten sonra her derlemede Releases'e `Radyo-Play.aab` de gelir.
2. **Play Console:** Yeni uygulama oluşturun, "Ücretsiz" seçin, `Radyo-Play.aab` dosyasını yükleyin.
3. **Destek ürünleri:** Play Console > Para kazanma > Uygulama içi ürünler > tek seferlik ürün oluşturun:
   - `destek_kucuk` (ör. Küçük destek)
   - `destek_orta` (ör. Orta destek)
   - `destek_buyuk` (ör. Büyük destek)
   Fiyatları siz belirleyin. Ürün açıklamasına "Gönüllü destek, hiçbir özellik açmaz" yazın.
   Ödeme alabilmek için Play Console'da ödeme profili gerekir.
4. **Reklam beyanı:** "Uygulamanızda reklam var mı?" sorusuna **Hayır**.
5. **Veri güvenliği formu:** Uygulama kişisel veri toplamaz; favoriler ve ayarlar sadece telefonda saklanır.
6. **Gizlilik politikası adresi:** https://github.com/HAKANMAZI/ClaudeNotes/blob/main/radyo/v2-android/GIZLILIK.md
7. Her yeni sürümde `app/build.gradle.kts` içindeki `versionCode` bir artırılmalı.

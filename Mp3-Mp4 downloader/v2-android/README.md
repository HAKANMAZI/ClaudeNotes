# Mp3-Mp4 Downloader — v2 Android

YouTube ve diğer sitelerden videoları telefona **MP4 (video)** veya **MP3 (ses)** olarak indiren Android uygulaması.

**İndir (telefona kur):** https://github.com/HAKANMAZI/ClaudeNotes/releases/download/video-indirici-android/VideoIndirici.apk
(Kurulmazsa eski telefonlar için: https://github.com/HAKANMAZI/ClaudeNotes/releases/download/video-indirici-android/VideoIndirici-eski.apk)

## Kurulum
1. Linki telefonda açın, APK inecek.
2. Dosyayı açın, "bilinmeyen kaynaklardan yüklemeye izin ver" deyin.
3. "Yükle"ye basın.

Gereken: Android 10 veya üstü.

## Kullanım
1. Uygulamayı açın. İlk açılışta motor hazırlanır, "Hazır" yazısını bekleyin.
2. Linki kutuya yapıştırın ya da **📋 Panodan yapıştır** düğmesine basın.
3. Biçim seçin:
   - **Video MP4**: görüntü + ses. Kalite: En iyi, 1080p, 720p, 480p, 360p
   - **Ses MP3**: sadece ses, her yerde çalar. Kalite: 320, 192, 128 kbps
   - **Ses M4A**: sadece ses, orijinal kalite, daha küçük dosya
5. **İNDİR**'e basın. İlerleme çubuğu dolar.
6. Kapak resmi, başlık ve süre görünür. "Tamamlandı ✔" çıkınca **Aç** ile hemen oynatın.

**En kolay yol:** YouTube'da videoyu açın → **Paylaş** → **Video İndirici**. Link otomatik gelir.

**Dosyalar nerede?** Dosya Yöneticisi → **İndirilenler / VideoIndirici**

## v1'den farkları
- Telefonda çalışır, bilgisayar gerekmez
- Python ve ffmpeg uygulamanın içinde, ayrıca kurulum yok
- YouTube uygulamasından "Paylaş" ile link alma
- **İptal** düğmesi
- **🔄 İndirme motorunu güncelle** düğmesi (açılışta da kendiliğinden güncellenir)
- İndirme sırasında ekran kapanmaz

## v2.1 yenilikleri
- Yeni arayüz: kartlar, yeşil başlık, kapak resmi önizlemesi, "Aç" düğmesi
- M4A ses seçeneği, MP3 için kalite seçimi
- APK boyutu yetmiş MB'tan yaklaşık kırk beş MB'a indi (işlemciye göre ayrı APK)

## Güvenlik
- Tek izin: **İnternet**. Rehber, konum, kamera, mikrofon istemez.
- Reklam yok, takip yok, veri toplama yok.
- Kod açık kaynak, bu depoda. APK GitHub'da otomatik derlenir.
- Sadece `https://` ile başlayan linkler kabul edilir (komut gönderme engeli).
- Dışarıdan ayar dosyası ve komut çalıştırma kapalı (`--ignore-config`, `--no-exec`).
- Hata ayıklama modu kapalı yayın sürümü, yedekleme kapalı.

## Sorun giderme
- **YouTube hata veriyor:** "İndirme motorunu güncelle"ye basıp tekrar deneyin.
- **İndirme yarıda kesildi:** Uygulamayı indirme bitene kadar açık tutun.
- **Kurulmuyor:** Telefon Android 10'dan eskiyse çalışmaz.

## Klasör yapısı
| Dosya | Ne işe yarar |
|---|---|
| `app/src/main/java/.../MainActivity.kt` | Ekran, indirme, kaydetme |
| `app/src/main/res/layout/activity_main.xml` | Ekran tasarımı |
| `app/build.gradle.kts` | Ayarlar ve kütüphaneler (yt-dlp, ffmpeg) |
| `.github/workflows/video-indirici-android.yml` | GitHub'da otomatik APK derleme |

## Not
Telif hakkı olan içerikleri yalnızca izinli veya kişisel kullanım için indirin.
Google Play, YouTube indiren uygulamaları kabul etmez; bu uygulama APK ile kurulur.

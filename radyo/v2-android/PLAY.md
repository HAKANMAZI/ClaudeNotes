# Kızılelma Radyo – Google Play'e Yükleme Rehberi

Yüklemeyi Play Console hesabınızla siz yaparsınız. Aşağıdaki metinler ve görseller hazır, kopyalayıp yapıştırmanız yeterli.

## 1. Geliştirici hesabı

- https://play.google.com/console adresinden hesap açın (bir kerelik 25 dolar, kimlik doğrulama).
- **Kişisel hesap:** Yayına çıkmadan önce **12 test kullanıcısıyla 14 gün kapalı test** zorunlu (Kasım 2023'ten sonra açılan kişisel hesaplar için).
- **Kurum hesabı (şirket):** Bu test şartı yok, ama D-U-N-S numarası gerekir (ücretsiz, birkaç hafta sürebilir).

## 2. Yükleme dosyası (Radyo-Play.aab)

1. GitHub > ClaudeNotes > **Settings > Secrets and variables > Actions > New repository secret**
2. `radyo-play-anahtar-bilgileri.txt` dosyasındaki dört değeri ekleyin:
   `UPLOAD_KEYSTORE_BASE64`, `UPLOAD_STORE_PASSWORD`, `UPLOAD_KEY_ALIAS`, `UPLOAD_KEY_PASSWORD`
3. GitHub > **Actions > Radyo Android > Run workflow**
4. Bitince indirin: https://github.com/HAKANMAZI/ClaudeNotes/releases/download/radyo-android/Radyo-Play.aab

## 3. Uygulamayı oluşturma

Play Console > **Uygulama oluştur**
- Ad: **Kızılelma Radyo**
- Dil: Türkçe
- Uygulama / Oyun: **Uygulama**
- Ücretsiz / Ücretli: **Ücretsiz**

## 4. Mağaza sayfası

**Kısa açıklama (80 karakter):**
> Türk radyoları ve podcastler tek yerde. Reklamsız, aboneliksiz, ücretsiz.

**Tam açıklama:**
> Kızılelma Radyo ile Türkiye'nin ve dünyanın internet radyolarını, binlerce podcasti tek uygulamada dinleyin.
>
> 📻 RADYO
> • Yüzlerce Türk radyosu: pop, haber, türkü, arabesk, klasik, belgesel, sohbet
> • Yazdıkça arama, favoriler
> • Listede olmayan radyoyu kendiniz ekleyin
> • Ekran kapalıyken de çalmaya devam eder
>
> 🎙️ PODCAST
> • Binlerce Türkçe podcast; en yeni bölümler en üstte
> • Kaldığınız yerden devam edin
> • Abone olun, bölümleri indirip internetsiz dinleyin
> • İleri/geri sarma, hız ayarı
>
> 🌙 KAPANMA ZAMANLAYICISI
> • 15, 30, 45 dakika, 1 saat veya istediğiniz süre sonunda kendiliğinden kapanır
>
> ❤️ REKLAMSIZ VE ABONELİKSİZ
> Uygulamada reklam ve abonelik yoktur. Beğenirseniz isteğe bağlı olarak destek olabilirsiniz; destek hiçbir özelliği açmaz.
>
> Kişisel veri toplanmaz. Favorileriniz ve ayarlarınız sadece telefonunuzda saklanır.

**Görseller** (depoda `radyo/amblem/` klasörü):
- Uygulama simgesi 512x512: `play-simge-512.png`
- Tanıtım görseli 1024x500: `play-tanitim-1024x500.png`
- Telefon ekran görüntüleri: en az 2 adet. Uygulamadan kendiniz alın (Radyo listesi, Podcast, çalarken, kapanma zamanlayıcısı).

**Kategori:** Müzik ve Ses
**İletişim e-postası:** sizin e-postanız
**Gizlilik politikası:** https://github.com/HAKANMAZI/ClaudeNotes/blob/main/radyo/v2-android/GIZLILIK.md

## 5. Uygulama içeriği soruları (Politika > Uygulama içeriği)

| Soru | Cevap |
|---|---|
| Reklam içeriyor mu? | **Hayır** |
| Uygulama erişimi | Tüm özellikler kısıtlama olmadan kullanılabilir (giriş yok) |
| İçerik derecelendirmesi | Anketi doldurun: şiddet/cinsellik/kumar yok. Kullanıcıların internetten içerik dinlediğini belirtin |
| Hedef kitle | 18 yaş ve üzeri (veya 13+) |
| Veri güvenliği | Veri toplanmıyor, paylaşılmıyor. Satın alma bilgisi Google Play'de kalır |
| Haber uygulaması mı? | Hayır |
| Devlet uygulaması mı? | Hayır |
| Ön plan hizmeti izni (Foreground service) | **Medya oynatma** seçin. Açıklama: "Kullanıcı radyo veya podcast başlattığında, ekran kapalıyken ve uygulama arka plandayken ses çalmaya devam etmek için." Play kısa bir video isteyebilir: uygulamada radyoyu başlatıp ekranı kapatın, bildirimdeki "Durdur" düğmesini gösterin, telefonla kaydedin |
| Finans özellikleri | Yok |
| Sağlık uygulaması mı? | Hayır |

**Not:** ⚙️ Kaynaklar panelinde TuneIn varsayılan kapalıdır; Play sürümünde kapalı bırakın (resmî izin gerektirir).

## 6. Gönüllü destek ürünleri

Play Console > **Para kazanma > Ürünler > Uygulama içi ürünler** (önce bir AAB yüklenmiş olmalı, ödeme profili gerekir)

| Ürün kimliği | Ad | Örnek fiyat |
|---|---|---|
| `destek_kucuk` | Küçük destek | 20 TL |
| `destek_orta` | Orta destek | 50 TL |
| `destek_buyuk` | Büyük destek | 100 TL |

Açıklama: "Gönüllü destek. Hiçbir özelliği açmaz. Teşekkürler!" Ürünleri **Etkin** yapın.

## 7. Test ve yayın

1. **Test > Kapalı test > Sürüm oluştur**, `Radyo-Play.aab` yükleyin.
2. Test kullanıcılarının Gmail adreslerini ekleyin (kişisel hesapta en az 12, 14 gün boyunca).
3. Test bağlantısını paylaşın; uygulamayı Play'den kursunlar ve silmesinler.
4. 14 gün dolunca **Üretim erişimi için başvur**, sonra **Üretim > Sürüm oluştur**.
5. Her yeni sürümde `app/build.gradle.kts` içindeki `versionCode` bir artırılmalı (Claude bunu yapıyor).

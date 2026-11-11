# Fiş Takip - Android uygulaması

Web arayüzünü (`../web/index.html` ve `../web/en/index.html`) Capacitor ile Android uygulamasına çevirir.
APK, GitHub Actions'ta otomatik derlenir ve **Releases** bölümüne konur.

## Telefona kurulum
1. Depoda **Releases** bölümünü aç, en son `Fiş Takip Android` sürümünü seç.
2. Türkçe için `fis-takip-tr.apk`, İngilizce için `fis-takip-en.apk` dosyasını telefona indir ve aç.
3. Telefon izin isterse "bu kaynaktan yüklemeye izin ver" de.
4. Uygulamayı açınca ilk fiş okumada Anthropic API anahtarını gir.

## Notlar
- Veriler telefonda saklanır. Tarayıcıdaki ve Streamlit'teki verilerden ayrıdır.
- Verileri taşımak için ⚙️ → Yedek yükle kullan.
- Bu bir test (debug) APK'sıdır; Play Store'a koymak için imzalı sürüm gerekir.

## Elle derleme
```
npm ci
mkdir -p www && cp ../web/index.html www/index.html
npx cap add android
cd android && ./gradlew assembleDebug
```

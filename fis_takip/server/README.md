# Fiş Takip - test sürümü
Gereken: Node 18+, Anthropic API anahtarı.
## Yerelde çalıştır
    npm install
    ACCESS_CODE=test123 npm start   # ANTHROPIC_API_KEY isteğe bağlı: verilmezse her kullanıcıdan kendi anahtarı istenir
Tarayıcıda http://localhost:3000 aç. Telefondan denemek için aynı ağdan bilgisayarın IP'siyle aç.
## İnternete aç (testçiler için)
Render.com / Railway / Fly.io gibi bir yere yükle. Start komutu: `npm start`.
Ortam değişkenleri: ANTHROPIC_API_KEY, ACCESS_CODE (testçilere vereceğin kod), DAILY_LIMIT (kişi başı günlük fiş okuma, varsayılan 30), MODEL (varsayılan claude-sonnet-5-5), DATA_DIR (kalıcı disk yolu).
## Notlar
- Testçi ilk açılışta ad ve erişim kodunu girer. Veriler ada göre data/ klasöründe JSON dosyası olarak tutulur (test için yeterli, gerçek ürün için PostgreSQL'e geçilmeli).
- Ücretsiz planlarda disk silinebilir; kalıcı disk bağla.
- Fişlerde kişisel veri olabilir: testçilere bilgi ver, ve gerçek ürün öncesi KVKK metni hazırla.

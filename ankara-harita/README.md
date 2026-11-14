# Ankara Gezi Haritası

Ankara'nın ünlü mekanlarını, AVM'lerini, okullarını ve camilerini haritada gösterir. Bir noktaya dokununca özet bilgi açılır.

## Google Maps ile kullanmak

1. Google Cloud Console'da bir proje açın ve **Maps JavaScript API**'yi etkinleştirin.
2. Bir API anahtarı oluşturun. Anahtarı yalnızca `hakanmazi.github.io` sitesine kısıtlayın.
3. `index.html` içindeki `const GOOGLE_KEY='';` satırına anahtarı yazın.

Anahtar boş kalırsa harita OpenStreetMap ile açılır.

## Anahtarsız: Google Haritam

1. https://www.google.com/mymaps adresinde yeni harita oluşturun.
2. "İçe aktar" deyip `ankara-mekanlar.kml` dosyasını seçin.
3. Harita telefondaki Google Maps uygulamasında da görünür (Kaydedilenler > Haritalar).

Bazı konumlar yaklaşıktır.

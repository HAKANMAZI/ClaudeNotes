# BotTwitter

## BIST 100 Takip Uygulaması

Seçilmiş 20 BIST 100 şirketini tek ekrandan takip etmek için bir web uygulaması.

### Neler var?

| Sekme | İçerik |
|---|---|
| 📊 Özet | 20 şirketin fiyatı, günlük değişimi, F/K, PD/DD, piyasa değeri ve 52 haftalık aralığı. Ayrıca her şirket için okunmamış bildirim ve son 30 gündeki ihale sayısı |
| 📰 KAP Haberleri | Tüm şirketlerin son KAP bildirimleri. Şirkete, kategoriye (finansal rapor, temettü, geri alım vb.) ve yenilere göre filtrelenebilir |
| 🏗️ İhaleler & Sözleşmeler | "Yeni İş İlişkisi", "İhale", "Sözleşme", "Sipariş" gibi bildirimler ve şirket bazında grafik |
| 🔍 Şirket Detayı | Fiyat grafiği (1 ay - 5 yıl), şirketin bildirimleri ve KAP'ta beklenen bildirimler (ör. bilanço tarihi) |

- Son ziyaretten beri gelen bildirimler 🆕 ile işaretlenir. **Tümünü okundu say** düğmesiyle işaretler temizlenir. Bu bilgi `data/seen_disclosures.json` dosyasında tutulur.
- Fiyatlar 15 dakikada, KAP bildirimleri 10 dakikada bir yenilenir. **Verileri yenile** düğmesi beklemeden yeniler.

### Kurulum ve çalıştırma

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Tarayıcıda `http://localhost:8501` açılır.

İnternet olmadan arayüzü sahte verilerle denemek için:

```bash
BIST_TAKIP_DEMO=1 streamlit run app.py
```

### Şirket listesini değiştirmek

Takip listesi `bist_takip/watchlist.py` dosyasındadır. Şirket ekleyip çıkarabilir, sırayı değiştirebilirsiniz.

### Testler

```bash
pytest
```

### Notlar

- Veriler [borsapy](https://github.com/saidsurucu/borsapy) kütüphanesiyle KAP ve borsa kaynaklarından çekilir ve gecikmeli olabilir.
- İhaleler KAP bildirim başlıklarına göre otomatik sınıflandırılır (`bist_takip/categories.py`). Ayrıntı için KAP linkini açın.
- Bu uygulama yatırım tavsiyesi değildir.

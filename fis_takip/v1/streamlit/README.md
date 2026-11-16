# Fiş Takip - Streamlit sürümü

`app.py` mevcut arayüzü (`index.html`) Streamlit içinde açar. Sunucu tarafı veri tutmaz:
- Kayıtlar tarayıcının IndexedDB'sinde saklanır (cihaza özel).
- Fiş okuma için tarayıcı doğrudan Anthropic API'sini çağırır; anahtar sağ alttaki ⚙️ ayarlarına girilir ve sadece o tarayıcıda durur.
- Taşımak için ⚙️ → Yedek al / Yedek yükle.

## Yayınlama (Streamlit Community Cloud)
1. Bu klasörü GitHub deposuna koy (ör. `ClaudeNotes/fis-takip/streamlit`).
2. share.streamlit.io → New app → depo seç → Main file path: `fis-takip/streamlit/app.py`.
3. Deploy. Sonra uygulamayı Chrome'da aç, ⚙️'den API anahtarını gir.

## Yerelde
```
pip install -r requirements.txt
streamlit run app.py
```

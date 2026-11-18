# Mp3-Mp4 Downloader — v1

YouTube ve diğer sitelerden videoları **MP4 (video)** veya **MP3 (ses)** olarak indiren Windows masaüstü uygulaması.

## Özellikler
- YouTube dahil yt-dlp'nin desteklediği bin sekiz yüzü aşkın site
- MP4 kalite seçimi: En iyi, 1080p, 720p, 480p, 360p
- MP3: 192 kbps
- İndirme klasörü seçimi (varsayılan: İndirilenler)
- İlerleme çubuğu ve durum bilgisi

## Gereksinimler
- Windows 10 / 11
- Python 3.9 veya üstü (kurulumda "Add Python to PATH" işaretli olmalı)
- `yt-dlp` kütüphanesi
- `ffmpeg` (MP3 dönüştürme ve MP4 birleştirme için)

## Kurulum ve Çalıştırma

### Kolay yol
1. Bu klasördeki `video_indirici.py` ve `baslat.bat` dosyalarını aynı klasöre indirin.
2. `baslat.bat` dosyasına çift tıklayın.
   - yt-dlp'yi kurar/günceller
   - ffmpeg'i winget ile kurar
   - Uygulamayı açar

### Elle kurulum
```bat
pip install -U yt-dlp
winget install -e --id Gyan.FFmpeg
python video_indirici.py
```

## Kullanım
1. **Video linki** kutusuna linki yapıştırın.
2. **Biçim** seçin: MP4 (video) veya MP3 (ses).
3. MP4 için **Kalite** seçin.
4. İsterseniz **Seç** ile indirme klasörünü değiştirin.
5. **İNDİR** butonuna basın.
6. "Tamamlandı ✔" yazısı çıkınca dosya klasördedir.

## Sorun Giderme
- **"pip install yt-dlp" uyarısı:** `pip install yt-dlp` komutunu çalıştırın.
- **MP3 hatası / ffmpeg bulunamadı:** ffmpeg'i kurun, ardından bilgisayarı yeniden başlatın.
- **YouTube indirmiyor:** `pip install -U yt-dlp` ile güncelleyin.

## Not
Telif hakkı olan içerikleri yalnızca izinli veya kişisel kullanım için indirin.

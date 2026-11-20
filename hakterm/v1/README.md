# HakTerm v1

MobaXterm benzeri, sade ve ücretsiz SSH + SFTP istemcisi (Python).

## Kurulum
```
pip install paramiko
python hakterm.py
```

## Tek dosya .exe yapmak (Windows)
```
pip install pyinstaller
pyinstaller --onefile --windowed --name HakTerm hakterm.py
```
Çıktı: `dist\HakTerm.exe`

## Özellikler
- Kayıtlı oturumlar (sol panel)
- Sekmeli SSH terminali
- Her sekmede SFTP dosya gezgini: yükle, indir, klasör aç, sil
- Hızlı bağlantı: Ctrl+N → `kullanici@sunucu:port`
- Şifre veya SSH anahtarı ile giriş

## Kısayollar
- Sağ tık: seçili metni kopyala, seçim yoksa yapıştır
- Ctrl+Shift+C / Ctrl+Shift+V: kopyala / yapıştır
- Ctrl+W veya orta tık: sekmeyi kapat

Oturumlar `~/.hakterm_sessions.json` dosyasında tutulur. Şifreler kaydedilmez.

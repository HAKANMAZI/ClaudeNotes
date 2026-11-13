# PyMeet

Python ile yazılmış basit, Zoom benzeri toplantı uygulaması.

## Özellikler
- 💬 Yazılı sohbet
- 🎤 Sesli konuşma (birden çok kişinin sesi karıştırılarak çalınır)
- 🖥 Ekran paylaşımı (son paylaşan devralır)
- 👥 Katılımcı listesi

## Kurulum
```bash
pip install -r requirements.txt
```
Linux'ta ses için: `sudo apt install libportaudio2 python3-tk`

## Çalıştırma
1. Sunucuyu başlat:
   ```bash
   python server.py --port 5050
   ```
2. Her katılımcı istemciyi açar:
   ```bash
   python client.py --host SUNUCU_IP --port 5050 --name Hasan
   ```

## İnternet üzerinden kullanım
Aynı ağda doğrudan çalışır. Farklı ağlar için sunucuyu bir VPS'e kur,
modemde 5050 portunu yönlendir ya da Tailscale gibi bir VPN kullan.

## Not
Trafik şifrelenmez. Güvenilir ağlarda kullan.

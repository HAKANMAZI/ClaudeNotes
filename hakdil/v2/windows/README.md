# HakDil v2 — Windows

Bu klasörde Windows için hazır derlenmiş dosyalar var.

## Dosyalar
| Dosya | Görevi |
|---|---|
| `hakc.exe` | HakDil derleyicisi |
| `hakrt.o` | Çalışma zamanı kütüphanesi (`hakc.exe` ile aynı klasörde durmalı) |

## Kurulum
1. **Bağlayıcıyı indirin:** [w64devkit](https://github.com/skeeto/w64devkit/releases) sayfasından `w64devkit-x64-....exe` dosyasını indirip açın (örnek: `C:\w64devkit`).
2. **PATH'e ekleyin:** `C:\w64devkit\bin` klasörünü Windows ortam değişkeni PATH'e ekleyin.
3. **HakDil'i yerleştirin:** `hakc.exe` ve `hakrt.o` dosyalarını bir klasöre koyun (örnek: `C:\hakdil`) ve bu klasörü de PATH'e ekleyin.
4. **Deneyin:** Yeni bir komut penceresi açın:
```
hakc --sürüm
```

## Kullanım
`merhaba.hak` adlı bir dosya oluşturun (UTF-8 kaydedin):
```
ad = girdi("Adın ne? ")
yazdır("Merhaba, " + ad + "!")
```
Derleyin ve çalıştırın:
```
hakc merhaba.hak
merhaba.exe
```
Ya da tek adımda:
```
hakc -r merhaba.hak
```
Oluşan `merhaba.exe` başka bilgisayarlarda da tek başına çalışır.

## Neden w64devkit gerekiyor?
`hakc.exe` programınızı işlemci komutlarına kendisi çevirir. w64devkit içindeki assembler ve bağlayıcı yalnızca bu komutları `.exe` dosyası olarak paketler.

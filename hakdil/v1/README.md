# HakDil v1

Python benzeri, Türkçe anahtar kelimeli programlama dili. İlk sürüm.

## Klasör içeriği
- `hakdil.py` — dilin yorumlayıcısı (tek dosya, ek kurulum gerekmez)
- `ornekler/` — hazır örnek programlar ([açıklamalar](ornekler/README.md))

## Çalıştırma
```
python hakdil.py ornek.hak   # dosya çalıştır
python hakdil.py             # etkileşimli mod
```

## Anahtar kelimeler
| HakDil | Python |
|---|---|
| eğer / yada / değilse | if / elif / else |
| iken | while |
| için x içinde liste | for x in liste |
| fonk | def |
| döndür, kır, devam, geç | return, break, continue, pass |
| ve, veya, değil | and, or, not |
| doğru, yanlış, boş | True, False, None |

## Hazır fonksiyonlar
yazdır, girdi, uzunluk, aralık, sayı, ondalık, metin, liste, tür, toplam, en_büyük, en_küçük, yuvarla, mutlak, sıralı

## Metotlar
- Liste: ekle, çıkar, sil, sırala, ters_çevir, genişlet, bul, say, araya_ekle, temizle
- Metin: büyük, küçük, böl, değiştir, kırp, birleştir, başlar, biter, bul, say
- Sözlük: anahtarlar, değerler, çiftler, al, sil, güncelle, temizle

## Örnek
```
fonk faktöriyel(n):
    eğer n <= 1:
        döndür 1
    döndür n * faktöriyel(n - 1)

yazdır("5! =", faktöriyel(5))
```

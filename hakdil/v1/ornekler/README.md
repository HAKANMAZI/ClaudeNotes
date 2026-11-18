# HakDil v1 — Örnekler

Bu klasörde HakDil ile yazılmış hazır programlar var.

## Çalıştırma
`v1` klasöründeyken:
```
python hakdil.py ornekler/tanitim.hak
```

## Dosyalar
| Dosya | Ne yapar? | Gösterdiği özellikler |
|---|---|---|
| `tanitim.hak` | Dilin genel tanıtımı | Değişken, koşul, fonksiyon, liste, sözlük, döngü |
| `hesap_makinesi.hak` | İki sayıyla dört işlem | `girdi`, `ondalık`, `eğer/yada`, `döndür` |
| `sayi_tahmin.hak` | Sayı tahmin oyunu | `iken doğru`, `kır`, `+=` |
| `not_ortalamasi.hak` | Notlardan ortalama ve geçti/kaldı | Sözlük, `toplam`, `uzunluk`, `yuvarla` |
| `fibonacci.hak` | Fibonacci dizisi | Özyineleme, `aralık`, `liste.ekle` |

## Örnek çıktı (fibonacci.hak)
```
İlk on terim: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
Otuzuncu terim: 832040
```

## Kendi programını yaz
1. `.hak` uzantılı bir dosya oluştur (UTF-8 kaydet).
2. Bloklar `:` ile başlar, içi dört boşlukla girintilenir.
3. `python hakdil.py dosyan.hak` ile çalıştır.

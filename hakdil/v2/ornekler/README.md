# HakDil v2 — Örnekler

v1 örnekleri v2'de değiştirilmeden çalışır. Ek olarak bir hız testi var.

## Çalıştırma
```
hakc -r tanitim.hak
```
Ya da önce `.exe` üretip sonra çalıştırın:
```
hakc fibonacci.hak
fibonacci.exe
```

## Dosyalar
| Dosya | Ne yapar? | Gösterdiği özellikler |
|---|---|---|
| `tanitim.hak` | Dilin genel tanıtımı | Değişken, koşul, fonksiyon, liste, sözlük, döngü |
| `hesap_makinesi.hak` | İki sayıyla dört işlem | `girdi`, `ondalık`, `eğer/yada`, `döndür` |
| `sayi_tahmin.hak` | Sayı tahmin oyunu | `iken doğru`, `kır`, `+=` |
| `not_ortalamasi.hak` | Notlardan ortalama ve geçti/kaldı | Sözlük, `toplam`, `uzunluk`, `yuvarla` |
| `fibonacci.hak` | Fibonacci dizisi | Özyineleme, `aralık`, `liste.ekle` |
| `hiz_testi.hak` | Hız ölçümü | Özyineleme ve elli milyon turluk döngü |

## Hız testi sonucu
Aynı program, aynı bilgisayarda:
| | Süre |
|---|---|
| Python 3 | dört saniye |
| HakDil v2 | üç saniyenin onda biri |

Çıktı:
```
fib(32) = 2178309
döngü toplamı: 149999997
```

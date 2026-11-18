# HakDil

Hasan'a ait, Türkçe anahtar kelimeli, Python gibi kolay yazılan programlama dili.

## Sürümler
| Klasör | Açıklama |
|---|---|
| [v2](v2/) | **Güncel.** Makine koduna derlenir, tek başına çalışan `.exe` üretir, Python gerekmez |
| [v1](v1/) | İlk sürüm: Python ile yazılmış yorumlayıcı |

## Hızlı başlangıç (v2)
Windows: [v2/windows](v2/windows/) klasöründeki kurulum adımlarını izleyin. Ardından:
```
hakc -r program.hak
```

## Kısa örnek
```
isim = girdi("Adın ne? ")
eğer isim == "Hasan":
    yazdır("Hoş geldin, dilin sahibi!")
değilse:
    yazdır("Merhaba, " + isim)

için i içinde aralık(1, 4):
    yazdır(i, "x", i, "=", i * i)
```

Ayrıntılı rehber: [v2/README.md](v2/README.md) · Örnekler: [v2/ornekler](v2/ornekler/)

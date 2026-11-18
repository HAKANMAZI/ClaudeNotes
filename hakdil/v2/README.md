# HakDil v2 — Makine koduna derlenen sürüm

v2, HakDil'in **gerçek derleyicisidir**. Python'a ihtiyaç duymaz.
Programınızı doğrudan x86-64 işlemci komutlarına çevirir ve tek bir `.exe` üretir.

## v1 ile farkı
| | v1 | v2 |
|---|---|---|
| Nasıl çalışır? | Python içinde yorumlanır | Makine koduna derlenir |
| Python gerekir mi? | Evet | Hayır |
| Çıktı | Yok, her seferinde yorumlanır | Tek başına çalışan `.exe` |
| Hız | Python'dan yavaş | Python'dan yaklaşık on üç kat hızlı |
| Yazılış | Aynı | Aynı (girintili, Türkçe) |

## Nasıl çalışır?
```
program.hak  →  sözcük çözümleyici  →  sözdizimi ağacı  →  x86-64 assembly  →  program.exe
```
- `hakc` (derleyici) her şeyi kendisi yapar: kodu okur, çözümler ve işlemci komutlarını üretir.
- Son adımda sistemdeki assembler ve bağlayıcı, bu komutları `.exe` dosyasına paketler.
- `hakrt` (çalışma zamanı) metin, liste, sözlük ve yazdır gibi hazır işleri yapan küçük bir kütüphanedir.

## Hızlı başlangıç
**Windows:** [windows](windows/) klasöründeki adımları izleyin.

**Linux / macOS:**
```
cd kaynak
./derle.sh
./hakc -r ../ornekler/tanitim.hak
```

## Komutlar
| Komut | Ne yapar? |
|---|---|
| `hakc program.hak` | `program.exe` üretir |
| `hakc program.hak -o ad` | Çıktı adını belirler |
| `hakc -r program.hak` | Derler ve hemen çalıştırır |
| `hakc -S program.hak` | Yalnızca assembly kodunu (`.s`) gösterir |
| `hakc --sürüm` | Sürümü yazar |

## Dil rehberi
### Anahtar kelimeler
| HakDil | Anlamı |
|---|---|
| `eğer` / `yada` / `değilse` | koşul |
| `iken` | koşul doğru oldukça tekrarla |
| `için x içinde liste` | listedeki her öğe için |
| `fonk` | fonksiyon tanımla |
| `döndür`, `kır`, `devam`, `geç` | değer döndür, döngüden çık, sonraki tura geç, hiçbir şey yapma |
| `ve`, `veya`, `değil` | mantık işlemleri |
| `doğru`, `yanlış`, `boş` | sabit değerler |

### Veri türleri
`tam_sayı` (5), `ondalık` (2.5), `metin` ("merhaba"), `liste` ([1, 2]), `sözlük` ({"a": 1}), `mantıksal` (doğru), `boş`

### Hazır fonksiyonlar
`yazdır`, `girdi`, `uzunluk`, `aralık`, `sayı`, `ondalık`, `metin`, `liste`, `tür`, `toplam`, `en_büyük`, `en_küçük`, `yuvarla`, `mutlak`, `sıralı`

### Metotlar
- **Liste:** `ekle`, `çıkar`, `sil`, `sırala`, `ters_çevir`, `genişlet`, `bul`, `say`, `araya_ekle`, `temizle`
- **Metin:** `büyük`, `küçük`, `böl`, `değiştir`, `kırp`, `birleştir`, `başlar`, `biter`, `bul`, `say`
- **Sözlük:** `anahtarlar`, `değerler`, `çiftler`, `al`, `sil`, `güncelle`, `temizle`

`büyük` ve `küçük` Türkçe kurallarına uyar: `"istanbul".büyük()` → `İSTANBUL`

## Kullanım örnekleri
```
fonk faktöriyel(n):
    eğer n <= 1:
        döndür 1
    döndür n * faktöriyel(n - 1)

yazdır("10! =", faktöriyel(10))

şehirler = ["kerkük", "istanbul", "ankara"]
için ş içinde sıralı(şehirler):
    yazdır(ş.büyük())

stok = {"elma": 5}
stok["armut"] = 3
stok["elma"] += 2
yazdır(stok)
```
Çıktı:
```
10! = 3628800
ANKARA
İSTANBUL
KERKÜK
{"elma": 7, "armut": 3}
```

## Hata mesajları
Derleme sırasında:
```
Derleme hatası (satır 3): Tanımsız isim: 'y'
```
Çalışırken:
```
Hata (satır 5): Sıfıra bölme yapılamaz
```

## Bu sürümün sınırları
- Tam sayılar altmış üç bitliktir; taşarsa ondalığa dönüşür.
- Fonksiyonlar yalnızca en dış seviyede tanımlanır ve değer olarak aktarılamaz.
- Bellek temizleyici (çöp toplayıcı) yoktur; çok uzun süre çalışan programlarda bellek büyüyebilir.
- Yalnızca 64 bit x86 işlemcilerde (Intel/AMD) çalışır.

## Klasörler
- [kaynak](kaynak/) — derleyici ve çalışma zamanının kaynak kodu
- [windows](windows/) — Windows için hazır derleyici
- [ornekler](ornekler/) — örnek programlar

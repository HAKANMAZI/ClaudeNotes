# HakDil v2 — Kaynak kod

## Dosyalar
| Dosya | Görevi |
|---|---|
| `hakc.c` | Derleyici: kodu okur, çözümler, x86-64 assembly üretir, `.exe` oluşturur |
| `hakrt.c` | Çalışma zamanı: metin, liste, sözlük, yazdır gibi hazır işler |
| `derle.sh` | Linux/macOS'ta derleyiciyi kurar |
| `derle.bat` | Windows'ta derleyiciyi kurar |

## Derleyicinin bölümleri (`hakc.c`)
1. **Sözcük çözümleyici:** Metni sözcüklere ayırır, girintileri blok olarak tanır.
2. **Ayrıştırıcı:** Sözcüklerden sözdizimi ağacı kurar.
3. **Anlam çözümleme:** Değişkenlerin yerel mi genel mi olduğunu bulur, tanımsız isimleri yakalar.
4. **Kod üretici:** Ağacı x86-64 komutlarına çevirir. Tam sayı işlemleri doğrudan işlemcide yapılır.
5. **Sürücü:** Assembler ve bağlayıcıyı çağırıp `.exe` dosyasını üretir.

## Değer gösterimi
Her değer altmış dört bitlik tek bir sayıdır:
- Son biti `1` ise tam sayıdır (kutusuz, çok hızlı).
- `0` boş, `2` yanlış, `4` doğrudur.
- Diğerleri bellekteki bir nesneyi gösterir (ondalık, metin, liste, sözlük).

## Kurma
Linux / macOS:
```
./derle.sh
./hakc -r ../ornekler/tanitim.hak
```
Windows (w64devkit veya MinGW-w64 kurulu olmalı):
```
derle.bat
hakc -r ..\ornekler\tanitim.hak
```

## Assembly çıktısını görmek
```
./hakc -S ../ornekler/fibonacci.hak
```
Örnek: `a + b` için üretilen hızlı yol
```
	mov rax, r10
	and rax, r11
	test al, 1          ; ikisi de tam sayı mı?
	jz .L5              ; değilse yavaş yola git
	lea rax, [r10-1]
	add rax, r11        ; işlemcide doğrudan topla
	jo .L5              ; taşma varsa yavaş yola git
```

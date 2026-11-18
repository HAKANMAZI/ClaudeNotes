# storage — Depolama katmanı

Veriyi diske yazar, okur ve çökmeye karşı korur.
SQL Server'daki "storage engine" katmanının karşılığıdır.

| Dosya | Görev |
|---|---|
| `row.py` | Satırı bayt dizisine çevirir ve geri okur |
| `page.py` | 4096 baytlık slotted page yapısı |
| `pager.py` | Sayfa önbelleği, commit, rollback, journal ile kurtarma |
| `table.py` | Heap tablo, ekleme, silme, tarama ve primary key indeksi |

## Disk düzeni

Her tablo için bir `.tbl` dosyası oluşur. Dosya sayfalardan oluşur.

```
Sayfa (4096 bayt)
┌──────────────┬───────────────────┬──────────── boş ────────────┬──────────────┐
│ Başlık (4 B) │ Slot dizisi →     │                             │ ← Satırlar   │
│ slot, boşluk │ (offset, uzunluk) │                             │              │
└──────────────┴───────────────────┴─────────────────────────────┴──────────────┘
```

- Slot dizisi baştan sona, satırlar sondan başa doğru büyür.
- Silinen satırın slot uzunluğu sıfır yapılır.

Satır biçimi (her kolon için):

| Tip baytı | Anlamı | Ardından gelen |
|---|---|---|
| 0 | NULL | — |
| 1 | INT | 8 bayt tam sayı |
| 2 | REAL | 8 bayt ondalık sayı |
| 3 | TEXT | 2 bayt uzunluk + UTF-8 metin |

## Çökme kurtarma (journal)

Commit sırası:
1. Değişecek sayfaların eski hâli `.tbl-journal` dosyasına yazılır.
2. Yeni sayfalar `.tbl` dosyasına yazılır.
3. Journal silinir.

Açılışta journal varsa eski sayfalar geri yüklenir. Böylece yarım kalan işlem iz bırakmaz.

## Kullanım örnekleri

### Satır kodlama

```python
from hakengine.storage.row import encode_row, decode_row

veri = encode_row([1, "Elma", 12.5, None])
print(decode_row(veri))   # [1, 'Elma', 12.5, None]
```

### Sayfa

```python
from hakengine.storage.page import Page
from hakengine.storage.row import encode_row

sayfa = Page()
slot = sayfa.insert(encode_row([1, "Elma"]))
print(list(sayfa.slots()))     # [(0, b'...')]
print(sayfa.free_space())      # kalan boş bayt
sayfa.delete(slot)
```

### Pager

```python
from hakengine.storage.pager import Pager

p = Pager("deneme.tbl")
no = p.new_page()
p.get(no).insert(b"\x01" + (5).to_bytes(8, "little"))
p.commit()     # diske yazar
p.close()
```

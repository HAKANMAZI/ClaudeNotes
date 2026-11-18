# storage — Depolama katmanı

Veriyi diske yazar, okur ve çökmeye karşı korur. SQL Server'daki "storage engine" karşılığıdır.

| Dosya | Görev |
|---|---|
| `row.py` | Satırı bayt dizisine çevirir ve geri okur |
| `page.py` | 4096 baytlık slotted page. Slot yeniden kullanımı ve sıkıştırma |
| `pager.py` | Buffer pool, dirty sayfalar, statement savepoint |
| `journal.py` | Birden çok dosyaya atomik commit, çökme kurtarma |
| `btree.py` | Diskte B+ ağacı indeksi |
| `table.py` | Heap tablo, tip dönüşümü, kısıtlar, indeks bakımı |

## Disk düzeni

```
veritabanim/
├── catalog.json              şema
├── musteri.tbl               tablo verisi
├── musteri__PK_musteri.idx   primary key indeksi
├── musteri__IX_sehir.idx     ek indeks
├── hakengine.lock            kilit
└── hakengine.journal         sadece commit sırasında
```

### Tablo sayfası

```
┌──────────────┬────────────────────┬──────── boş ────────┬──────────────┐
│ Başlık (4 B) │ Slotlar →          │                     │ ← Satırlar   │
└──────────────┴────────────────────┴─────────────────────┴──────────────┘
```

Satır adresi `rid = (sayfa_no, slot_no)`. Silinen slot yeniden kullanılır. Sıkıştırmada slot numarası değişmez, bu yüzden indeksler bozulmaz.

### B+ ağacı

```
            [sayfa 0: meta → kök]
                     │
               [ iç düğüm ]              anahtar: (değer, sayfa_no, slot_no)
              /     |      \
      [yaprak] → [yaprak] → [yaprak]     yapraklar zincirle bağlı (aralık taraması)
```

Yirmi bin satırda ağaç derinliği üçtür. Bir arama en fazla üç sayfa okur.

## Commit ve kurtarma

```
1. Eski sayfalar → hakengine.journal  (sonunda HEND işareti, fsync)
2. Yeni sayfalar → .tbl ve .idx dosyaları (fsync)
3. Journal silinir  ← commit burada tamamlanır
```

| Çökme anı | Açılışta ne olur |
|---|---|
| 1. adım sırasında | Journal'da HEND yok, silinir. Veri dosyalarına dokunulmamıştı. |
| 2. adım sırasında | Journal geri yazılır. Tüm dosyalar commit öncesine döner. |
| 3. adımdan sonra | Journal yok. Commit tamamdır. |

## Kullanım örnekleri

### B+ ağacı

```python
from hakengine.storage import Pager, BTree, journal

p = Pager("deneme.idx")
t = BTree(p)
for i in range(1000):
    t.insert(i % 100, (i, 0))          # değer, satır adresi

print(list(t.seek(42))[:3])            # [(42, 0), (142, 0), (242, 0)]
print(sum(1 for _ in t.range(10, 20))) # 110
print(t.height())                      # 2

journal.commit(".", "deneme.journal", [p])
p.close()
```

### Sayfa

```python
from hakengine.storage import Page
from hakengine.storage.row import encode_row, decode_row

s = Page()
a = s.insert(encode_row([1, "Elma", 12.5]))
b = s.insert(encode_row([2, "Çay", None]))
s.delete(a)
c = s.insert(encode_row([3, "Süt", 30.0]))   # silinen slot yeniden kullanılır
print(a == c)                                # True
print(decode_row(s.get(b)))                  # [2, 'Çay', None]
```

### Savepoint

```python
p.begin_statement()
p.write(0).data[100] = 7      # değişiklik
p.rollback_statement()        # sadece bu komutun değişikliği geri alınır
p.end_statement()
```

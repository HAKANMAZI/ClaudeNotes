"""Journal: birden çok dosyaya atomik commit ve çökme kurtarma.

Bir commit tablo dosyasını ve indeks dosyalarını birlikte değiştirir.
Hepsi ya birlikte yazılmalı ya hiç yazılmamalı.

Commit sırası:
  1. Değişecek sayfaların ESKİ hâli tek bir journal dosyasına yazılır.
     Dosya HEND işaretiyle biter ve diske zorla yazılır (fsync).
  2. Yeni sayfalar veri dosyalarına yazılır.
  3. Journal silinir. Commit burada tamamlanmış olur.

Açılışta journal varsa:
  - HEND işareti yoksa: çökme 1. adımda oldu, veri dosyalarına dokunulmadı.
    Journal silinir.
  - HEND varsa: çökme 2. adımda oldu. Eski sayfalar geri yazılır.
"""
import os, struct
from .page import PAGE_SIZE

MAGIC, END = b"HAKJ", b"HEND"


def commit(dirpath, jname, pagers):
    pagers = [p for p in pagers if p.dirty]
    if not pagers:
        return
    jpath = os.path.join(dirpath, jname)
    with open(jpath, "wb") as j:
        j.write(MAGIC + struct.pack("<I", len(pagers)))
        for p in pagers:
            imgs = p.original_images()
            name = os.path.basename(p.path).encode("utf-8")
            j.write(struct.pack("<H", len(name)) + name + struct.pack("<II", p.disk_pages, len(imgs)))
            for pno, data in imgs:
                j.write(struct.pack("<I", pno) + data)
        j.write(END)
        j.flush()
        os.fsync(j.fileno())
    for p in pagers:
        p.flush()
    os.remove(jpath)
    for p in pagers:
        p.committed()


def recover(dirpath, jname):
    jpath = os.path.join(dirpath, jname)
    if not os.path.exists(jpath):
        return False
    with open(jpath, "rb") as jf:
        data = jf.read()
    if not (data.startswith(MAGIC) and data.endswith(END)):
        os.remove(jpath)
        return False
    pos = 4
    count = struct.unpack_from("<I", data, pos)[0]; pos += 4
    for _ in range(count):
        ln = struct.unpack_from("<H", data, pos)[0]; pos += 2
        name = data[pos:pos + ln].decode("utf-8"); pos += ln
        orig, n = struct.unpack_from("<II", data, pos); pos += 8
        pages = []
        for _ in range(n):
            pno = struct.unpack_from("<I", data, pos)[0]; pos += 4
            pages.append((pno, data[pos:pos + PAGE_SIZE])); pos += PAGE_SIZE
        fpath = os.path.join(dirpath, name)
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r+b") as f:
            for pno, img in pages:
                f.seek(pno * PAGE_SIZE)
                f.write(img)
            f.truncate(orig * PAGE_SIZE)
            f.flush()
            os.fsync(f.fileno())
    os.remove(jpath)
    return True

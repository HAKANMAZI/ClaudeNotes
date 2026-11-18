"""Pager: sayfa önbelleği, commit/rollback ve journal ile kurtarma."""
import os, struct
from .page import Page, PAGE_SIZE

class Pager:
    """Sayfa önbelleği. Değişiklikler commit'e kadar bellekte kalır.
    Commit sırasında önce eski sayfalar journal dosyasına yazılır (rollback journal),
    sonra veri dosyası güncellenir. Çökme olursa açılışta journal geri yüklenir."""

    def __init__(self, path):
        self.path = path
        self.jpath = path + "-journal"
        if not os.path.exists(path):
            open(path, "wb").close()
        self.recover()
        self.f = open(path, "r+b")
        self.cache, self.dirty = {}, set()
        self.disk_pages = os.path.getsize(path) // PAGE_SIZE
        self.num_pages = self.disk_pages

    def recover(self):
        if not os.path.exists(self.jpath):
            return
        with open(self.jpath, "rb") as j, open(self.path, "r+b") as f:
            orig_pages = struct.unpack("<I", j.read(4))[0]
            while True:
                h = j.read(4)
                if len(h) < 4:
                    break
                pno = struct.unpack("<I", h)[0]
                data = j.read(PAGE_SIZE)
                if len(data) < PAGE_SIZE:
                    break
                f.seek(pno * PAGE_SIZE); f.write(data)
            f.truncate(orig_pages * PAGE_SIZE)
            f.flush(); os.fsync(f.fileno())
        os.remove(self.jpath)

    def get(self, pno):
        if pno not in self.cache:
            self.f.seek(pno * PAGE_SIZE)
            self.cache[pno] = Page(self.f.read(PAGE_SIZE))
        return self.cache[pno]

    def new_page(self):
        pno = self.num_pages
        self.num_pages += 1
        self.cache[pno] = Page()
        self.dirty.add(pno)
        return pno

    def mark(self, pno):
        self.dirty.add(pno)

    def commit(self):
        if not self.dirty:
            return
        with open(self.jpath, "wb") as j:
            j.write(struct.pack("<I", self.disk_pages))
            for pno in sorted(self.dirty):
                if pno < self.disk_pages:
                    self.f.seek(pno * PAGE_SIZE)
                    j.write(struct.pack("<I", pno) + self.f.read(PAGE_SIZE))
            j.flush(); os.fsync(j.fileno())
        for pno in sorted(self.dirty):
            self.f.seek(pno * PAGE_SIZE)
            self.f.write(self.cache[pno].data)
        self.f.flush(); os.fsync(self.f.fileno())
        os.remove(self.jpath)
        self.disk_pages = self.num_pages
        self.dirty.clear()

    def rollback(self):
        for pno in self.dirty:
            self.cache.pop(pno, None)
        self.dirty.clear()
        self.num_pages = self.disk_pages

    def close(self):
        self.f.close()



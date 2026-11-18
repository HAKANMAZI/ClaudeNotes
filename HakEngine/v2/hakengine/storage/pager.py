"""Pager: sayfa önbelleği (buffer pool) ve statement savepoint.

- Okunan sayfalar bellekte tutulur. Önbellek dolunca temiz sayfalar atılır.
- Değişen sayfalar commit'e kadar bellekte kalır (dirty).
- Transaction içinde her komut öncesi bir savepoint açılır. Komut hata verirse
  sadece o komutun değişiklikleri geri alınır (SQL Server'daki gibi).
- Diske yazma ve çökme kurtarma işini Journal yönetir (journal.py).
"""
import os
from .page import Page, PAGE_SIZE

CACHE_LIMIT = 4000      # yaklaşık 16 MB


class Pager:
    def __init__(self, path):
        self.path = path
        if not os.path.exists(path):
            open(path, "wb").close()
        self.f = open(path, "r+b")
        self.disk_pages = os.path.getsize(path) // PAGE_SIZE
        self.num_pages = self.disk_pages
        self.cache, self.dirty = {}, set()
        self.undo, self.undo_np = None, 0

    # ---- okuma / yazma
    def get(self, pno):
        p = self.cache.get(pno)
        if p is None:
            if len(self.cache) >= CACHE_LIMIT:
                self._evict()
            self.f.seek(pno * PAGE_SIZE)
            p = Page(self.f.read(PAGE_SIZE))
            self.cache[pno] = p
        return p

    def write(self, pno):
        """Değiştirilecek sayfayı döndürür. Değişiklikten ÖNCE çağrılmalı."""
        p = self.get(pno)
        if self.undo is not None and pno not in self.undo:
            self.undo[pno] = bytes(p.data) if pno in self.dirty else None
        self.dirty.add(pno)
        return p

    def new_page(self):
        pno = self.num_pages
        self.num_pages += 1
        self.cache[pno] = Page()
        self.dirty.add(pno)
        if self.undo is not None:
            self.undo[pno] = "new"
        return pno

    def _evict(self):
        for pno in list(self.cache):
            if pno not in self.dirty:
                del self.cache[pno]
                if len(self.cache) < CACHE_LIMIT // 2:
                    break

    # ---- statement savepoint
    def begin_statement(self):
        self.undo, self.undo_np = {}, self.num_pages

    def end_statement(self):
        self.undo = None

    def rollback_statement(self):
        if self.undo is None:
            return
        for pno, img in self.undo.items():
            if img is None or img == "new":
                self.cache.pop(pno, None)
                self.dirty.discard(pno)
            else:
                self.cache[pno] = Page(img)
        self.num_pages = self.undo_np
        self.undo = {}

    # ---- commit (Journal tarafından çağrılır)
    def original_images(self):
        out = []
        for pno in sorted(self.dirty):
            if pno < self.disk_pages:
                self.f.seek(pno * PAGE_SIZE)
                out.append((pno, self.f.read(PAGE_SIZE)))
        return out

    def flush(self):
        for pno in sorted(self.dirty):
            self.f.seek(pno * PAGE_SIZE)
            self.f.write(self.cache[pno].data)
        self.f.flush()
        os.fsync(self.f.fileno())

    def committed(self):
        self.disk_pages = self.num_pages
        self.dirty.clear()

    def rollback(self):
        for pno in self.dirty:
            self.cache.pop(pno, None)
        self.dirty.clear()
        self.num_pages = self.disk_pages
        if self.undo is not None:
            self.undo = {}

    def reload(self):
        """Disk durumunu yeniden okur (başarısız commit sonrası kurtarmada)."""
        self.cache.clear()
        self.dirty.clear()
        self.disk_pages = self.num_pages = os.path.getsize(self.path) // PAGE_SIZE
        if self.undo is not None:
            self.undo = {}

    def close(self):
        self.f.close()

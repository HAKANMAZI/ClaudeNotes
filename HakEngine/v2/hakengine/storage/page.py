"""Slotted page: 4096 baytlık sayfa yapısı.

v2 yenilikleri:
  - Silinen satırın slotu yeniden kullanılır.
  - Sayfa parçalanınca sıkıştırılır (compact). Slot numaraları değişmez,
    bu yüzden indekslerdeki satır adresleri (rid) geçerli kalır.
"""
import struct

PAGE_SIZE = 4096
HDR = struct.Struct("<HH")      # slot sayısı, boş alan başlangıcı
SLOT = struct.Struct("<HH")     # satır offset, satır uzunluğu (0 = silinmiş)


class Page:
    __slots__ = ("data",)

    def __init__(self, data=None):
        if data:
            self.data = bytearray(data)
        else:
            self.data = bytearray(PAGE_SIZE)
            HDR.pack_into(self.data, 0, 0, PAGE_SIZE)

    def header(self):
        return HDR.unpack_from(self.data, 0)

    def _slot(self, s):
        return SLOT.unpack_from(self.data, HDR.size + s * SLOT.size)

    def _set_slot(self, s, off, ln):
        SLOT.pack_into(self.data, HDR.size + s * SLOT.size, off, ln)

    def slots(self):
        n, _ = self.header()
        for s in range(n):
            off, ln = self._slot(s)
            if ln:
                yield s, bytes(self.data[off:off + ln])

    def get(self, s):
        n, _ = self.header()
        if s >= n:
            return None
        off, ln = self._slot(s)
        return bytes(self.data[off:off + ln]) if ln else None

    def live_count(self):
        n, _ = self.header()
        return sum(1 for s in range(n) if self._slot(s)[1])

    def _live_bytes(self):
        n, _ = self.header()
        return sum(self._slot(s)[1] for s in range(n))

    def _free_slot(self):
        n, _ = self.header()
        for s in range(n):
            if self._slot(s)[1] == 0:
                return s
        return None

    def total_free(self):
        n, _ = self.header()
        return PAGE_SIZE - HDR.size - n * SLOT.size - self._live_bytes()

    def can_fit(self, rec):
        need = len(rec) + (0 if self._free_slot() is not None else SLOT.size)
        return need <= self.total_free()

    def insert(self, rec):
        if not self.can_fit(rec):
            return None
        s = self._free_slot()
        n, free = self.header()
        slot_end = HDR.size + (n if s is not None else n + 1) * SLOT.size
        if free - len(rec) < slot_end:
            self.compact()
            n, free = self.header()
        off = free - len(rec)
        self.data[off:free] = rec
        if s is None:
            s, n = n, n + 1
        self._set_slot(s, off, len(rec))
        HDR.pack_into(self.data, 0, n, off)
        return s

    def delete(self, s):
        self._set_slot(s, 0, 0)

    def compact(self):
        n, _ = self.header()
        live = list(self.slots())
        end = PAGE_SIZE
        for s, rec in live:
            end -= len(rec)
            self.data[end:end + len(rec)] = rec
            self._set_slot(s, end, len(rec))
        HDR.pack_into(self.data, 0, n, end)

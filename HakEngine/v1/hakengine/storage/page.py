"""Slotted page: 4096 baytlık sayfa yapısı."""
import struct

PAGE_SIZE = 4096
HDR = struct.Struct("<HH")      # slot sayısı, boş alan başlangıcı
SLOT = struct.Struct("<HH")     # satır offset, satır uzunluğu (0 = silinmiş)

class Page:
    def __init__(self, data=None):
        self.data = bytearray(data) if data else bytearray(PAGE_SIZE)
        if not data:
            HDR.pack_into(self.data, 0, 0, PAGE_SIZE)

    def header(self):
        return HDR.unpack_from(self.data, 0)

    def slots(self):
        n, _ = self.header()
        for s in range(n):
            off, ln = SLOT.unpack_from(self.data, HDR.size + s * SLOT.size)
            if ln:
                yield s, bytes(self.data[off:off + ln])

    def free_space(self):
        n, free = self.header()
        return free - (HDR.size + (n + 1) * SLOT.size)

    def insert(self, rec):
        if len(rec) > self.free_space():
            return None
        n, free = self.header()
        off = free - len(rec)
        self.data[off:free] = rec
        SLOT.pack_into(self.data, HDR.size + n * SLOT.size, off, len(rec))
        HDR.pack_into(self.data, 0, n + 1, off)
        return n

    def delete(self, slot):
        pos = HDR.size + slot * SLOT.size
        off, _ = SLOT.unpack_from(self.data, pos)
        SLOT.pack_into(self.data, pos, off, 0)



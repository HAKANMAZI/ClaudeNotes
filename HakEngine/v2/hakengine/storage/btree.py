"""Diskte B+ ağacı indeksi.

- Her düğüm bir sayfadır (4096 bayt). Sayfa 0 meta sayfasıdır, kök sayfa numarasını tutar.
- Anahtar: (değer, sayfa_no, slot_no). Satır adresi anahtara eklendiği için
  aynı değerden birden çok satır olabilir (non-unique index).
- Yaprak düğümler birbirine bağlıdır. Aralık taraması (range scan) bu bağla yapılır.
- Silmede düğüm birleştirme yapılmaz. Boş yapraklar zincirde kalır. Basitlik için.
"""
import bisect, struct
from ..errors import DBError
from .page import PAGE_SIZE
from .row import encode_row, decode_row

NODE = struct.Struct("<BHI")    # yaprak mı, anahtar sayısı, (yaprak: sonraki yaprak | iç: ilk çocuk)
U16, U32 = struct.Struct("<H"), struct.Struct("<I")
NIL = 0xFFFFFFFF
MAX_KEY = 1000
CACHE_LIMIT = 5000
BEFORE_ALL = ((-1, 0), -1, -1)
AFTER_NULLS = ((0, 1), -1, -1)


def sort_key(v):
    if v is None:
        return (0, 0)
    if isinstance(v, str):
        return (2, v)
    return (1, v)


def ckey(k):
    return (sort_key(k[0]), k[1], k[2])


class Node:
    __slots__ = ("leaf", "keys", "ck", "ptrs", "next")

    def __init__(self, leaf, keys=None, ptrs=None, nxt=NIL):
        self.leaf = leaf
        self.keys = keys or []
        self.ck = [ckey(k) for k in self.keys]
        self.ptrs = ptrs or []
        self.next = nxt


class BTree:
    def __init__(self, pager):
        self.pager = pager
        self.cache = {}
        if pager.num_pages == 0:
            pager.new_page()                    # 0: meta
            root = pager.new_page()             # 1: boş kök yaprak
            self._put(root, Node(True))
            self._set_root(root)

    def reset_cache(self):
        self.cache.clear()

    # ---- sayfa <-> düğüm
    def root(self):
        return U32.unpack_from(self.pager.get(0).data, 0)[0]

    def _set_root(self, pno):
        U32.pack_into(self.pager.write(0).data, 0, pno)

    def node(self, pno):
        n = self.cache.get(pno)
        if n is None:
            if len(self.cache) >= CACHE_LIMIT:
                self.cache.clear()
            n = self._decode(self.pager.get(pno).data)
            self.cache[pno] = n
        return n

    @staticmethod
    def _decode(d):
        leaf, cnt, p = NODE.unpack_from(d, 0)
        pos, keys, ptrs = NODE.size, [], []
        if not leaf:
            ptrs.append(p)
        for _ in range(cnt):
            ln = U16.unpack_from(d, pos)[0]; pos += 2
            keys.append(tuple(decode_row(bytes(d[pos:pos + ln])))); pos += ln
            if not leaf:
                ptrs.append(U32.unpack_from(d, pos)[0]); pos += 4
        return Node(bool(leaf), keys, ptrs, p if leaf else NIL)

    @staticmethod
    def _encode(n):
        out = bytearray(NODE.pack(1 if n.leaf else 0, len(n.keys), n.next if n.leaf else n.ptrs[0]))
        for i, k in enumerate(n.keys):
            b = encode_row(list(k))
            out += U16.pack(len(b)) + b
            if not n.leaf:
                out += U32.pack(n.ptrs[i + 1])
        return out

    def _put(self, pno, n, check=False):
        b = self._encode(n)
        if len(b) > PAGE_SIZE:
            if check:
                return False
            raise DBError("B-ağacı düğümü sayfaya sığmadı")
        self.pager.write(pno).data[:len(b)] = b
        self.cache[pno] = n
        return True

    # ---- ekleme
    def insert(self, value, rid):
        key = (value, rid[0], rid[1])
        if len(encode_row(list(key))) > MAX_KEY:
            raise DBError("İndeks anahtarı çok uzun")
        root = self.root()
        res = self._ins(root, key, ckey(key))
        if res:
            sep, right = res
            nr = self.pager.new_page()
            self._put(nr, Node(False, [sep], [root, right]))
            self._set_root(nr)

    def _ins(self, pno, key, c):
        n = self.node(pno)
        if n.leaf:
            i = bisect.bisect_left(n.ck, c)
            n.keys.insert(i, key); n.ck.insert(i, c)
            if self._put(pno, n, check=True):
                return None
            mid = len(n.keys) // 2
            rp = self.pager.new_page()
            right = Node(True, n.keys[mid:], None, n.next)
            n.keys, n.ck, n.next = n.keys[:mid], n.ck[:mid], rp
            self._put(rp, right); self._put(pno, n)
            return right.keys[0], rp
        i = bisect.bisect_right(n.ck, c)
        res = self._ins(n.ptrs[i], key, c)
        if not res:
            return None
        sep, child = res
        n.keys.insert(i, sep); n.ck.insert(i, ckey(sep)); n.ptrs.insert(i + 1, child)
        if self._put(pno, n, check=True):
            return None
        mid = len(n.keys) // 2
        up = n.keys[mid]
        rp = self.pager.new_page()
        right = Node(False, n.keys[mid + 1:], n.ptrs[mid + 1:])
        n.keys, n.ck, n.ptrs = n.keys[:mid], n.ck[:mid], n.ptrs[:mid + 1]
        self._put(rp, right); self._put(pno, n)
        return up, rp

    # ---- arama
    def _leaf_for(self, c):
        pno = self.root()
        while True:
            n = self.node(pno)
            if n.leaf:
                return pno, n
            pno = n.ptrs[bisect.bisect_right(n.ck, c)]

    def range(self, lo=None, hi=None, lo_incl=True, hi_incl=True):
        """(rid, değer) üretir. lo/hi None ise o taraf sınırsızdır (NULL'lar atlanır)."""
        c = (sort_key(lo), -1, -1) if lo is not None else AFTER_NULLS
        lo_k = sort_key(lo) if lo is not None else None
        hi_k = sort_key(hi) if hi is not None else None
        _, n = self._leaf_for(c)
        i = bisect.bisect_left(n.ck, c)
        while True:
            while i < len(n.keys):
                k = n.ck[i][0]
                if lo_k is not None and not lo_incl and k == lo_k:
                    i += 1; continue
                if hi_k is not None and (k > hi_k or (not hi_incl and k == hi_k)):
                    return
                key = n.keys[i]
                yield (key[1], key[2]), key[0]
                i += 1
            if n.next == NIL:
                return
            n, i = self.node(n.next), 0

    def seek(self, value):
        for rid, _ in self.range(value, value):
            yield rid

    # ---- silme
    def delete(self, value, rid):
        c = ckey((value, rid[0], rid[1]))
        pno, n = self._leaf_for(c)
        while True:
            i = bisect.bisect_left(n.ck, c)
            if i < len(n.ck):
                if n.ck[i] == c:
                    del n.keys[i]; del n.ck[i]
                    self._put(pno, n)
                    return True
                return False
            if n.next == NIL:
                return False
            pno = n.next
            n = self.node(pno)

    def height(self):
        h, pno = 1, self.root()
        while not self.node(pno).leaf:
            pno = self.node(pno).ptrs[0]; h += 1
        return h

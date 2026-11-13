"""Hesap Tablom formül motoru.

Hücre başvuruları (A1, $B$2), aralıklar (A1:C5), sayfalar arası başvurular
(Sayfa2!A1), işleçler ve Türkçe/İngilizce fonksiyon adlarını destekler.
"""
from __future__ import annotations

import datetime
import math
import re

# ---------------------------------------------------------------- hatalar
VAL, REF, NAME, DIV, NA, CYC, NUM, SYN = (
    "#DEĞER!", "#BAŞV!", "#AD?", "#SAYI/0!", "#YOK", "#DÖNGÜ!", "#SAYI!", "#FORMÜL!"
)


class FErr(Exception):
    """Formül hatası. Hem fırlatılır hem de hücre değeri olarak saklanır."""

    # Kurucu: başlangıç durumunu hazırlar.
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code

    # Hatanın ekranda görünen kodu (örn. #DEĞER!).
    def __str__(self):
        return self.code

    # İki hatayı kodlarına göre karşılaştırır.
    def __eq__(self, other):
        return isinstance(other, FErr) and other.code == self.code

    # Hatanın sözlük/küme anahtarı olabilmesi için özet değeri.
    def __hash__(self):
        return hash(self.code)


# Verilen kodla formül hatası fırlatır.
def fail(code):
    raise FErr(code)


# ---------------------------------------------------------------- adresler
def col_name(c: int) -> str:
    s, c = "", c + 1
    while c > 0:
        m = (c - 1) % 26
        s = chr(65 + m) + s
        c = (c - 1) // 26
    return s


# Sütun harfini sıra numarasına çevirir (A → 0, AA → 26).
def col_index(s: str) -> int:
    n = 0
    for ch in s.upper():
        n = n * 26 + (ord(ch) - 64)
    return n - 1


# Satır ve sütundan hücre adresi üretir (0,0 → A1).
def key(r: int, c: int) -> str:
    return f"{col_name(c)}{r + 1}"


_REF_ONLY = re.compile(r"^\$?([A-Za-z]{1,3})\$?(\d+)$")


# 'B12' gibi bir adresi (satır, sütun) ikilisine çevirir.
def parse_ref(s: str):
    m = _REF_ONLY.match(s)
    if not m:
        return None
    return int(m.group(2)) - 1, col_index(m.group(1))


# Değer sayı mı? (Python'da True da sayı sayıldığı için ayrıca denetlenir.)
def is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# ---------------------------------------------------------------- Türkçe sıralama
_TR_ALPHA = "abcçdefgğhıijklmnoöprsştuüvyz"
_TR_POS = {ch: i for i, ch in enumerate(_TR_ALPHA)}


# Türkçe kurala göre küçük harfe çevirir (I → ı).
def tr_lower(s: str) -> str:
    return s.replace("I", "ı").replace("İ", "i").lower()


# Türkçe kurala göre büyük harfe çevirir (i → İ).
def tr_upper(s: str) -> str:
    return s.replace("i", "İ").replace("ı", "I").upper()


# Türk alfabesine göre sıralama anahtarı üretir.
def tr_key(s: str):
    return [(_TR_POS[ch], "") if ch in _TR_POS else (1000 + ord(ch), "") for ch in tr_lower(s)]


# ---------------------------------------------------------------- sözcük çözümleme
_LETTER = re.compile(r"[A-Za-z_$ÇĞİÖŞÜçğıöşü]")
_IDCH = re.compile(r"[A-Za-z0-9_.$ÇĞİÖŞÜçğıöşü]")
_REF_WORD = re.compile(r"^\$?[A-Za-z]{1,3}\$?\d+$")


# Formül metnini simgelere ayırır (sayı, metin, başvuru, işleç...).
def tokenize(s: str):
    t, i, sheet = [], 0, None
    # ";" kullanılan ya da fonksiyon içermeyen formüllerde virgül ondalık ayıracıdır
    comma_dec = ";" in s or "(" not in s
    n = len(s)
    while i < n:
        ch = s[i]
        if ch.isspace():
            i += 1
            continue
        if ch.isdigit() or (ch == "." and i + 1 < n and s[i + 1].isdigit()):
            j = i
            while j < n and (s[j].isdigit() or s[j] == "."):
                j += 1
            if comma_dec and j + 1 < n and s[j] == "," and s[j + 1].isdigit() and "." not in s[i:j]:
                j += 1
                while j < n and s[j].isdigit():
                    j += 1
            if j < n and s[j] in "eE" and j + 1 < n and (s[j + 1].isdigit() or s[j + 1] in "+-"):
                j += 1
                if s[j] in "+-":
                    j += 1
                while j < n and s[j].isdigit():
                    j += 1
            try:
                v = float(s[i:j].replace(",", "."))
            except ValueError:
                fail(SYN)
            t.append(("num", v, None))
            i = j
            continue
        if ch == '"':
            j, buf, closed = i + 1, [], False
            while j < n:
                if s[j] == '"':
                    if j + 1 < n and s[j + 1] == '"':
                        buf.append('"')
                        j += 2
                        continue
                    closed = True
                    break
                buf.append(s[j])
                j += 1
            if not closed:
                fail(SYN)
            t.append(("str", "".join(buf), None))
            i = j + 1
            continue
        if ch == "'":
            j = s.find("'", i + 1)
            if j < 0 or j + 1 >= n or s[j + 1] != "!":
                fail(SYN)
            sheet = s[i + 1:j]
            i = j + 2
            continue
        if _LETTER.match(ch):
            j = i
            while j < n and _IDCH.match(s[j]):
                j += 1
            w = s[i:j]
            if j < n and s[j] == "!":
                sheet = w
                i = j + 1
                continue
            if _REF_WORD.match(w):
                t.append(("ref", w, sheet))
                sheet = None
                i = j
                continue
            k = j
            while k < n and s[k].isspace():
                k += 1
            if k < n and s[k] == "(":
                t.append(("fn", w, None))
                i = j
                continue
            u = w.upper()
            if u in ("TRUE", "DOĞRU"):
                t.append(("lit", True, None))
            elif u in ("FALSE", "YANLIŞ"):
                t.append(("lit", False, None))
            else:
                fail(NAME)
            i = j
            continue
        two = s[i:i + 2]
        if two in ("<=", ">=", "<>"):
            t.append(("op", two, None))
            i += 2
            continue
        if ch in "+-*/^&=<>%(),;:":
            t.append(("op", ch, None))
            i += 1
            continue
        fail(SYN)
    if sheet is not None:
        fail(SYN)
    return t


# Fonksiyon adını büyük harfe çevirir; Türkçe İ'yi I yapar.
def norm_name(n: str) -> str:
    return n.upper().replace("İ", "I")


# ---------------------------------------------------------------- ayrıştırma
_CMP = ("=", "<>", "<", ">", "<=", ">=")


# Simge listesinden formül ağacı kurar (öncelik sırasına göre).
def parse(tk):
    p = 0

    # Sıradaki simge verilen işleç mi?
    def is_op(v):
        return p < len(tk) and tk[p][0] == "op" and tk[p][1] == v

    # Beklenen işleci okur; yoksa sözdizimi hatası verir.
    def expect(v):
        nonlocal p
        if not is_op(v):
            fail(SYN)
        p += 1

    # Karşılaştırma (= <> < > <= >=) düzeyini ayrıştırır; en düşük öncelik.
    def cmp():
        nonlocal p
        left = cat()
        while p < len(tk) and tk[p][0] == "op" and tk[p][1] in _CMP:
            o = tk[p][1]
            p += 1
            left = ("bin", o, left, cat())
        return left

    # Metin birleştirme (&) düzeyini ayrıştırır.
    def cat():
        nonlocal p
        left = add()
        while is_op("&"):
            p += 1
            left = ("bin", "&", left, add())
        return left

    # Toplama ve çıkarma (+, -) düzeyini ayrıştırır.
    def add():
        nonlocal p
        left = mul()
        while is_op("+") or is_op("-"):
            o = tk[p][1]
            p += 1
            left = ("bin", o, left, mul())
        return left

    # Çarpma ve bölme (* /) düzeyini ayrıştırır.
    def mul():
        nonlocal p
        left = pw()
        while is_op("*") or is_op("/"):
            o = tk[p][1]
            p += 1
            left = ("bin", o, left, pw())
        return left

    # Üs alma (^) düzeyini ayrıştırır.
    def pw():
        nonlocal p
        left = un()
        while is_op("^"):
            p += 1
            left = ("bin", "^", left, un())
        return left

    # Tekli eksi/artı işaretini ayrıştırır.
    def un():
        nonlocal p
        if is_op("-"):
            p += 1
            return ("neg", un())
        if is_op("+"):
            p += 1
            return un()
        return post()

    # Yüzde (%) son ekini ayrıştırır.
    def post():
        nonlocal p
        e = prim()
        while is_op("%"):
            p += 1
            e = ("pct", e)
        return e

    # En temel öğeyi ayrıştırır: sayı, metin, başvuru, aralık, fonksiyon ya da parantez.
    def prim():
        nonlocal p
        if p >= len(tk):
            fail(SYN)
        kind, v, sheet = tk[p]
        if kind in ("num", "str", "lit"):
            p += 1
            return ("lit", v)
        if kind == "ref":
            p += 1
            a = parse_ref(v)
            if is_op(":"):
                p += 1
                if p >= len(tk) or tk[p][0] != "ref":
                    fail(SYN)
                b = parse_ref(tk[p][1])
                p += 1
                return ("range", sheet, min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
            return ("ref", sheet, a[0], a[1])
        if kind == "fn":
            p += 1
            expect("(")
            args = []
            if not is_op(")"):
                args.append(cmp())
                while is_op(",") or is_op(";"):
                    p += 1
                    args.append(cmp())
            expect(")")
            return ("fn", norm_name(v), args)
        if is_op("("):
            p += 1
            e = cmp()
            expect(")")
            return e
        fail(SYN)

    e = cmp()
    if p < len(tk):
        fail(SYN)
    return e


# ---------------------------------------------------------------- değerler
def literal(raw: str):
    t = raw.strip()
    if re.fullmatch(r"[-+]?\d+([.,]\d+)?", t):
        return float(t.replace(",", "."))
    if re.fullmatch(r"[-+]?\d+([.,]\d+)?%", t):
        return float(t[:-1].replace(",", ".")) / 100
    u = t.upper()
    if u in ("DOĞRU", "TRUE"):
        return True
    if u in ("YANLIŞ", "FALSE"):
        return False
    return raw


# Sayıyı 'Genel' biçimde, virgüllü ondalıkla yazar.
def fmt_general(v: float) -> str:
    if math.isnan(v) or math.isinf(v):
        return NUM
    if v == int(v) and abs(v) < 1e15:
        return str(int(v))
    s = f"{v:.12g}"
    return s.replace(".", ",")


# Bir değeri sayıya çevirir; olmuyorsa #DEĞER! verir.
def num(v):
    if isinstance(v, FErr):
        raise v
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if is_num(v):
        return float(v)
    if v is None or v == "":
        return 0.0
    t = str(v).strip().replace(",", ".")
    try:
        return float(t)
    except ValueError:
        fail(VAL)


# Bir değeri metne çevirir.
def to_str(v) -> str:
    if isinstance(v, FErr):
        raise v
    if v is None:
        return ""
    if isinstance(v, bool):
        return "DOĞRU" if v else "YANLIŞ"
    if is_num(v):
        return fmt_general(v)
    return str(v)


# Bir değeri DOĞRU/YANLIŞ'a çevirir.
def to_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    if is_num(v):
        return v != 0
    if v is None or v == "":
        return False
    u = str(v).upper()
    if u in ("DOĞRU", "TRUE"):
        return True
    if u in ("YANLIŞ", "FALSE"):
        return False
    fail(VAL)


# İki değeri karşılaştırır: küçükse eksi, eşitse sıfır, büyükse artı döner.
def compare(a, b) -> int:
    if isinstance(a, FErr):
        raise a
    if isinstance(b, FErr):
        raise b
    if a is None:
        a = "" if isinstance(b, str) else 0.0
    if b is None:
        b = "" if isinstance(a, str) else 0.0
    if is_num(a) and is_num(b):
        return (a > b) - (a < b)
    if isinstance(a, bool) and isinstance(b, bool):
        return int(a) - int(b)
    if is_num(a):
        return -1
    if is_num(b):
        return 1
    ka, kb = tr_key(to_str(a)), tr_key(to_str(b))
    return (ka > kb) - (ka < kb)


# Bir değeri hücrede gösterilecek metne çevirir.
def display(v, st=None) -> str:
    """Bir değeri hücrede gösterilecek metne çevirir."""
    if v is None:
        return ""
    if isinstance(v, FErr):
        return v.code
    if isinstance(v, bool):
        return "DOĞRU" if v else "YANLIŞ"
    if is_num(v):
        if math.isnan(v) or math.isinf(v):
            return NUM
        f = (st or {}).get("fmt")

        # Sayıyı Türkçe biçimde yazar (1.234,56).
        def tr(x, d):
            return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")

        if f == "num":
            return tr(v, 2)
        if f == "int":
            return tr(round(v), 0)
        if f == "cur":
            return tr(v, 2) + " ₺"
        if f == "pct":
            s = f"{v * 100:.2f}".rstrip("0").rstrip(".").replace(".", ",")
            return "%" + s
        return fmt_general(v)
    return str(v)


class Rng:
    __slots__ = ("sh", "r1", "c1", "r2", "c2")

    # Kurucu: başlangıç durumunu hazırlar.
    def __init__(self, sh, r1, c1, r2, c2):
        self.sh, self.r1, self.c1, self.r2, self.c2 = sh, r1, c1, r2, c2


# ETOPLA/EĞERSAY ölçütünü (">5", "elma" gibi) bir sınama işlevine çevirir.
def _crit(c):
    if isinstance(c, str):
        m = re.match(r"^(<=|>=|<>|<|>|=)?(.*)$", c, re.S)
        op, rhs = m.group(1) or "=", m.group(2)
        try:
            nv = float(rhs.strip().replace(",", ".")) if rhs.strip() else None
        except ValueError:
            nv = None

        # Bir değerin ölçüte uyup uymadığını sınar.
        def test(v):
            if isinstance(v, FErr):
                return False
            if nv is not None:
                if not is_num(v):
                    if op in ("=", "<>"):
                        k = compare(to_str(v), rhs)
                    else:
                        return False
                else:
                    k = (v > nv) - (v < nv)
            else:
                if op not in ("=", "<>") and is_num(v):
                    return False
                k = compare("" if v is None else v, rhs)
            return {"=": k == 0, "<>": k != 0, "<": k < 0, ">": k > 0, "<=": k <= 0, ">=": k >= 0}[op]

        return test

    # Ölçüt metin değilse birebir eşitlik arar.
    def eq(v):
        try:
            return not isinstance(v, FErr) and compare(v, c) == 0
        except FErr:
            return False

    return eq


# ---------------------------------------------------------------- motor
class Engine:
    """Bir çalışma kitabının hücre değerlerini hesaplar ve önbelleğe alır."""

    # Kurucu: başlangıç durumunu hazırlar.
    def __init__(self, get_book):
        self._get_book = get_book
        self.cache = {}
        self.visiting = set()
        self.ast = {}
        self.fn = {}
        self._register()

    # Motorun üzerinde çalıştığı güncel çalışma kitabı.
    @property
    def book(self):
        return self._get_book()

    # Hesaplanmış değer önbelleğini boşaltır.
    def clear(self):
        self.cache.clear()

    # Sayfayı adına göre bulur (büyük/küçük harf duyarsız).
    def sheet_by_name(self, name):
        low = tr_lower(name)
        for s in self.book["sheets"]:
            if tr_lower(s["name"]) == low:
                return s
        return None

    # Bir hücrenin değerini hesaplar; önbellek kullanır, döngüsel başvuruyu yakalar.
    def value(self, sh, r, c):
        k = (sh["id"], r, c)
        if k in self.cache:
            return self.cache[k]
        cell = sh["cells"].get(key(r, c))
        raw = cell.get("v", "") if cell else ""
        if not raw:
            v = None
        elif raw.startswith("=") and len(raw) > 1:
            if k in self.visiting:
                return FErr(CYC)
            self.visiting.add(k)
            try:
                src = raw[1:]
                tree = self.ast.get(src)
                if tree is None:
                    tree = parse(tokenize(src))
                    self.ast[src] = tree
                v = self.scalar(self.ev(tree, sh))
                if v is None:
                    v = 0.0
            except FErr as e:
                v = e
            except (ValueError, OverflowError, ZeroDivisionError, RecursionError):
                v = FErr(NUM)
            finally:
                self.visiting.discard(k)
        else:
            v = literal(raw)
        self.cache[k] = v
        return v

    # --- değerlendirme
    def resolve(self, name, sh):
        if name is None:
            return sh
        s = self.sheet_by_name(name)
        if s is None:
            fail(REF)
        return s

    # Ayrıştırılmış bir formül ağacını hesaplar.
    def ev(self, n, sh):
        kind = n[0]
        if kind == "lit":
            return n[1]
        if kind == "ref":
            v = self.value(self.resolve(n[1], sh), n[2], n[3])
            if isinstance(v, FErr):
                raise v
            return v
        if kind == "range":
            return Rng(self.resolve(n[1], sh), n[2], n[3], n[4], n[5])
        if kind == "neg":
            return -num(self.scalar(self.ev(n[1], sh)))
        if kind == "pct":
            return num(self.scalar(self.ev(n[1], sh))) / 100
        if kind == "bin":
            return self.binop(n[1], self.scalar(self.ev(n[2], sh)), self.scalar(self.ev(n[3], sh)))
        if kind == "fn":
            f = self.fn.get(n[1])
            if f is None:
                fail(NAME)
            return f(n[2], sh)
        fail(SYN)

    # Tek hücrelik aralığı değere çevirir; çok hücreliyse #DEĞER! verir.
    def scalar(self, v):
        if isinstance(v, Rng):
            if v.r1 == v.r2 and v.c1 == v.c2:
                x = self.value(v.sh, v.r1, v.c1)
                if isinstance(x, FErr):
                    raise x
                return x
            fail(VAL)
        if isinstance(v, FErr):
            raise v
        return v

    # İki değer arasında işleç uygular (+ - * / ^ & ve karşılaştırmalar).
    @staticmethod
    def binop(o, a, b):
        if o == "+":
            return num(a) + num(b)
        if o == "-":
            return num(a) - num(b)
        if o == "*":
            return num(a) * num(b)
        if o == "/":
            d = num(b)
            if d == 0:
                fail(DIV)
            return num(a) / d
        if o == "^":
            try:
                return float(num(a) ** num(b))
            except (OverflowError, ZeroDivisionError):
                fail(NUM)
        if o == "&":
            return to_str(a) + to_str(b)
        c = compare(a, b)
        return {"=": c == 0, "<>": c != 0, "<": c < 0, ">": c > 0, "<=": c <= 0, ">=": c >= 0}[o]

    # Bir aralıktaki değerleri iki boyutlu liste olarak döndürür.
    def range_vals(self, rg):
        return [[self.value(rg.sh, r, c) for c in range(rg.c1, rg.c2 + 1)] for r in range(rg.r1, rg.r2 + 1)]

    # Bağımsız değişkenleri ve aralıkları tek bir değer listesine açar.
    def flat(self, args, sh):
        out = []
        for a in args:
            v = self.ev(a, sh)
            if isinstance(v, Rng):
                for row in self.range_vals(v):
                    out.extend((x, True) for x in row)
            else:
                out.append((v, False))
        return out

    # Bağımsız değişkenlerdeki sayıları toplar (aralıktaki metinler atlanır).
    def nums(self, args, sh):
        out = []
        for v, rg in self.flat(args, sh):
            if isinstance(v, FErr):
                raise v
            if rg:
                if is_num(v):
                    out.append(float(v))
            else:
                out.append(num(v))
        return out

    # i'nci bağımsız değişkeni tek bir değer olarak hesaplar.
    def arg(self, a, i, sh):
        if i >= len(a):
            fail(VAL)
        return self.scalar(self.ev(a[i], sh))

    # i'nci bağımsız değişkenin aralık olmasını şart koşar.
    def range_arg(self, a, i, sh):
        v = self.ev(a[i], sh) if i < len(a) else None
        if not isinstance(v, Rng):
            fail(VAL)
        return v

    # --- fonksiyonlar
    def _register(self):
        F = self.fn

        # Bir fonksiyonu birden çok adla (Türkçe ve İngilizce) kaydeder.
        def d(names, f):
            for n in names.split():
                F[norm_name(n)] = f

        # ORTALAMA: sayıların aritmetik ortalaması.
        def avg(a, sh):
            n = self.nums(a, sh)
            if not n:
                fail(DIV)
            return sum(n) / len(n)

        # YUVARLA: Excel gibi yarımları sıfırdan uzağa yuvarlar.
        def rnd(a, sh):
            x = num(self.arg(a, 0, sh))
            dg = int(num(self.arg(a, 1, sh))) if len(a) > 1 else 0
            if abs(dg) > 15:
                fail(NUM)
            m = 10 ** dg
            return math.floor(abs(x) * m + 0.5 + 1e-9) / m * (1 if x >= 0 else -1)

        # KAREKÖK: eksi sayılarda #SAYI! verir.
        def sqrt(a, sh):
            x = num(self.arg(a, 0, sh))
            if x < 0:
                fail(NUM)
            return math.sqrt(x)

        # MOD: bölümden kalan (Excel gibi bölenin işaretini alır).
        def mod(a, sh):
            x, dv = num(self.arg(a, 0, sh)), num(self.arg(a, 1, sh))
            if dv == 0:
                fail(DIV)
            return x - dv * math.floor(x / dv)

        # VE/YADA için aralıklardaki boş ve metin hücreleri atlar.
        def logic_vals(a, sh):
            return [v for v, rg in self.flat(a, sh) if not (rg and (v is None or isinstance(v, str)))]

        # EĞER: koşula göre ikinci ya da üçüncü bağımsız değişkeni döndürür.
        def if_(a, sh):
            if to_bool(self.arg(a, 0, sh)):
                return self.ev(a[1], sh) if len(a) > 1 else True
            return self.ev(a[2], sh) if len(a) > 2 else False

        # EĞERHATA: hata varsa yedek değeri döndürür.
        def iferror(a, sh):
            try:
                return self.scalar(self.ev(a[0], sh))
            except FErr:
                return self.ev(a[1], sh) if len(a) > 1 else ""

        # ETOPLA: ölçüte uyan satırların toplamı.
        def sumif(a, sh):
            rg = self.range_arg(a, 0, sh)
            test = _crit(self.arg(a, 1, sh))
            sr = self.range_arg(a, 2, sh) if len(a) > 2 else rg
            total = 0.0
            for i in range(rg.r2 - rg.r1 + 1):
                for j in range(rg.c2 - rg.c1 + 1):
                    if test(self.value(rg.sh, rg.r1 + i, rg.c1 + j)):
                        v = self.value(sr.sh, sr.r1 + i, sr.c1 + j)
                        if isinstance(v, FErr):
                            raise v
                        if is_num(v):
                            total += v
            return total

        # EĞERSAY: ölçüte uyan hücreleri sayar.
        def countif(a, sh):
            rg = self.range_arg(a, 0, sh)
            test = _crit(self.arg(a, 1, sh))
            return float(sum(1 for row in self.range_vals(rg) for v in row if test(v)))

        # DÜŞEYARA: ilk sütunda arar, istenen sütundaki değeri döndürür.
        def vlookup(a, sh):
            look = self.arg(a, 0, sh)
            rg = self.range_arg(a, 1, sh)
            ci = int(num(self.arg(a, 2, sh))) - 1
            approx = to_bool(self.arg(a, 3, sh)) if len(a) > 3 else True
            if ci < 0 or ci > rg.c2 - rg.c1:
                fail(REF)
            hit = -1
            for r in range(rg.r1, rg.r2 + 1):
                v = self.value(rg.sh, r, rg.c1)
                if v is None or isinstance(v, FErr):
                    continue
                try:
                    k = compare(v, look)
                except FErr:
                    continue
                if k == 0:
                    hit = r
                    break
                if approx:
                    if k < 0:
                        hit = r
                    else:
                        break
            if hit < 0:
                fail(NA)
            out = self.value(rg.sh, hit, rg.c1 + ci)
            if isinstance(out, FErr):
                raise out
            return out

        # BUGÜN: bugünün tarihi (gg.aa.yyyy).
        def today(a, sh):
            return datetime.date.today().strftime("%d.%m.%Y")

        # ŞİMDİ: bugünün tarihi ve saati.
        def now(a, sh):
            return datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

        d("SUM TOPLA", lambda a, sh: sum(self.nums(a, sh)))
        d("AVERAGE ORTALAMA", avg)
        d("MIN", lambda a, sh: min(self.nums(a, sh), default=0.0))
        d("MAX MAK", lambda a, sh: max(self.nums(a, sh), default=0.0))
        d("COUNT BAĞ_DEĞ_SAY", lambda a, sh: float(sum(1 for v, _ in self.flat(a, sh) if is_num(v))))
        d("COUNTA BAĞ_DEĞ_DOLU_SAY", lambda a, sh: float(sum(1 for v, _ in self.flat(a, sh) if v not in (None, ""))))
        d("ROUND YUVARLA", rnd)
        d("ABS MUTLAK", lambda a, sh: abs(num(self.arg(a, 0, sh))))
        d("SQRT KAREKÖK", sqrt)
        d("POWER KUVVET", lambda a, sh: self.binop("^", self.arg(a, 0, sh), self.arg(a, 1, sh)))
        d("INT TAMSAYI", lambda a, sh: float(math.floor(num(self.arg(a, 0, sh)))))
        d("MOD", mod)
        d("PI", lambda a, sh: math.pi)
        d("CONCAT CONCATENATE BİRLEŞTİR", lambda a, sh: "".join(to_str(v) for v, _ in self.flat(a, sh)))
        d("LEN UZUNLUK", lambda a, sh: float(len(to_str(self.arg(a, 0, sh)))))
        d("UPPER BÜYÜKHARF", lambda a, sh: tr_upper(to_str(self.arg(a, 0, sh))))
        d("LOWER KÜÇÜKHARF", lambda a, sh: tr_lower(to_str(self.arg(a, 0, sh))))
        d("TODAY BUGÜN", today)
        d("NOW ŞİMDİ", now)
        d("AND VE", lambda a, sh: all(to_bool(v) for v in logic_vals(a, sh)))
        d("OR YADA", lambda a, sh: any(to_bool(v) for v in logic_vals(a, sh)))
        d("NOT DEĞİL", lambda a, sh: not to_bool(self.arg(a, 0, sh)))
        d("IF EĞER", if_)
        d("IFERROR EĞERHATA", iferror)
        d("SUMIF ETOPLA", sumif)
        d("COUNTIF EĞERSAY", countif)
        d("VLOOKUP DÜŞEYARA", vlookup)


# ---------------------------------------------------------------- formül kaydırma
_REF_RE = re.compile(
    r"(?<![A-Za-z0-9_.$ÇĞİÖŞÜçğıöşü!'])(\$?)([A-Za-z]{1,3})(\$?)(\d+)"
    r"(?::(\$?)([A-Za-z]{1,3})(\$?)(\d+))?(?![A-Za-z0-9_(ÇĞİÖŞÜçğıöşü!])"
)
_STR_SPLIT = re.compile(r'("(?:[^"]|"")*")')


# Formüldeki her hücre başvurusunu verilen işlevle dönüştürür.
def map_formula(f, fn):
    """Formüldeki her başvuruyu fn(a, b) ile dönüştürür.

    a ve b sözlüktür: {"r", "c", "ar", "ac"} (ar/ac: satır/sütun mutlak mı).
    fn None dönerse başvuru #BAŞV! olur.
    """
    if not isinstance(f, str) or not f.startswith("="):
        return f

    # Başvuruyu metne geri yazar ($ işaretleriyle).
    def out(x):
        return ("$" if x["ac"] else "") + col_name(x["c"]) + ("$" if x["ar"] else "") + str(x["r"] + 1)

    # Tek bir başvuruyu (ya da aralığı) dönüştürür.
    def repl(m):
        d1, cl, d2, rw, e1, cl2, e2, rw2 = m.groups()
        a = {"c": col_index(cl), "r": int(rw) - 1, "ac": bool(d1), "ar": bool(d2)}
        b = {"c": col_index(cl2), "r": int(rw2) - 1, "ac": bool(e1), "ar": bool(e2)} if cl2 else None
        res = fn(a, b)
        if not res:
            return REF
        return out(res[0]) + (":" + out(res[1]) if res[1] else "")

    parts = _STR_SPLIT.split(f)
    return "".join(p if i % 2 else _REF_RE.sub(repl, p) for i, p in enumerate(parts))


# Kopyala-yapıştırda göreli başvuruları kaydırır ($ olanlar sabit kalır).
def shift_formula(f, dr, dc):
    """Kopyala-yapıştırda göreli başvuruları kaydırır."""
    if not dr and not dc:
        return f

    # Bir başvuruyu, mutlak değilse kaydırır.
    def sh1(x):
        y = dict(x)
        if not x["ac"]:
            y["c"] += dc
        if not x["ar"]:
            y["r"] += dr
        return y

    # Bir başvuruyu (a) ya da aralığı (a:b) dönüştürür; None dönerse #BAŞV! olur.
    def fn(a, b):
        A, B = sh1(a), (sh1(b) if b else None)
        if A["r"] < 0 or A["c"] < 0 or (B and (B["r"] < 0 or B["c"] < 0)):
            return None
        return A, B

    return map_formula(f, fn)


# Satır/sütun ekleme-silme sonrası başvuruları güncelleyen işlev üretir.
def structural_map(is_row, insert, at, count):
    """Satır/sütun ekleme-silme sonrası başvuruları güncelleyen işlev üretir."""
    fld = "r" if is_row else "c"

    # Başvurunun satır ya da sütun alanını değiştirir.
    def setv(x, v):
        y = dict(x)
        y[fld] = v
        return y

    # Bir başvuruyu (a) ya da aralığı (a:b) dönüştürür; None dönerse #BAŞV! olur.
    def fn(a, b):
        if insert:
            # Yardımcı dönüşüm işlevi.
            def f(x):
                return setv(x, x[fld] + count) if x[fld] >= at else x
            return f(a), (f(b) if b else None)
        end = at + count - 1
        if not b:
            i = a[fld]
            if at <= i <= end:
                return None
            return (setv(a, i - count) if i > end else a), None
        s, e = a[fld], b[fld]
        ns = s if s < at else (s - count if s > end else at)
        ne = e if e < at else (e - count if e > end else at - 1)
        if ne < ns:
            return None
        return setv(a, ns), setv(b, ne)

    return fn

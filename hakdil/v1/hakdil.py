#!/usr/bin/env python3
"""HakDil - Python benzeri, Türkçe anahtar kelimeli programlama dili.

Kullanım:
    python hakdil.py dosya.hak     # dosya çalıştır
    python hakdil.py               # etkileşimli mod
"""
import sys
import operator

sys.setrecursionlimit(10000)
SURUM = "1.0"


# ---------------------------------------------------------------- Hatalar
class HakHata(Exception):
    def __init__(self, mesaj, satir=None):
        super().__init__(mesaj)
        self.mesaj = mesaj
        self.satir = satir

    def __str__(self):
        if self.satir:
            return f"Hata (satır {self.satir}): {self.mesaj}"
        return f"Hata: {self.mesaj}"


class Dondur(Exception):
    def __init__(self, deger):
        self.deger = deger


class Kir(Exception):
    pass


class Devam(Exception):
    pass


# ---------------------------------------------------------------- Sözcük çözümleyici
KELIMELER = {
    "eğer", "yada", "değilse", "iken", "için", "içinde", "fonk", "döndür",
    "kır", "devam", "geç", "ve", "veya", "değil", "doğru", "yanlış", "boş",
}
OPS2 = {"**", "//", "==", "!=", "<=", ">=", "+=", "-=", "*=", "/="}
OPS1 = set("+-*/%<>=()[]{},:.")
KACIS = {"n": "\n", "t": "\t", "\\": "\\", '"': '"', "'": "'"}


class Tok:
    __slots__ = ("tur", "deger", "satir")

    def __init__(self, tur, deger, satir):
        self.tur, self.deger, self.satir = tur, deger, satir


def tokenize(kaynak):
    toks, girintiler, parantez = [], [0], 0
    for no, satir in enumerate(kaynak.split("\n"), 1):
        satir = satir.replace("\t", "    ").rstrip("\r")
        i, n = 0, len(satir)
        if parantez == 0:
            s = satir.strip()
            if not s or s.startswith("#"):
                continue
            g = len(satir) - len(satir.lstrip(" "))
            if g > girintiler[-1]:
                girintiler.append(g)
                toks.append(Tok("GIR", None, no))
            while g < girintiler[-1]:
                girintiler.pop()
                toks.append(Tok("CIK", None, no))
            if g != girintiler[-1]:
                raise HakHata("Girinti hatalı", no)
            i = g
        while i < n:
            c = satir[i]
            if c == " ":
                i += 1
                continue
            if c == "#":
                break
            if c.isdigit():
                j = i
                while j < n and (satir[j].isdigit() or satir[j] == "_"):
                    j += 1
                if j < n - 1 and satir[j] == "." and satir[j + 1].isdigit():
                    j += 1
                    while j < n and satir[j].isdigit():
                        j += 1
                    toks.append(Tok("SAYI", float(satir[i:j].replace("_", "")), no))
                else:
                    toks.append(Tok("SAYI", int(satir[i:j].replace("_", "")), no))
                i = j
                continue
            if c.isalpha() or c == "_":
                j = i
                while j < n and (satir[j].isalnum() or satir[j] == "_"):
                    j += 1
                k = satir[i:j]
                toks.append(Tok("KEL" if k in KELIMELER else "AD", k, no))
                i = j
                continue
            if c in "\"'":
                j, buf = i + 1, []
                while j < n and satir[j] != c:
                    if satir[j] == "\\" and j + 1 < n:
                        buf.append(KACIS.get(satir[j + 1], "\\" + satir[j + 1]))
                        j += 2
                    else:
                        buf.append(satir[j])
                        j += 1
                if j >= n:
                    raise HakHata("Metin kapatılmamış", no)
                toks.append(Tok("METIN", "".join(buf), no))
                i = j + 1
                continue
            if satir[i:i + 2] in OPS2:
                toks.append(Tok("OP", satir[i:i + 2], no))
                i += 2
                continue
            if c in OPS1:
                if c in "([{":
                    parantez += 1
                elif c in ")]}":
                    parantez = max(0, parantez - 1)
                toks.append(Tok("OP", c, no))
                i += 1
                continue
            raise HakHata(f"Bilinmeyen karakter: {c!r}", no)
        if parantez == 0:
            toks.append(Tok("SATIR", None, no))
    son = toks[-1].satir if toks else 1
    while len(girintiler) > 1:
        girintiler.pop()
        toks.append(Tok("CIK", None, son))
    toks.append(Tok("SON", None, son))
    return toks


# ---------------------------------------------------------------- Ayrıştırıcı
class Ayristirici:
    def __init__(self, toks):
        self.t, self.p = toks, 0

    def bak(self):
        return self.t[self.p]

    def al(self):
        t = self.t[self.p]
        self.p += 1
        return t

    def esle(self, tur, deger=None):
        t = self.t[self.p]
        if t.tur == tur and (deger is None or t.deger == deger):
            self.p += 1
            return t
        return None

    def bekle(self, tur, deger=None):
        t = self.esle(tur, deger)
        if t is None:
            b = self.bak()
            bulunan = b.deger if b.deger is not None else {"SATIR": "satır sonu", "SON": "dosya sonu",
                                                            "GIR": "girinti", "CIK": "girinti sonu"}.get(b.tur, b.tur)
            beklenen = deger or {"AD": "isim", "GIR": "girintili blok"}.get(tur, tur)
            raise HakHata(f"'{beklenen}' bekleniyordu, '{bulunan}' bulundu", b.satir)
        return t

    def program(self):
        govde = []
        while self.bak().tur != "SON":
            if self.esle("SATIR"):
                continue
            govde.append(self.deyim())
        return govde

    def blok(self):
        self.bekle("OP", ":")
        if self.esle("SATIR"):
            self.bekle("GIR")
            govde = []
            while not self.esle("CIK"):
                if self.bak().tur == "SON":
                    break
                govde.append(self.deyim())
            return govde
        d = self.basit()
        self.bekle("SATIR")
        return [d]

    def deyim(self):
        t = self.bak()
        if t.tur == "KEL":
            k = t.deger
            if k == "eğer":
                self.al()
                dallar = [(self.ifade(), self.blok())]
                degilse = None
                while self.esle("KEL", "yada"):
                    dallar.append((self.ifade(), self.blok()))
                if self.esle("KEL", "değilse"):
                    degilse = self.blok()
                return ("eger", t.satir, dallar, degilse)
            if k == "iken":
                self.al()
                kosul = self.ifade()
                return ("iken", t.satir, kosul, self.blok())
            if k == "için":
                self.al()
                ad = self.bekle("AD").deger
                self.bekle("KEL", "içinde")
                kaynak = self.ifade()
                return ("icin", t.satir, ad, kaynak, self.blok())
            if k == "fonk":
                self.al()
                ad = self.bekle("AD").deger
                self.bekle("OP", "(")
                params = []
                if not self.esle("OP", ")"):
                    while True:
                        params.append(self.bekle("AD").deger)
                        if self.esle("OP", ")"):
                            break
                        self.bekle("OP", ",")
                return ("fonk", t.satir, ad, params, self.blok())
        d = self.basit()
        if self.bak().tur != "SON":
            self.bekle("SATIR")
        return d

    def basit(self):
        t = self.bak()
        if t.tur == "KEL":
            if t.deger == "döndür":
                self.al()
                d = None if self.bak().tur in ("SATIR", "SON") else self.ifade()
                return ("dondur", t.satir, d)
            if t.deger in ("kır", "devam", "geç"):
                self.al()
                return ({"kır": "kir", "devam": "devam", "geç": "gec"}[t.deger], t.satir)
        e = self.ifade()
        o = self.bak()
        if o.tur == "OP" and o.deger in ("=", "+=", "-=", "*=", "/="):
            self.al()
            if e[0] not in ("ad", "indeks"):
                raise HakHata("Geçersiz atama hedefi", o.satir)
            return ("ata", t.satir, e, o.deger, self.ifade())
        return ("ifade", t.satir, e)

    # --- ifadeler (öncelik sırasıyla)
    def ifade(self):
        sol = self.ve()
        while self.esle("KEL", "veya"):
            sol = ("veya", sol, self.ve())
        return sol

    def ve(self):
        sol = self.degil()
        while self.esle("KEL", "ve"):
            sol = ("ve", sol, self.degil())
        return sol

    def degil(self):
        if self.esle("KEL", "değil"):
            return ("degil", self.degil())
        return self.karsilastir()

    def karsilastir(self):
        sol = self.toplam()
        while True:
            t = self.bak()
            if t.tur == "OP" and t.deger in ("==", "!=", "<", ">", "<=", ">="):
                self.al()
                sol = ("ikili", t.deger, sol, self.toplam())
            elif t.tur == "KEL" and t.deger == "içinde":
                self.al()
                sol = ("ikili", "içinde", sol, self.toplam())
            else:
                return sol

    def toplam(self):
        sol = self.carpim()
        while self.bak().tur == "OP" and self.bak().deger in ("+", "-"):
            op = self.al().deger
            sol = ("ikili", op, sol, self.carpim())
        return sol

    def carpim(self):
        sol = self.tekli()
        while self.bak().tur == "OP" and self.bak().deger in ("*", "/", "//", "%"):
            op = self.al().deger
            sol = ("ikili", op, sol, self.tekli())
        return sol

    def tekli(self):
        if self.esle("OP", "-"):
            return ("eksi", self.tekli())
        if self.esle("OP", "+"):
            return self.tekli()
        return self.us()

    def us(self):
        taban = self.sonek()
        if self.esle("OP", "**"):
            return ("ikili", "**", taban, self.tekli())
        return taban

    def sonek(self):
        e = self.birincil()
        while True:
            if self.esle("OP", "("):
                args = []
                if not self.esle("OP", ")"):
                    while True:
                        args.append(self.ifade())
                        if self.esle("OP", ")"):
                            break
                        self.bekle("OP", ",")
                e = ("cagir", e, args)
            elif self.esle("OP", "["):
                bas = None if self.bak().deger == ":" else self.ifade()
                if self.esle("OP", ":"):
                    son = None if self.bak().deger == "]" else self.ifade()
                    self.bekle("OP", "]")
                    e = ("dilim", e, bas, son)
                else:
                    self.bekle("OP", "]")
                    e = ("indeks", e, bas)
            elif self.esle("OP", "."):
                e = ("ozellik", e, self.bekle("AD").deger)
            else:
                return e

    def birincil(self):
        t = self.al()
        if t.tur in ("SAYI", "METIN"):
            return ("sabit", t.deger)
        if t.tur == "AD":
            return ("ad", t.deger)
        if t.tur == "KEL" and t.deger in ("doğru", "yanlış", "boş"):
            return ("sabit", {"doğru": True, "yanlış": False, "boş": None}[t.deger])
        if t.tur == "OP":
            if t.deger == "(":
                e = self.ifade()
                self.bekle("OP", ")")
                return e
            if t.deger == "[":
                ogeler = []
                while not self.esle("OP", "]"):
                    ogeler.append(self.ifade())
                    if not self.esle("OP", ","):
                        self.bekle("OP", "]")
                        break
                return ("liste", ogeler)
            if t.deger == "{":
                ciftler = []
                while not self.esle("OP", "}"):
                    k = self.ifade()
                    self.bekle("OP", ":")
                    ciftler.append((k, self.ifade()))
                    if not self.esle("OP", ","):
                        self.bekle("OP", "}")
                        break
                return ("sozluk", ciftler)
        bulunan = t.deger if t.deger is not None else "satır sonu"
        raise HakHata(f"Beklenmeyen ifade: '{bulunan}'", t.satir)


# ---------------------------------------------------------------- Çalışma zamanı
class Ortam:
    def __init__(self, ust=None):
        self.d, self.ust = {}, ust

    def bul(self, ad):
        o = self
        while o is not None:
            if ad in o.d:
                return o.d[ad]
            o = o.ust
        raise HakHata(f"Tanımsız isim: '{ad}'")


class Fonk:
    def __init__(self, ad, params, govde, ortam):
        self.ad, self.params, self.govde, self.ortam = ad, params, govde, ortam

    def __call__(self, *args):
        if len(args) != len(self.params):
            raise HakHata(f"'{self.ad}' {len(self.params)} değer bekliyor, {len(args)} verildi")
        o = Ortam(self.ortam)
        o.d.update(zip(self.params, args))
        try:
            calistir_blok(self.govde, o)
        except Dondur as r:
            return r.deger
        return None


def metin(v):
    if v is True:
        return "doğru"
    if v is False:
        return "yanlış"
    if v is None:
        return "boş"
    if isinstance(v, list):
        return "[" + ", ".join(temsil(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{temsil(k)}: {temsil(x)}" for k, x in v.items()) + "}"
    if isinstance(v, Fonk):
        return f"<fonk {v.ad}>"
    if callable(v):
        return "<yerleşik fonk>"
    return str(v)


def temsil(v):
    return '"' + v + '"' if isinstance(v, str) else metin(v)


def tur_adi(v):
    if isinstance(v, bool):
        return "mantıksal"
    if v is None:
        return "boş"
    return {int: "tam_sayı", float: "ondalık", str: "metin", list: "liste", dict: "sözlük"}.get(
        type(v), "fonksiyon" if callable(v) else "bilinmeyen")


def tr_buyuk(s):
    return s.replace("i", "İ").replace("ı", "I").upper()


def tr_kucuk(s):
    return s.replace("I", "ı").replace("İ", "i").lower()


def _sayi(x):
    try:
        return int(x.strip()) if isinstance(x, str) else int(x)
    except ValueError:
        raise HakHata(f"Sayıya çevrilemedi: {temsil(x)}")


def _ondalik(x):
    try:
        return float(x.strip().replace(",", ".")) if isinstance(x, str) else float(x)
    except ValueError:
        raise HakHata(f"Ondalığa çevrilemedi: {temsil(x)}")


YERLESIK = {
    "yazdır": lambda *a: print(*(metin(x) for x in a)),
    "girdi": lambda m="": input(metin(m)),
    "uzunluk": len,
    "aralık": lambda *a: list(range(*a)),
    "sayı": _sayi,
    "ondalık": _ondalik,
    "metin": metin,
    "liste": lambda x=None: [] if x is None else list(x),
    "tür": tur_adi,
    "toplam": sum,
    "en_büyük": lambda *a: max(a[0]) if len(a) == 1 else max(a),
    "en_küçük": lambda *a: min(a[0]) if len(a) == 1 else min(a),
    "yuvarla": round,
    "mutlak": abs,
    "sıralı": sorted,
}

METOTLAR = {
    list: {"ekle": "append", "çıkar": "pop", "sil": "remove", "sırala": "sort", "ters_çevir": "reverse",
           "genişlet": "extend", "bul": "index", "say": "count", "araya_ekle": "insert", "temizle": "clear"},
    str: {"böl": "split", "değiştir": "replace", "kırp": "strip", "birleştir": "join", "başlar": "startswith",
          "biter": "endswith", "bul": "find", "say": "count"},
    dict: {"al": "get", "sil": "pop", "güncelle": "update", "temizle": "clear"},
}
OZEL_METOT = {
    (str, "büyük"): lambda s: lambda: tr_buyuk(s),
    (str, "küçük"): lambda s: lambda: tr_kucuk(s),
    (dict, "anahtarlar"): lambda d: lambda: list(d.keys()),
    (dict, "değerler"): lambda d: lambda: list(d.values()),
    (dict, "çiftler"): lambda d: lambda: [[k, v] for k, v in d.items()],
}


def ozellik_al(nesne, ad):
    t = type(nesne)
    if (t, ad) in OZEL_METOT:
        return OZEL_METOT[(t, ad)](nesne)
    if t in METOTLAR and ad in METOTLAR[t]:
        return getattr(nesne, METOTLAR[t][ad])
    raise HakHata(f"{tur_adi(nesne)} türünde '{ad}' diye bir özellik yok")


def bol(a, b):
    if isinstance(a, int) and isinstance(b, int) and not isinstance(a, bool) and b != 0 and a % b == 0:
        return a // b
    return a / b


def topla(a, b):
    if isinstance(a, str) != isinstance(b, str):
        return metin(a) + metin(b)
    return a + b


IKILI = {
    "+": topla, "-": operator.sub, "*": operator.mul, "/": bol, "//": operator.floordiv,
    "%": operator.mod, "**": operator.pow, "==": operator.eq, "!=": operator.ne,
    "<": operator.lt, ">": operator.gt, "<=": operator.le, ">=": operator.ge,
    "içinde": lambda a, b: a in b,
}


def degerlendir(e, o):
    k = e[0]
    if k == "sabit":
        return e[1]
    if k == "ad":
        return o.bul(e[1])
    if k == "ikili":
        return IKILI[e[1]](degerlendir(e[2], o), degerlendir(e[3], o))
    if k == "ve":
        sol = degerlendir(e[1], o)
        return degerlendir(e[2], o) if sol else sol
    if k == "veya":
        sol = degerlendir(e[1], o)
        return sol if sol else degerlendir(e[2], o)
    if k == "degil":
        return not degerlendir(e[1], o)
    if k == "eksi":
        return -degerlendir(e[1], o)
    if k == "cagir":
        f = degerlendir(e[1], o)
        if not callable(f):
            raise HakHata(f"{tur_adi(f)} çağrılamaz")
        return f(*[degerlendir(a, o) for a in e[2]])
    if k == "indeks":
        return degerlendir(e[1], o)[degerlendir(e[2], o)]
    if k == "dilim":
        n = degerlendir(e[1], o)
        bas = None if e[2] is None else degerlendir(e[2], o)
        son = None if e[3] is None else degerlendir(e[3], o)
        return n[bas:son]
    if k == "ozellik":
        return ozellik_al(degerlendir(e[1], o), e[2])
    if k == "liste":
        return [degerlendir(x, o) for x in e[1]]
    if k == "sozluk":
        return {degerlendir(a, o): degerlendir(b, o) for a, b in e[1]}
    raise HakHata(f"Bilinmeyen ifade türü: {k}")


def calistir_blok(govde, o):
    for d in govde:
        calistir(d, o)


def calistir(d, o):
    try:
        _calistir(d, o)
    except HakHata as h:
        if h.satir is None:
            h.satir = d[1]
        raise
    except ZeroDivisionError:
        raise HakHata("Sıfıra bölme yapılamaz", d[1])
    except IndexError:
        raise HakHata("İndeks liste/metin sınırları dışında", d[1])
    except KeyError as ke:
        raise HakHata(f"Sözlükte anahtar yok: {temsil(ke.args[0])}", d[1])
    except RecursionError:
        raise HakHata("Çok derin özyineleme", d[1])
    except TypeError as te:
        raise HakHata(f"Tür uyumsuzluğu ({te})", d[1])
    except ValueError as ve:
        raise HakHata(f"Geçersiz değer ({ve})", d[1])


def _calistir(d, o):
    k = d[0]
    if k == "ifade":
        degerlendir(d[2], o)
    elif k == "ata":
        _, _, hedef, op, ifade = d
        deger = degerlendir(ifade, o)
        if op != "=":
            mevcut = degerlendir(hedef, o)
            deger = IKILI[op[0]](mevcut, deger)
        if hedef[0] == "ad":
            o.d[hedef[1]] = deger
        else:
            degerlendir(hedef[1], o)[degerlendir(hedef[2], o)] = deger
    elif k == "eger":
        for kosul, govde in d[2]:
            if degerlendir(kosul, o):
                calistir_blok(govde, o)
                return
        if d[3] is not None:
            calistir_blok(d[3], o)
    elif k == "iken":
        while degerlendir(d[2], o):
            try:
                calistir_blok(d[3], o)
            except Kir:
                break
            except Devam:
                continue
    elif k == "icin":
        for x in list(degerlendir(d[3], o)):
            o.d[d[2]] = x
            try:
                calistir_blok(d[4], o)
            except Kir:
                break
            except Devam:
                continue
    elif k == "fonk":
        o.d[d[2]] = Fonk(d[2], d[3], d[4], o)
    elif k == "dondur":
        raise Dondur(None if d[2] is None else degerlendir(d[2], o))
    elif k == "kir":
        raise Kir()
    elif k == "devam":
        raise Devam()
    elif k == "gec":
        pass


def genel_ortam():
    o = Ortam()
    o.d.update(YERLESIK)
    return o


def calistir_kaynak(kaynak, ortam=None, yankila=False):
    ortam = ortam or genel_ortam()
    agac = Ayristirici(tokenize(kaynak)).program()
    for d in agac:
        if yankila and d[0] == "ifade":
            try:
                v = degerlendir(d[2], ortam)
            except HakHata as h:
                h.satir = h.satir or d[1]
                raise
            if v is not None:
                print(temsil(v))
        else:
            calistir(d, ortam)
    return ortam


def repl():
    print(f"HakDil {SURUM} — çıkmak için 'çık' yazın.")
    ortam = genel_ortam()
    while True:
        try:
            satir = input(">>> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if satir.strip() == "çık":
            break
        kaynak = satir
        if satir.rstrip().endswith(":"):
            while True:
                try:
                    ek = input("... ")
                except EOFError:
                    break
                if not ek.strip():
                    break
                kaynak += "\n" + ek
        try:
            calistir_kaynak(kaynak, ortam, yankila=True)
        except HakHata as h:
            print(h)
        except (Dondur, Kir, Devam):
            print("Hata: 'döndür/kır/devam' yalnızca uygun blok içinde kullanılır")


def main():
    if len(sys.argv) < 2:
        repl()
        return
    yol = sys.argv[1]
    try:
        with open(yol, encoding="utf-8") as f:
            kaynak = f.read()
    except OSError:
        print(f"Dosya açılamadı: {yol}", file=sys.stderr)
        sys.exit(1)
    try:
        calistir_kaynak(kaynak)
    except HakHata as h:
        print(h, file=sys.stderr)
        sys.exit(1)
    except (Dondur, Kir, Devam):
        print("Hata: 'döndür/kır/devam' yalnızca uygun blok içinde kullanılır", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

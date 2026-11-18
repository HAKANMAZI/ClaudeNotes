/* HakDil çalışma zamanı kütüphanesi (v2)
 * Derlenen her HakDil programı bu kütüphaneyle bağlanır.
 * Değer gösterimi (64 bit):
 *   ...1  -> tam sayı (63 bit, kutusuz, çok hızlı)
 *   0     -> boş,  2 -> yanlış,  4 -> doğru
 *   diğer -> yığındaki nesneye işaretçi (ondalık, metin, liste, sözlük)
 */
#define __USE_MINGW_ANSI_STDIO 1
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>
#include <math.h>
#ifdef _WIN32
#include <windows.h>
#endif

typedef intptr_t V;
#undef V_NONE
#define V_NONE ((V)0)
#define V_FALSE ((V)2)
#define V_TRUE ((V)4)
#define ISINT(v) ((v) & 1)
#define IVAL(v) ((int64_t)(v) >> 1)
#define V_NOTFOUND ((V)6) /* hiçbir geçerli değerle çakışmaz */
#define BOOLV(c) ((c) ? V_TRUE : V_FALSE)
#define HK_IMAX ((int64_t)(((uint64_t)1 << 62) - 1))
#define HK_IMIN (-HK_IMAX - 1)

enum { T_NONE, T_BOOL, T_INT, T_FLT, T_STR, T_LIST, T_DICT };
typedef struct { int64_t t; double d; } Flt;
typedef struct { int64_t t; int64_t len; int64_t nch; uint64_t h; char s[]; } Str;
typedef struct { int64_t t; int64_t len, cap; V *a; } List;   /* düzen derleyiciyle ortak: len@8, a@24 */
typedef struct { int64_t t; int64_t len, cap; V *k, *v; int64_t *ix; int64_t icap; } Dict;

int hk_line;

static void err(const char *fmt, ...) {
    fflush(stdout);
    fprintf(stderr, "Hata (satır %d): ", hk_line);
    va_list ap;
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
    fputc('\n', stderr);
    exit(1);
}

static void *xmalloc(size_t n) {
    void *p = malloc(n ? n : 1);
    if (!p) err("Bellek yetersiz");
    return p;
}
static void *xrealloc(void *p, size_t n) {
    p = realloc(p, n ? n : 1);
    if (!p) err("Bellek yetersiz");
    return p;
}

static int typ(V v) {
    if (v == V_NONE) return T_NONE;
    if (v == V_FALSE || v == V_TRUE) return T_BOOL;
    if (ISINT(v)) return T_INT;
    return (int)((int64_t *)v)[0];
}
#define AS_F(v) ((Flt *)(v))
#define AS_S(v) ((Str *)(v))
#define AS_L(v) ((List *)(v))
#define AS_D(v) ((Dict *)(v))

static const char *tn(V v) {
    static const char *n[] = {"boş", "mantıksal", "tam_sayı", "ondalık", "metin", "liste", "sözlük"};
    return n[typ(v)];
}

static V mkflt(double d) {
    Flt *f = xmalloc(sizeof *f);
    f->t = T_FLT;
    f->d = d;
    return (V)f;
}
static V mkint(int64_t i) {
    if (i > HK_IMAX || i < HK_IMIN) return mkflt((double)i);
    return (V)(((uint64_t)i << 1) | 1);
}

/* ---------------- metin ---------------- */
static int64_t u8count(const char *s, int64_t n) {
    int64_t c = 0;
    for (int64_t i = 0; i < n; i++)
        if ((s[i] & 0xC0) != 0x80) c++;
    return c;
}
static Str *mkstr_raw(int64_t len) {
    Str *s = xmalloc(sizeof(Str) + len + 1);
    s->t = T_STR;
    s->len = len;
    s->nch = -1;
    s->h = 0;
    s->s[len] = 0;
    return s;
}
static V mkstr(const char *p, int64_t len) {
    Str *s = mkstr_raw(len);
    memcpy(s->s, p, len);
    return (V)s;
}
static V mkcstr(const char *p) { return mkstr(p, strlen(p)); }
static int64_t nch(Str *s) {
    if (s->nch < 0) s->nch = u8count(s->s, s->len);
    return s->nch;
}
static int64_t u8off(Str *s, int64_t ci) {
    if (nch(s) == s->len) return ci;
    int64_t c = 0, i = 0;
    while (i < s->len) {
        if (c == ci) return i;
        i++;
        while (i < s->len && (s->s[i] & 0xC0) == 0x80) i++;
        c++;
    }
    return s->len;
}
static int64_t bfind(const char *h, int64_t hn, const char *nd, int64_t nn, int64_t from) {
    if (nn == 0) return from <= hn ? from : -1;
    for (int64_t i = from; i + nn <= hn; i++)
        if (h[i] == nd[0] && memcmp(h + i, nd, nn) == 0) return i;
    return -1;
}

V hk_str_new(const char *p, int64_t len) { return mkstr(p, len); }
V hk_flt_bits(uint64_t b) {
    double d;
    memcpy(&d, &b, 8);
    return mkflt(d);
}

/* ---------------- tampon ---------------- */
typedef struct { char *p; int64_t n, cap; } Buf;
static void bput(Buf *b, const char *s, int64_t n) {
    if (b->n + n + 1 > b->cap) {
        b->cap = (b->n + n + 1) * 2;
        b->p = xrealloc(b->p, b->cap);
    }
    memcpy(b->p + b->n, s, n);
    b->n += n;
    b->p[b->n] = 0;
}
static void bputs(Buf *b, const char *s) { bput(b, s, strlen(s)); }
static void bputc(Buf *b, char c) { bput(b, &c, 1); }

/* ---------------- liste ---------------- */
static List *mklist(int64_t cap) {
    List *l = xmalloc(sizeof *l);
    l->t = T_LIST;
    l->len = 0;
    l->cap = cap < 4 ? 4 : cap;
    l->a = xmalloc(sizeof(V) * l->cap);
    return l;
}
static void lpush(List *l, V v) {
    if (l->len == l->cap) {
        l->cap *= 2;
        l->a = xrealloc(l->a, sizeof(V) * l->cap);
    }
    l->a[l->len++] = v;
}
V hk_list_new(void) { return (V)mklist(4); }
void hk_list_push(V l, V v) { lpush(AS_L(l), v); }

/* ---------------- yazdırma ---------------- */
static void fmtflt(char *b, double d) {
    if (isnan(d)) { strcpy(b, "nan"); return; }
    if (isinf(d)) { strcpy(b, d > 0 ? "sonsuz" : "-sonsuz"); return; }
    for (int p = 1; p <= 17; p++) {
        snprintf(b, 40, "%.*g", p, d);
        if (strtod(b, NULL) == d) break;
    }
    if (!strpbrk(b, ".e")) strcat(b, ".0");
}
static void show(Buf *b, V v, int repr) {
    char t[48];
    switch (typ(v)) {
    case T_NONE: bputs(b, "boş"); break;
    case T_BOOL: bputs(b, v == V_TRUE ? "doğru" : "yanlış"); break;
    case T_INT: snprintf(t, sizeof t, "%lld", (long long)IVAL(v)); bputs(b, t); break;
    case T_FLT: fmtflt(t, AS_F(v)->d); bputs(b, t); break;
    case T_STR:
        if (repr) bputc(b, '"');
        bput(b, AS_S(v)->s, AS_S(v)->len);
        if (repr) bputc(b, '"');
        break;
    case T_LIST: {
        List *l = AS_L(v);
        bputc(b, '[');
        for (int64_t i = 0; i < l->len; i++) {
            if (i) bputs(b, ", ");
            show(b, l->a[i], 1);
        }
        bputc(b, ']');
        break;
    }
    case T_DICT: {
        Dict *d = AS_D(v);
        bputc(b, '{');
        for (int64_t i = 0; i < d->len; i++) {
            if (i) bputs(b, ", ");
            show(b, d->k[i], 1);
            bputs(b, ": ");
            show(b, d->v[i], 1);
        }
        bputc(b, '}');
        break;
    }
    }
}
static V tostr(V v) {
    if (typ(v) == T_STR) return v;
    Buf b = {0};
    show(&b, v, 0);
    V r = mkstr(b.p, b.n);
    free(b.p);
    return r;
}
static const char *reprc(V v) {
    Buf b = {0};
    show(&b, v, 1);
    return b.p;
}

/* ---------------- eşitlik / özet ---------------- */
static int isnum(V v) { return ISINT(v) || (v > 4 && typ(v) == T_FLT); }
static double num(V v) { return ISINT(v) ? (double)IVAL(v) : AS_F(v)->d; }

static int dhas(Dict *d, V k);
static int64_t dfind(Dict *d, V k);
static int eq(V a, V b) {
    if (a == b) return typ(a) != T_FLT || AS_F(a)->d == AS_F(a)->d;
    if (isnum(a) && isnum(b)) {
        if (ISINT(a) && ISINT(b)) return 0;
        return num(a) == num(b);
    }
    int ta = typ(a), tb = typ(b);
    if (ta != tb) return 0;
    if (ta == T_STR) return AS_S(a)->len == AS_S(b)->len && memcmp(AS_S(a)->s, AS_S(b)->s, AS_S(a)->len) == 0;
    if (ta == T_LIST) {
        List *x = AS_L(a), *y = AS_L(b);
        if (x->len != y->len) return 0;
        for (int64_t i = 0; i < x->len; i++)
            if (!eq(x->a[i], y->a[i])) return 0;
        return 1;
    }
    if (ta == T_DICT) {
        Dict *x = AS_D(a), *y = AS_D(b);
        if (x->len != y->len) return 0;
        for (int64_t i = 0; i < x->len; i++) {
            int64_t e = dfind(y, x->k[i]);
            if (e < 0 || !eq(x->v[i], y->v[e])) return 0;
        }
        return 1;
    }
    return 0;
}
static uint64_t hash(V v) {
    switch (typ(v)) {
    case T_NONE: return 7;
    case T_BOOL: return v;
    case T_INT: return (uint64_t)IVAL(v) * 0x9E3779B97F4A7C15ULL;
    case T_FLT: {
        double d = AS_F(v)->d;
        if (d == floor(d) && fabs(d) < 9e18) return (uint64_t)(int64_t)d * 0x9E3779B97F4A7C15ULL;
        uint64_t b;
        memcpy(&b, &d, 8);
        return b * 0x9E3779B97F4A7C15ULL;
    }
    case T_STR: {
        Str *s = AS_S(v);
        if (!s->h) {
            uint64_t h = 1469598103934665603ULL;
            for (int64_t i = 0; i < s->len; i++) h = (h ^ (unsigned char)s->s[i]) * 1099511628211ULL;
            s->h = h | 1;
        }
        return s->h;
    }
    default: err("%s sözlük anahtarı olamaz", tn(v));
    }
    return 0;
}

/* ---------------- sözlük ---------------- */
static Dict *mkdict(void) {
    Dict *d = xmalloc(sizeof *d);
    d->t = T_DICT;
    d->len = 0;
    d->cap = 4;
    d->k = xmalloc(sizeof(V) * 4);
    d->v = xmalloc(sizeof(V) * 4);
    d->icap = 8;
    d->ix = calloc(8, sizeof(int64_t));
    return d;
}
static int64_t dfind(Dict *d, V k) {
    int64_t m = d->icap - 1;
    for (int64_t i = hash(k) & m;; i = (i + 1) & m) {
        int64_t e = d->ix[i];
        if (!e) return -1;
        if (eq(d->k[e - 1], k)) return e - 1;
    }
}
static int dhas(Dict *d, V k) { return dfind(d, k) >= 0; }
static void dslot(Dict *d, int64_t e) {
    int64_t m = d->icap - 1;
    int64_t i = hash(d->k[e]) & m;
    while (d->ix[i]) i = (i + 1) & m;
    d->ix[i] = e + 1;
}
static void dreindex(Dict *d) {
    while (d->icap < d->len * 2 + 2) d->icap *= 2;
    free(d->ix);
    d->ix = calloc(d->icap, sizeof(int64_t));
    if (!d->ix) err("Bellek yetersiz");
    for (int64_t e = 0; e < d->len; e++) dslot(d, e);
}
static void dset(Dict *d, V k, V v) {
    int64_t e = dfind(d, k);
    if (e >= 0) { d->v[e] = v; return; }
    if (d->len == d->cap) {
        d->cap *= 2;
        d->k = xrealloc(d->k, sizeof(V) * d->cap);
        d->v = xrealloc(d->v, sizeof(V) * d->cap);
    }
    d->k[d->len] = k;
    d->v[d->len] = v;
    d->len++;
    if (d->len * 2 > d->icap) dreindex(d);
    else dslot(d, d->len - 1);
}
static void ddel(Dict *d, int64_t e) {
    memmove(d->k + e, d->k + e + 1, sizeof(V) * (d->len - e - 1));
    memmove(d->v + e, d->v + e + 1, sizeof(V) * (d->len - e - 1));
    d->len--;
    dreindex(d);
}
V hk_dict_new(void) { return (V)mkdict(); }
void hk_dict_set(V d, V k, V v) { dset(AS_D(d), k, v); }

/* ---------------- aritmetik ---------------- */
V hk_add(V a, V b) {
    if (ISINT(a) && ISINT(b)) return mkint(IVAL(a) + IVAL(b));
    if (isnum(a) && isnum(b)) return mkflt(num(a) + num(b));
    int ta = typ(a), tb = typ(b);
    if (ta == T_STR || tb == T_STR) {
        Str *x = AS_S(tostr(a)), *y = AS_S(tostr(b));
        Str *r = mkstr_raw(x->len + y->len);
        memcpy(r->s, x->s, x->len);
        memcpy(r->s + x->len, y->s, y->len);
        return (V)r;
    }
    if (ta == T_LIST && tb == T_LIST) {
        List *x = AS_L(a), *y = AS_L(b), *r = mklist(x->len + y->len);
        memcpy(r->a, x->a, sizeof(V) * x->len);
        memcpy(r->a + x->len, y->a, sizeof(V) * y->len);
        r->len = x->len + y->len;
        return (V)r;
    }
    err("'+' işlemi %s ve %s ile yapılamaz", tn(a), tn(b));
    return 0;
}
V hk_sub(V a, V b) {
    if (ISINT(a) && ISINT(b)) return mkint(IVAL(a) - IVAL(b));
    if (isnum(a) && isnum(b)) return mkflt(num(a) - num(b));
    err("'-' işlemi %s ve %s ile yapılamaz", tn(a), tn(b));
    return 0;
}
static V repeat(V s, int64_t k) {
    if (k < 0) k = 0;
    if (typ(s) == T_STR) {
        Str *x = AS_S(s), *r = mkstr_raw(x->len * k);
        for (int64_t i = 0; i < k; i++) memcpy(r->s + i * x->len, x->s, x->len);
        return (V)r;
    }
    List *x = AS_L(s), *r = mklist(x->len * k);
    for (int64_t i = 0; i < k; i++)
        for (int64_t j = 0; j < x->len; j++) lpush(r, x->a[j]);
    return (V)r;
}
V hk_mul(V a, V b) {
    if (ISINT(a) && ISINT(b)) {
        int64_t r;
        if (__builtin_mul_overflow(IVAL(a), IVAL(b), &r)) return mkflt((double)IVAL(a) * (double)IVAL(b));
        return mkint(r);
    }
    if (isnum(a) && isnum(b)) return mkflt(num(a) * num(b));
    int ta = typ(a), tb = typ(b);
    if ((ta == T_STR || ta == T_LIST) && tb == T_INT) return repeat(a, IVAL(b));
    if ((tb == T_STR || tb == T_LIST) && ta == T_INT) return repeat(b, IVAL(a));
    err("'*' işlemi %s ve %s ile yapılamaz", tn(a), tn(b));
    return 0;
}
static void numcheck(V a, V b, const char *op) {
    if (!isnum(a) || !isnum(b)) err("'%s' işlemi %s ve %s ile yapılamaz", op, tn(a), tn(b));
}
V hk_div(V a, V b) {
    numcheck(a, b, "/");
    if (num(b) == 0) err("Sıfıra bölme yapılamaz");
    if (ISINT(a) && ISINT(b) && IVAL(a) % IVAL(b) == 0) return mkint(IVAL(a) / IVAL(b));
    return mkflt(num(a) / num(b));
}
V hk_fdiv(V a, V b) {
    numcheck(a, b, "//");
    if (num(b) == 0) err("Sıfıra bölme yapılamaz");
    if (ISINT(a) && ISINT(b)) {
        int64_t x = IVAL(a), y = IVAL(b), q = x / y;
        if ((x % y != 0) && ((x < 0) != (y < 0))) q--;
        return mkint(q);
    }
    return mkflt(floor(num(a) / num(b)));
}
V hk_mod(V a, V b) {
    numcheck(a, b, "%");
    if (num(b) == 0) err("Sıfıra bölme yapılamaz");
    if (ISINT(a) && ISINT(b)) {
        int64_t x = IVAL(a), y = IVAL(b), r = x % y;
        if (r != 0 && ((r < 0) != (y < 0))) r += y;
        return mkint(r);
    }
    double x = num(a), y = num(b), r = fmod(x, y);
    if (r != 0 && ((r < 0) != (y < 0))) r += y;
    return mkflt(r);
}
V hk_pow(V a, V b) {
    numcheck(a, b, "**");
    if (ISINT(a) && ISINT(b) && IVAL(b) >= 0) {
        int64_t base = IVAL(a), e = IVAL(b), r = 1;
        while (e) {
            if (e & 1)
                if (__builtin_mul_overflow(r, base, &r)) return mkflt(pow(num(a), num(b)));
            e >>= 1;
            if (e && __builtin_mul_overflow(base, base, &base)) return mkflt(pow(num(a), num(b)));
        }
        return mkint(r);
    }
    return mkflt(pow(num(a), num(b)));
}
V hk_neg(V a) {
    if (ISINT(a)) return mkint(-IVAL(a));
    if (isnum(a)) return mkflt(-num(a));
    err("%s eksi yapılamaz", tn(a));
    return 0;
}

/* ---------------- karşılaştırma ---------------- */
static int cmp(V a, V b) {
    if (isnum(a) && isnum(b)) {
        double x = num(a), y = num(b);
        if (ISINT(a) && ISINT(b)) return IVAL(a) < IVAL(b) ? -1 : IVAL(a) > IVAL(b);
        return x < y ? -1 : x > y;
    }
    int ta = typ(a), tb = typ(b);
    if (ta == T_STR && tb == T_STR) {
        Str *x = AS_S(a), *y = AS_S(b);
        int64_t n = x->len < y->len ? x->len : y->len;
        int c = memcmp(x->s, y->s, n);
        if (c) return c < 0 ? -1 : 1;
        return x->len < y->len ? -1 : x->len > y->len;
    }
    if (ta == T_LIST && tb == T_LIST) {
        List *x = AS_L(a), *y = AS_L(b);
        for (int64_t i = 0; i < x->len && i < y->len; i++) {
            int c = cmp(x->a[i], y->a[i]);
            if (c) return c;
        }
        return x->len < y->len ? -1 : x->len > y->len;
    }
    err("%s ile %s karşılaştırılamaz", tn(a), tn(b));
    return 0;
}
V hk_lt(V a, V b) { return BOOLV(cmp(a, b) < 0); }
V hk_gt(V a, V b) { return BOOLV(cmp(a, b) > 0); }
V hk_le(V a, V b) { return BOOLV(cmp(a, b) <= 0); }
V hk_ge(V a, V b) { return BOOLV(cmp(a, b) >= 0); }
V hk_eq(V a, V b) { return BOOLV(eq(a, b)); }
V hk_ne(V a, V b) { return BOOLV(!eq(a, b)); }

V hk_contains(V c, V x) {
    switch (typ(c)) {
    case T_STR:
        if (typ(x) != T_STR) err("metin içinde yalnızca metin aranabilir");
        return BOOLV(bfind(AS_S(c)->s, AS_S(c)->len, AS_S(x)->s, AS_S(x)->len, 0) >= 0);
    case T_LIST:
        for (int64_t i = 0; i < AS_L(c)->len; i++)
            if (eq(AS_L(c)->a[i], x)) return V_TRUE;
        return V_FALSE;
    case T_DICT: return BOOLV(dhas(AS_D(c), x));
    }
    err("%s içinde arama yapılamaz", tn(c));
    return 0;
}

int64_t hk_truthy(V v) {
    switch (typ(v)) {
    case T_NONE: return 0;
    case T_BOOL: return v == V_TRUE;
    case T_INT: return IVAL(v) != 0;
    case T_FLT: return AS_F(v)->d != 0;
    case T_STR: return AS_S(v)->len != 0;
    case T_LIST: return AS_L(v)->len != 0;
    case T_DICT: return AS_D(v)->len != 0;
    }
    return V_NOTFOUND;
}

/* ---------------- indeksleme ---------------- */
static int64_t idxv(V i) {
    if (!ISINT(i)) err("İndeks tam sayı olmalı, %s verildi", tn(i));
    return IVAL(i);
}
static int64_t norm(int64_t j, int64_t n) {
    if (j < 0) j += n;
    if (j < 0 || j >= n) err("İndeks sınırların dışında");
    return j;
}
static V strchar(Str *s, int64_t j) {
    int64_t a = u8off(s, j), b = a + 1;
    while (b < s->len && (s->s[b] & 0xC0) == 0x80) b++;
    return mkstr(s->s + a, b - a);
}
V hk_index(V o, V i) {
    switch (typ(o)) {
    case T_LIST: return AS_L(o)->a[norm(idxv(i), AS_L(o)->len)];
    case T_STR: return strchar(AS_S(o), norm(idxv(i), nch(AS_S(o))));
    case T_DICT: {
        int64_t e = dfind(AS_D(o), i);
        if (e < 0) err("Sözlükte anahtar yok: %s", reprc(i));
        return AS_D(o)->v[e];
    }
    }
    err("%s indekslenemez", tn(o));
    return 0;
}
V hk_setindex(V o, V i, V v) {
    if (typ(o) == T_LIST) AS_L(o)->a[norm(idxv(i), AS_L(o)->len)] = v;
    else if (typ(o) == T_DICT) dset(AS_D(o), i, v);
    else err("%s içine atama yapılamaz", tn(o));
    return V_NONE;
}
static int64_t clampi(V v, int64_t def, int64_t n) {
    if (v == V_NONE) return def;
    int64_t j = idxv(v);
    if (j < 0) j += n;
    if (j < 0) j = 0;
    if (j > n) j = n;
    return j;
}
V hk_slice(V o, V a, V b) {
    int t = typ(o);
    if (t == T_LIST) {
        int64_t n = AS_L(o)->len, x = clampi(a, 0, n), y = clampi(b, n, n);
        List *r = mklist(y > x ? y - x : 0);
        for (int64_t i = x; i < y; i++) lpush(r, AS_L(o)->a[i]);
        return (V)r;
    }
    if (t == T_STR) {
        Str *s = AS_S(o);
        int64_t n = nch(s), x = clampi(a, 0, n), y = clampi(b, n, n);
        if (y <= x) return mkstr("", 0);
        int64_t bx = u8off(s, x), by = u8off(s, y);
        return mkstr(s->s + bx, by - bx);
    }
    err("%s dilimlenemez", tn(o));
    return 0;
}

/* ---------------- döngü yardımcıları ---------------- */
static List *listof(V v) {
    switch (typ(v)) {
    case T_LIST: {
        List *r = mklist(AS_L(v)->len);
        memcpy(r->a, AS_L(v)->a, sizeof(V) * AS_L(v)->len);
        r->len = AS_L(v)->len;
        return r;
    }
    case T_STR: {
        Str *s = AS_S(v);
        List *r = mklist(nch(s));
        for (int64_t i = 0; i < s->len;) {
            int64_t j = i + 1;
            while (j < s->len && (s->s[j] & 0xC0) == 0x80) j++;
            lpush(r, mkstr(s->s + i, j - i));
            i = j;
        }
        return r;
    }
    case T_DICT: {
        List *r = mklist(AS_D(v)->len);
        for (int64_t i = 0; i < AS_D(v)->len; i++) lpush(r, AS_D(v)->k[i]);
        return r;
    }
    }
    err("%s üzerinde dönülemez", tn(v));
    return 0;
}
V hk_iter(V v) { return (V)listof(v); }
V hk_check_int(V v) {
    if (!ISINT(v)) err("aralık tam sayı ister, %s verildi", tn(v));
    return v;
}
V hk_check_step(V v) {
    hk_check_int(v);
    if (IVAL(v) == 0) err("aralık adımı sıfır olamaz");
    return v;
}

/* ---------------- sıralama ---------------- */
static void msort(V *a, V *t, int64_t n) {
    if (n < 2) return;
    int64_t m = n / 2;
    msort(a, t, m);
    msort(a + m, t, n - m);
    int64_t i = 0, j = m, k = 0;
    while (i < m && j < n) t[k++] = cmp(a[j], a[i]) < 0 ? a[j++] : a[i++];
    while (i < m) t[k++] = a[i++];
    while (j < n) t[k++] = a[j++];
    memcpy(a, t, sizeof(V) * n);
}
static void lsort(List *l) {
    V *t = xmalloc(sizeof(V) * (l->len + 1));
    msort(l->a, t, l->len);
    free(t);
}

/* ---------------- Türkçe büyük/küçük harf ---------------- */
static int u8dec(const unsigned char *s, int64_t n, int64_t *i) {
    unsigned c = s[(*i)++];
    if (c < 0x80) return c;
    int k = c >= 0xF0 ? 3 : c >= 0xE0 ? 2 : 1;
    c &= 0x3F >> k;
    while (k-- && *i < n) c = (c << 6) | (s[(*i)++] & 0x3F);
    return c;
}
static void u8enc(Buf *b, int c) {
    char t[4];
    int n;
    if (c < 0x80) { t[0] = c; n = 1; }
    else if (c < 0x800) { t[0] = 0xC0 | c >> 6; t[1] = 0x80 | (c & 63); n = 2; }
    else if (c < 0x10000) { t[0] = 0xE0 | c >> 12; t[1] = 0x80 | (c >> 6 & 63); t[2] = 0x80 | (c & 63); n = 3; }
    else { t[0] = 0xF0 | c >> 18; t[1] = 0x80 | (c >> 12 & 63); t[2] = 0x80 | (c >> 6 & 63); t[3] = 0x80 | (c & 63); n = 4; }
    bput(b, t, n);
}
static int tr_up(int c) {
    if (c == 'i') return 0x130;
    if (c == 0x131) return 'I';
    if (c >= 'a' && c <= 'z') return c - 32;
    if (c >= 0xE0 && c <= 0xFE && c != 0xF7) return c - 32;
    if (c == 0x11F || c == 0x15F) return c - 1;
    return c;
}
static int tr_low(int c) {
    if (c == 'I') return 0x131;
    if (c == 0x130) return 'i';
    if (c >= 'A' && c <= 'Z') return c + 32;
    if (c >= 0xC0 && c <= 0xDE && c != 0xD7) return c + 32;
    if (c == 0x11E || c == 0x15E) return c + 1;
    return c;
}
static V casemap(Str *s, int up) {
    Buf b = {0};
    int64_t i = 0;
    while (i < s->len) u8enc(&b, (up ? tr_up : tr_low)(u8dec((unsigned char *)s->s, s->len, &i)));
    V r = mkstr(b.p ? b.p : "", b.n);
    free(b.p);
    return r;
}

/* ---------------- hazır fonksiyonlar ---------------- */
#define ARG(i) p[n - 1 - (i)]
static void argn(const char *ad, int64_t n, int lo, int hi) {
    if (n < lo || n > hi) {
        if (lo == hi) err("'%s' %d değer bekliyor, %lld verildi", ad, lo, (long long)n);
        err("'%s' %d ile %d arası değer bekliyor, %lld verildi", ad, lo, hi, (long long)n);
    }
}
static V readline_v(void) {
    Buf b = {0};
    int c;
    while ((c = getchar()) != EOF && c != '\n') bputc(&b, (char)c);
    if (b.n && b.p[b.n - 1] == '\r') b.n--;
    V r = mkstr(b.p ? b.p : "", b.n);
    free(b.p);
    return r;
}
static V parse_int(V x) {
    switch (typ(x)) {
    case T_INT: return x;
    case T_BOOL: return mkint(x == V_TRUE);
    case T_FLT: return mkint((int64_t)AS_F(x)->d);
    case T_STR: {
        char *e;
        const char *s = AS_S(x)->s;
        long long v = strtoll(s, &e, 10);
        while (*e == ' ' || *e == '\t' || *e == '\r' || *e == '\n') e++;
        if (e == s || *e) err("Sayıya çevrilemedi: %s", reprc(x));
        return mkint(v);
    }
    }
    err("%s sayıya çevrilemez", tn(x));
    return 0;
}
static V parse_flt(V x) {
    if (isnum(x)) return mkflt(num(x));
    if (typ(x) == T_STR) {
        char *t = strdup(AS_S(x)->s), *e;
        for (char *q = t; *q; q++)
            if (*q == ',') *q = '.';
        double d = strtod(t, &e);
        while (*e == ' ' || *e == '\t' || *e == '\r' || *e == '\n') e++;
        int bad = (e == t || *e);
        free(t);
        if (bad) err("Ondalığa çevrilemedi: %s", reprc(x));
        return mkflt(d);
    }
    err("%s ondalığa çevrilemez", tn(x));
    return 0;
}
static V minmax(V *p, int64_t n, int big, const char *ad) {
    V *a = p;
    int64_t m = n, rev = 1;
    if (n == 1) {
        List *l = listof(ARG(0));
        a = l->a;
        m = l->len;
        rev = 0;
    }
    if (m == 0) err("'%s' boş listeyle kullanılamaz", ad);
    V best = a[0];
    for (int64_t i = 1; i < m; i++) {
        int c = cmp(a[i], best);
        if (big ? c > 0 : c < 0) best = a[i];
    }
    (void)rev;
    return best;
}

V hk_builtin(int64_t id, V *p, int64_t n) {
    switch (id) {
    case 0: { /* yazdır */
        Buf b = {0};
        for (int64_t i = 0; i < n; i++) {
            if (i) bputc(&b, ' ');
            show(&b, ARG(i), 0);
        }
        bputc(&b, '\n');
        fwrite(b.p, 1, b.n, stdout);
        free(b.p);
        return V_NONE;
    }
    case 1: /* girdi */
        argn("girdi", n, 0, 1);
        if (n) {
            Str *s = AS_S(tostr(ARG(0)));
            fwrite(s->s, 1, s->len, stdout);
        }
        fflush(stdout);
        return readline_v();
    case 2: { /* uzunluk */
        argn("uzunluk", n, 1, 1);
        V x = ARG(0);
        switch (typ(x)) {
        case T_STR: return mkint(nch(AS_S(x)));
        case T_LIST: return mkint(AS_L(x)->len);
        case T_DICT: return mkint(AS_D(x)->len);
        }
        err("%s için uzunluk alınamaz", tn(x));
    }
    case 3: { /* aralık */
        argn("aralık", n, 1, 3);
        int64_t a = 0, b, s = 1;
        if (n == 1) b = IVAL(hk_check_int(ARG(0)));
        else {
            a = IVAL(hk_check_int(ARG(0)));
            b = IVAL(hk_check_int(ARG(1)));
            if (n == 3) s = IVAL(hk_check_step(ARG(2)));
        }
        List *l = mklist(4);
        for (int64_t i = a; s > 0 ? i < b : i > b; i += s) lpush(l, mkint(i));
        return (V)l;
    }
    case 4: argn("sayı", n, 1, 1); return parse_int(ARG(0));
    case 5: argn("ondalık", n, 1, 1); return parse_flt(ARG(0));
    case 6: argn("metin", n, 1, 1); return tostr(ARG(0));
    case 7: argn("liste", n, 0, 1); return n ? (V)listof(ARG(0)) : (V)mklist(4);
    case 8: argn("tür", n, 1, 1); return mkcstr(tn(ARG(0)));
    case 9: { /* toplam */
        argn("toplam", n, 1, 1);
        List *l = listof(ARG(0));
        V acc = mkint(0);
        for (int64_t i = 0; i < l->len; i++) acc = hk_add(acc, l->a[i]);
        return acc;
    }
    case 10: if (!n) argn("en_büyük", n, 1, 99); return minmax(p, n, 1, "en_büyük");
    case 11: if (!n) argn("en_küçük", n, 1, 99); return minmax(p, n, 0, "en_küçük");
    case 12: { /* yuvarla */
        argn("yuvarla", n, 1, 2);
        V x = ARG(0);
        if (!isnum(x)) err("%s yuvarlanamaz", tn(x));
        if (n == 1) return ISINT(x) ? x : mkint((int64_t)nearbyint(num(x)));
        double k = pow(10, (double)IVAL(hk_check_int(ARG(1))));
        return mkflt(nearbyint(num(x) * k) / k);
    }
    case 13: { /* mutlak */
        argn("mutlak", n, 1, 1);
        V x = ARG(0);
        if (ISINT(x)) return mkint(IVAL(x) < 0 ? -IVAL(x) : IVAL(x));
        if (isnum(x)) return mkflt(fabs(num(x)));
        err("%s için mutlak değer alınamaz", tn(x));
    }
    case 14: { /* sıralı */
        argn("sıralı", n, 1, 1);
        List *l = listof(ARG(0));
        lsort(l);
        return (V)l;
    }
    }
    err("Bilinmeyen hazır fonksiyon");
    return 0;
}

/* ---------------- metotlar ---------------- */
#define IS(s) (strcmp(name, s) == 0)
static Str *needstr(V v, const char *ad) {
    if (typ(v) != T_STR) err("'%s' metin bekliyor, %s verildi", ad, tn(v));
    return AS_S(v);
}
static int isws(char c) { return c == ' ' || c == '\t' || c == '\n' || c == '\r'; }

static V str_method(Str *s, const char *name, V *p, int64_t n) {
    if (IS("büyük") || IS("küçük")) { argn(name, n, 0, 0); return casemap(s, IS("büyük")); }
    if (IS("kırp")) {
        argn(name, n, 0, 0);
        int64_t a = 0, b = s->len;
        while (a < b && isws(s->s[a])) a++;
        while (b > a && isws(s->s[b - 1])) b--;
        return mkstr(s->s + a, b - a);
    }
    if (IS("böl")) {
        argn(name, n, 0, 1);
        List *r = mklist(4);
        if (n == 0) {
            int64_t i = 0;
            while (i < s->len) {
                while (i < s->len && isws(s->s[i])) i++;
                int64_t j = i;
                while (j < s->len && !isws(s->s[j])) j++;
                if (j > i) lpush(r, mkstr(s->s + i, j - i));
                i = j;
            }
            return (V)r;
        }
        Str *sep = needstr(ARG(0), name);
        if (!sep->len) err("Ayraç boş olamaz");
        int64_t i = 0, j;
        while ((j = bfind(s->s, s->len, sep->s, sep->len, i)) >= 0) {
            lpush(r, mkstr(s->s + i, j - i));
            i = j + sep->len;
        }
        lpush(r, mkstr(s->s + i, s->len - i));
        return (V)r;
    }
    if (IS("değiştir")) {
        argn(name, n, 2, 2);
        Str *a = needstr(ARG(0), name), *b = needstr(ARG(1), name);
        if (!a->len) return (V)s;
        Buf o = {0};
        int64_t i = 0, j;
        while ((j = bfind(s->s, s->len, a->s, a->len, i)) >= 0) {
            bput(&o, s->s + i, j - i);
            bput(&o, b->s, b->len);
            i = j + a->len;
        }
        bput(&o, s->s + i, s->len - i);
        V r = mkstr(o.p, o.n);
        free(o.p);
        return r;
    }
    if (IS("birleştir")) {
        argn(name, n, 1, 1);
        List *l = listof(ARG(0));
        Buf o = {0};
        bput(&o, "", 0);
        for (int64_t i = 0; i < l->len; i++) {
            if (i) bput(&o, s->s, s->len);
            Str *x = AS_S(tostr(l->a[i]));
            bput(&o, x->s, x->len);
        }
        V r = mkstr(o.p, o.n);
        free(o.p);
        return r;
    }
    if (IS("başlar") || IS("biter")) {
        argn(name, n, 1, 1);
        Str *x = needstr(ARG(0), name);
        if (x->len > s->len) return V_FALSE;
        int64_t off = IS("başlar") ? 0 : s->len - x->len;
        return BOOLV(memcmp(s->s + off, x->s, x->len) == 0);
    }
    if (IS("bul")) {
        argn(name, n, 1, 1);
        Str *x = needstr(ARG(0), name);
        int64_t j = bfind(s->s, s->len, x->s, x->len, 0);
        return mkint(j < 0 ? -1 : u8count(s->s, j));
    }
    if (IS("say")) {
        argn(name, n, 1, 1);
        Str *x = needstr(ARG(0), name);
        if (!x->len) return mkint(nch(s) + 1);
        int64_t c = 0, i = 0, j;
        while ((j = bfind(s->s, s->len, x->s, x->len, i)) >= 0) { c++; i = j + x->len; }
        return mkint(c);
    }
    return V_NOTFOUND;
}

static V list_method(List *l, const char *name, V *p, int64_t n) {
    if (IS("ekle")) { argn(name, n, 1, 1); lpush(l, ARG(0)); return V_NONE; }
    if (IS("çıkar")) {
        argn(name, n, 0, 1);
        if (!l->len) err("Boş listeden çıkarılamaz");
        int64_t j = n ? norm(idxv(ARG(0)), l->len) : l->len - 1;
        V v = l->a[j];
        memmove(l->a + j, l->a + j + 1, sizeof(V) * (l->len - j - 1));
        l->len--;
        return v;
    }
    if (IS("sil")) {
        argn(name, n, 1, 1);
        for (int64_t i = 0; i < l->len; i++)
            if (eq(l->a[i], ARG(0))) {
                memmove(l->a + i, l->a + i + 1, sizeof(V) * (l->len - i - 1));
                l->len--;
                return V_NONE;
            }
        err("Listede yok: %s", reprc(ARG(0)));
    }
    if (IS("sırala")) { argn(name, n, 0, 0); lsort(l); return V_NONE; }
    if (IS("ters_çevir")) {
        argn(name, n, 0, 0);
        for (int64_t i = 0, j = l->len - 1; i < j; i++, j--) { V t = l->a[i]; l->a[i] = l->a[j]; l->a[j] = t; }
        return V_NONE;
    }
    if (IS("genişlet")) {
        argn(name, n, 1, 1);
        List *x = listof(ARG(0));
        for (int64_t i = 0; i < x->len; i++) lpush(l, x->a[i]);
        return V_NONE;
    }
    if (IS("bul")) {
        argn(name, n, 1, 1);
        for (int64_t i = 0; i < l->len; i++)
            if (eq(l->a[i], ARG(0))) return mkint(i);
        return mkint(-1);
    }
    if (IS("say")) {
        argn(name, n, 1, 1);
        int64_t c = 0;
        for (int64_t i = 0; i < l->len; i++) c += eq(l->a[i], ARG(0));
        return mkint(c);
    }
    if (IS("araya_ekle")) {
        argn(name, n, 2, 2);
        int64_t j = idxv(ARG(0));
        if (j < 0) j += l->len;
        if (j < 0) j = 0;
        if (j > l->len) j = l->len;
        lpush(l, V_NONE);
        memmove(l->a + j + 1, l->a + j, sizeof(V) * (l->len - j - 1));
        l->a[j] = ARG(1);
        return V_NONE;
    }
    if (IS("temizle")) { argn(name, n, 0, 0); l->len = 0; return V_NONE; }
    return V_NOTFOUND;
}

static V dict_method(Dict *d, const char *name, V *p, int64_t n) {
    if (IS("anahtarlar") || IS("değerler")) {
        argn(name, n, 0, 0);
        List *r = mklist(d->len);
        for (int64_t i = 0; i < d->len; i++) lpush(r, IS("anahtarlar") ? d->k[i] : d->v[i]);
        return (V)r;
    }
    if (IS("çiftler")) {
        argn(name, n, 0, 0);
        List *r = mklist(d->len);
        for (int64_t i = 0; i < d->len; i++) {
            List *c = mklist(2);
            lpush(c, d->k[i]);
            lpush(c, d->v[i]);
            lpush(r, (V)c);
        }
        return (V)r;
    }
    if (IS("al")) {
        argn(name, n, 1, 2);
        int64_t e = dfind(d, ARG(0));
        return e >= 0 ? d->v[e] : (n == 2 ? ARG(1) : V_NONE);
    }
    if (IS("sil")) {
        argn(name, n, 1, 1);
        int64_t e = dfind(d, ARG(0));
        if (e < 0) err("Sözlükte anahtar yok: %s", reprc(ARG(0)));
        V v = d->v[e];
        ddel(d, e);
        return v;
    }
    if (IS("güncelle")) {
        argn(name, n, 1, 1);
        if (typ(ARG(0)) != T_DICT) err("'güncelle' sözlük bekliyor");
        Dict *x = AS_D(ARG(0));
        for (int64_t i = 0; i < x->len; i++) dset(d, x->k[i], x->v[i]);
        return V_NONE;
    }
    if (IS("temizle")) { argn(name, n, 0, 0); d->len = 0; dreindex(d); return V_NONE; }
    return V_NOTFOUND;
}

V hk_method(V o, const char *name, V *p, int64_t n) {
    V r = V_NOTFOUND;
    switch (typ(o)) {
    case T_STR: r = str_method(AS_S(o), name, p, n); break;
    case T_LIST: r = list_method(AS_L(o), name, p, n); break;
    case T_DICT: r = dict_method(AS_D(o), name, p, n); break;
    }
    if (r == V_NOTFOUND) err("%s türünde '%s' diye bir metot yok", tn(o), name);
    return r;
}

/* ---------------- giriş noktası ---------------- */
extern V hk_main(void);
int main(void) {
#ifdef _WIN32
    SetConsoleOutputCP(65001);
    SetConsoleCP(65001);
#endif
    static char obuf[1 << 16];
    setvbuf(stdout, obuf, _IOFBF, sizeof obuf);
    hk_main();
    fflush(stdout);
    return 0;
}

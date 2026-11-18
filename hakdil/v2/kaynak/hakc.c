/* hakc — HakDil derleyicisi (v2)
 *
 * HakDil kaynak kodunu doğrudan x86-64 makine komutlarına (assembly) çevirir,
 * ardından sistemdeki assembler/bağlayıcı ile çalıştırılabilir dosya üretir.
 *
 *   kaynak (.hak) -> sözcükler -> sözdizimi ağacı -> x86-64 assembly -> .exe
 *
 * Kullanım:
 *   hakc program.hak              -> program (Windows'ta program.exe)
 *   hakc program.hak -o cikti     -> çıktı adını belirle
 *   hakc -r program.hak           -> derle ve hemen çalıştır
 *   hakc -S program.hak           -> yalnızca assembly (.s) üret
 */
#define __USE_MINGW_ANSI_STDIO 1
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdint.h>

#define SURUM "2.0"

#ifdef _WIN32
static int WIN = 1;
#else
static int WIN = 0;
#endif

static void cerr(int line, const char *fmt, ...) {
    va_list ap;
    if (line) fprintf(stderr, "Derleme hatası (satır %d): ", line);
    else fprintf(stderr, "Derleme hatası: ");
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
    fputc('\n', stderr);
    exit(1);
}
static void *xcalloc(size_t n) {
    void *p = calloc(1, n ? n : 1);
    if (!p) cerr(0, "Bellek yetersiz");
    return p;
}
static char *xstrndup(const char *s, size_t n) {
    char *p = xcalloc(n + 1);
    memcpy(p, s, n);
    return p;
}
#define VPUSH(arr, n, x) do { (arr) = realloc((arr), sizeof(*(arr)) * ((n) + 1)); (arr)[(n)++] = (x); } while (0)

/* =============================== SÖZCÜKLER =============================== */
enum { TK_INT, TK_FLT, TK_STR, TK_NAME, TK_KW, TK_OP, TK_NL, TK_IND, TK_DED, TK_EOF };
enum { KW_EGER, KW_YADA, KW_DEGILSE, KW_IKEN, KW_ICIN, KW_ICINDE, KW_FONK, KW_DONDUR, KW_KIR, KW_DEVAM,
       KW_GEC, KW_VE, KW_VEYA, KW_DEGIL, KW_DOGRU, KW_YANLIS, KW_BOS, KW_N };
static const char *KWS[KW_N] = {"eğer", "yada", "değilse", "iken", "için", "içinde", "fonk", "döndür", "kır",
                                "devam", "geç", "ve", "veya", "değil", "doğru", "yanlış", "boş"};

typedef struct { int k, line, kw, slen; char *s; int64_t i; double f; } Tok;
static Tok *toks;
static int ntok;

static void addtok(int k, int line, char *s, int slen) {
    Tok t = {0};
    t.k = k; t.line = line; t.s = s; t.slen = slen;
    VPUSH(toks, ntok, t);
}

static const char *OPS2[] = {"**", "//", "==", "!=", "<=", ">=", "+=", "-=", "*=", "/=", NULL};
static const char *OPS1 = "+-*/%<>=()[]{},:.";

static void lex(const char *src) {
    int ind[512], ni = 1, paren = 0, line = 0;
    ind[0] = 0;
    const char *p = src;
    if ((unsigned char)p[0] == 0xEF && (unsigned char)p[1] == 0xBB && (unsigned char)p[2] == 0xBF) p += 3;
    while (*p) {
        line++;
        const char *le = strchr(p, '\n');
        if (!le) le = p + strlen(p);
        const char *q = p;
        if (paren == 0) {
            int col = 0;
            while (q < le && (*q == ' ' || *q == '\t')) { col += *q == '\t' ? 4 : 1; q++; }
            const char *r = q;
            while (r < le && *r == '\r') r++;
            if (r == le || *r == '#') goto next;
            if (col > ind[ni - 1]) {
                if (ni >= 512) cerr(line, "Çok derin girinti");
                ind[ni++] = col;
                addtok(TK_IND, line, NULL, 0);
            }
            while (col < ind[ni - 1]) { ni--; addtok(TK_DED, line, NULL, 0); }
            if (col != ind[ni - 1]) cerr(line, "Girinti hatalı");
        }
        while (q < le) {
            unsigned char c = *q;
            if (c == ' ' || c == '\t' || c == '\r') { q++; continue; }
            if (c == '#') break;
            if (c >= '0' && c <= '9') {
                char buf[128];
                int bn = 0, isf = 0;
                while (q < le && ((*q >= '0' && *q <= '9') || *q == '_')) { if (*q != '_' && bn < 120) buf[bn++] = *q; q++; }
                if (q + 1 < le && *q == '.' && q[1] >= '0' && q[1] <= '9') {
                    isf = 1;
                    buf[bn++] = *q++;
                    while (q < le && *q >= '0' && *q <= '9') { if (bn < 120) buf[bn++] = *q; q++; }
                }
                buf[bn] = 0;
                addtok(TK_INT, line, NULL, 0);
                Tok *t = &toks[ntok - 1];
                if (!isf) {
                    unsigned long long v = strtoull(buf, NULL, 10);
                    if (bn > 19 || v > ((1ULL << 62) - 1)) isf = 1;
                    else t->i = (int64_t)v;
                }
                if (isf) { t->k = TK_FLT; t->f = strtod(buf, NULL); }
                continue;
            }
            if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_' || c >= 0x80) {
                const char *s = q;
                while (q < le) {
                    unsigned char d = *q;
                    if ((d >= 'a' && d <= 'z') || (d >= 'A' && d <= 'Z') || (d >= '0' && d <= '9') || d == '_' || d >= 0x80) q++;
                    else break;
                }
                char *w = xstrndup(s, q - s);
                int kw = -1;
                for (int i = 0; i < KW_N; i++)
                    if (!strcmp(w, KWS[i])) kw = i;
                addtok(kw >= 0 ? TK_KW : TK_NAME, line, w, (int)(q - s));
                toks[ntok - 1].kw = kw;
                continue;
            }
            if (c == '"' || c == '\'') {
                char *buf = xcalloc(le - q + 1);
                int bn = 0;
                q++;
                while (q < le && *q != (char)c) {
                    if (*q == '\\' && q + 1 < le) {
                        char e = q[1];
                        if (e == 'n') buf[bn++] = '\n';
                        else if (e == 't') buf[bn++] = '\t';
                        else if (e == '\\' || e == '"' || e == '\'') buf[bn++] = e;
                        else { buf[bn++] = '\\'; buf[bn++] = e; }
                        q += 2;
                    } else buf[bn++] = *q++;
                }
                if (q >= le) cerr(line, "Metin kapatılmamış");
                q++;
                addtok(TK_STR, line, buf, bn);
                continue;
            }
            int done = 0;
            for (int i = 0; OPS2[i]; i++)
                if (q + 1 < le && q[0] == OPS2[i][0] && q[1] == OPS2[i][1]) {
                    addtok(TK_OP, line, xstrndup(q, 2), 2);
                    q += 2;
                    done = 1;
                    break;
                }
            if (done) continue;
            if (strchr(OPS1, c)) {
                if (c == '(' || c == '[' || c == '{') paren++;
                else if ((c == ')' || c == ']' || c == '}') && paren > 0) paren--;
                addtok(TK_OP, line, xstrndup(q, 1), 1);
                q++;
                continue;
            }
            cerr(line, "Bilinmeyen karakter: '%c'", c);
        }
        if (paren == 0) addtok(TK_NL, line, NULL, 0);
    next:
        p = *le ? le + 1 : le;
    }
    while (ni > 1) { ni--; addtok(TK_DED, line, NULL, 0); }
    addtok(TK_EOF, line, NULL, 0);
}

/* =============================== AĞAÇ =============================== */
enum {
    N_INT, N_FLT, N_STR, N_TRUE, N_FALSE, N_NONE, N_NAME, N_BIN, N_AND, N_OR, N_NOT, N_NEG,
    N_CALL, N_METHOD, N_INDEX, N_SLICE, N_LIST, N_DICT,
    S_EXPR, S_ASSIGN, S_IF, S_WHILE, S_FOR, S_FUNC, S_RETURN, S_BREAK, S_CONTINUE, S_PASS, S_BLOCK
};
enum { OP_ADD, OP_SUB, OP_MUL, OP_DIV, OP_FDIV, OP_MOD, OP_POW, OP_EQ, OP_NE, OP_LT, OP_GT, OP_LE, OP_GE, OP_IN };

typedef struct Node Node;
struct Node {
    int k, line, op, slen;
    char *s;
    int64_t i;
    double f;
    Node *a, *b, *c;
    Node **v; int nv;
    Node **w; int nw;
};
static Node *mk(int k, int line) {
    Node *n = xcalloc(sizeof *n);
    n->k = k;
    n->line = line;
    return n;
}

/* =============================== AYRIŞTIRICI =============================== */
static int pos;
static Tok *cur(void) { return &toks[pos]; }
static int isop(const char *s) { return cur()->k == TK_OP && !strcmp(cur()->s, s); }
static int iskw(int kw) { return cur()->k == TK_KW && cur()->kw == kw; }
static int acceptop(const char *s) { if (isop(s)) { pos++; return 1; } return 0; }
static int acceptkw(int kw) { if (iskw(kw)) { pos++; return 1; } return 0; }
static const char *tdesc(Tok *t) {
    switch (t->k) {
    case TK_NL: return "satır sonu";
    case TK_EOF: return "dosya sonu";
    case TK_IND: return "girinti";
    case TK_DED: return "girinti sonu";
    case TK_INT: case TK_FLT: return "sayı";
    case TK_STR: return "metin";
    }
    return t->s;
}
static void expectop(const char *s) {
    if (!acceptop(s)) cerr(cur()->line, "'%s' bekleniyordu, '%s' bulundu", s, tdesc(cur()));
}
static void expectkw(int kw) {
    if (!acceptkw(kw)) cerr(cur()->line, "'%s' bekleniyordu, '%s' bulundu", KWS[kw], tdesc(cur()));
}
static void expectk(int k, const char *what) {
    if (cur()->k != k) cerr(cur()->line, "%s bekleniyordu, '%s' bulundu", what, tdesc(cur()));
    pos++;
}
static char *expectname(void) {
    if (cur()->k != TK_NAME) cerr(cur()->line, "isim bekleniyordu, '%s' bulundu", tdesc(cur()));
    return toks[pos++].s;
}

static Node *expr(void);
static Node *stmt(void);
static Node *simple(void);

static Node *block(void) {
    expectop(":");
    Node *b = mk(S_BLOCK, cur()->line);
    if (cur()->k == TK_NL) {
        pos++;
        expectk(TK_IND, "girintili blok");
        while (cur()->k != TK_DED && cur()->k != TK_EOF) VPUSH(b->v, b->nv, stmt());
        if (cur()->k == TK_DED) pos++;
        return b;
    }
    VPUSH(b->v, b->nv, simple());
    expectk(TK_NL, "satır sonu");
    return b;
}

static Node *stmt(void) {
    Tok *t = cur();
    if (t->k == TK_KW) {
        if (t->kw == KW_EGER) {
            pos++;
            Node *n = mk(S_IF, t->line);
            Node *c = expr();
            VPUSH(n->v, n->nv, c);
            Node *b = block();
            VPUSH(n->w, n->nw, b);
            while (acceptkw(KW_YADA)) {
                c = expr();
                VPUSH(n->v, n->nv, c);
                b = block();
                VPUSH(n->w, n->nw, b);
            }
            if (acceptkw(KW_DEGILSE)) n->c = block();
            return n;
        }
        if (t->kw == KW_IKEN) {
            pos++;
            Node *n = mk(S_WHILE, t->line);
            n->a = expr();
            n->b = block();
            return n;
        }
        if (t->kw == KW_ICIN) {
            pos++;
            Node *n = mk(S_FOR, t->line);
            n->s = expectname();
            expectkw(KW_ICINDE);
            n->a = expr();
            n->b = block();
            return n;
        }
        if (t->kw == KW_FONK) {
            pos++;
            Node *n = mk(S_FUNC, t->line);
            n->s = expectname();
            expectop("(");
            if (!acceptop(")")) {
                for (;;) {
                    Node *p = mk(N_NAME, cur()->line);
                    p->s = expectname();
                    VPUSH(n->v, n->nv, p);
                    if (acceptop(")")) break;
                    expectop(",");
                }
            }
            n->b = block();
            return n;
        }
    }
    Node *n = simple();
    if (cur()->k != TK_EOF) expectk(TK_NL, "satır sonu");
    return n;
}

static Node *simple(void) {
    Tok *t = cur();
    if (t->k == TK_KW) {
        if (t->kw == KW_DONDUR) {
            pos++;
            Node *n = mk(S_RETURN, t->line);
            if (cur()->k != TK_NL && cur()->k != TK_EOF) n->a = expr();
            return n;
        }
        if (t->kw == KW_KIR) { pos++; return mk(S_BREAK, t->line); }
        if (t->kw == KW_DEVAM) { pos++; return mk(S_CONTINUE, t->line); }
        if (t->kw == KW_GEC) { pos++; return mk(S_PASS, t->line); }
    }
    Node *e = expr();
    Tok *o = cur();
    if (o->k == TK_OP && (!strcmp(o->s, "=") || !strcmp(o->s, "+=") || !strcmp(o->s, "-=") || !strcmp(o->s, "*=") || !strcmp(o->s, "/="))) {
        pos++;
        if (e->k != N_NAME && e->k != N_INDEX) cerr(o->line, "Geçersiz atama hedefi");
        Node *n = mk(S_ASSIGN, t->line);
        n->a = e;
        n->op = o->s[0] == '=' ? -1 : o->s[0] == '+' ? OP_ADD : o->s[0] == '-' ? OP_SUB : o->s[0] == '*' ? OP_MUL : OP_DIV;
        n->b = expr();
        return n;
    }
    Node *n = mk(S_EXPR, t->line);
    n->a = e;
    return n;
}

static Node *bin(int op, Node *a, Node *b) {
    Node *n = mk(N_BIN, a->line);
    n->op = op;
    n->a = a;
    n->b = b;
    return n;
}
static Node *e_unary(void);
static Node *e_postfix(void);

static Node *e_mul(void) {
    Node *l = e_unary();
    for (;;) {
        if (acceptop("*")) l = bin(OP_MUL, l, e_unary());
        else if (acceptop("/")) l = bin(OP_DIV, l, e_unary());
        else if (acceptop("//")) l = bin(OP_FDIV, l, e_unary());
        else if (acceptop("%")) l = bin(OP_MOD, l, e_unary());
        else return l;
    }
}
static Node *e_add(void) {
    Node *l = e_mul();
    for (;;) {
        if (acceptop("+")) l = bin(OP_ADD, l, e_mul());
        else if (acceptop("-")) l = bin(OP_SUB, l, e_mul());
        else return l;
    }
}
static Node *e_cmp(void) {
    Node *l = e_add();
    static const char *ops[] = {"==", "!=", "<", ">", "<=", ">="};
    static const int codes[] = {OP_EQ, OP_NE, OP_LT, OP_GT, OP_LE, OP_GE};
    for (;;) {
        int f = 0;
        for (int i = 0; i < 6; i++)
            if (acceptop(ops[i])) { l = bin(codes[i], l, e_add()); f = 1; break; }
        if (f) continue;
        if (acceptkw(KW_ICINDE)) { l = bin(OP_IN, l, e_add()); continue; }
        return l;
    }
}
static Node *e_not(void) {
    int line = cur()->line;
    if (acceptkw(KW_DEGIL)) {
        Node *n = mk(N_NOT, line);
        n->a = e_not();
        return n;
    }
    return e_cmp();
}
static Node *e_and(void) {
    Node *l = e_not();
    while (iskw(KW_VE)) {
        int line = cur()->line;
        pos++;
        Node *n = mk(N_AND, line);
        n->a = l;
        n->b = e_not();
        l = n;
    }
    return l;
}
static Node *expr(void) {
    Node *l = e_and();
    while (iskw(KW_VEYA)) {
        int line = cur()->line;
        pos++;
        Node *n = mk(N_OR, line);
        n->a = l;
        n->b = e_and();
        l = n;
    }
    return l;
}
static Node *e_unary(void) {
    int line = cur()->line;
    if (acceptop("-")) {
        Node *x = e_unary();
        if (x->k == N_INT) { x->i = -x->i; return x; }
        if (x->k == N_FLT) { x->f = -x->f; return x; }
        Node *n = mk(N_NEG, line);
        n->a = x;
        return n;
    }
    if (acceptop("+")) return e_unary();
    Node *b = e_postfix();
    if (acceptop("**")) return bin(OP_POW, b, e_unary());
    return b;
}
static void args(Node *n) {
    if (acceptop(")")) return;
    for (;;) {
        Node *a = expr();
        VPUSH(n->v, n->nv, a);
        if (acceptop(")")) return;
        expectop(",");
    }
}
static Node *primary(void);
static Node *e_postfix(void) {
    Node *e = primary();
    for (;;) {
        int line = cur()->line;
        if (acceptop("(")) {
            if (e->k != N_NAME) cerr(line, "Yalnızca isimle tanımlanmış fonksiyonlar çağrılabilir");
            Node *n = mk(N_CALL, line);
            n->s = e->s;
            args(n);
            e = n;
        } else if (acceptop("[")) {
            Node *a = isop(":") ? NULL : expr();
            if (acceptop(":")) {
                Node *n = mk(N_SLICE, line);
                n->a = e;
                n->b = a;
                n->c = isop("]") ? NULL : expr();
                expectop("]");
                e = n;
            } else {
                expectop("]");
                Node *n = mk(N_INDEX, line);
                n->a = e;
                n->b = a;
                e = n;
            }
        } else if (acceptop(".")) {
            Node *n = mk(N_METHOD, line);
            n->a = e;
            n->s = expectname();
            expectop("(");
            args(n);
            e = n;
        } else return e;
    }
}
static Node *primary(void) {
    Tok *t = &toks[pos++];
    Node *n;
    switch (t->k) {
    case TK_INT: n = mk(N_INT, t->line); n->i = t->i; return n;
    case TK_FLT: n = mk(N_FLT, t->line); n->f = t->f; return n;
    case TK_STR: n = mk(N_STR, t->line); n->s = t->s; n->slen = t->slen; return n;
    case TK_NAME: n = mk(N_NAME, t->line); n->s = t->s; return n;
    case TK_KW:
        if (t->kw == KW_DOGRU) return mk(N_TRUE, t->line);
        if (t->kw == KW_YANLIS) return mk(N_FALSE, t->line);
        if (t->kw == KW_BOS) return mk(N_NONE, t->line);
        break;
    case TK_OP:
        if (!strcmp(t->s, "(")) { n = expr(); expectop(")"); return n; }
        if (!strcmp(t->s, "[")) {
            n = mk(N_LIST, t->line);
            while (!acceptop("]")) {
                Node *x = expr();
                VPUSH(n->v, n->nv, x);
                if (!acceptop(",")) { expectop("]"); break; }
            }
            return n;
        }
        if (!strcmp(t->s, "{")) {
            n = mk(N_DICT, t->line);
            while (!acceptop("}")) {
                Node *k = expr();
                VPUSH(n->v, n->nv, k);
                expectop(":");
                Node *v = expr();
                VPUSH(n->w, n->nw, v);
                if (!acceptop(",")) { expectop("}"); break; }
            }
            return n;
        }
    }
    cerr(t->line, "Beklenmeyen ifade: '%s'", tdesc(t));
    return NULL;
}

/* =============================== ANLAM ÇÖZÜMLEME =============================== */
static const char *BUILTINS[] = {"yazdır", "girdi", "uzunluk", "aralık", "sayı", "ondalık", "metin", "liste",
                                 "tür", "toplam", "en_büyük", "en_küçük", "yuvarla", "mutlak", "sıralı", NULL};
static int builtin_id(const char *s) {
    for (int i = 0; BUILTINS[i]; i++)
        if (!strcmp(BUILTINS[i], s)) return i;
    return -1;
}

typedef struct { char **v; int n; } Names;
static int nfind(Names *ns, const char *s) {
    for (int i = 0; i < ns->n; i++)
        if (!strcmp(ns->v[i], s)) return i;
    return -1;
}
static void nadd(Names *ns, char *s) {
    if (nfind(ns, s) < 0) VPUSH(ns->v, ns->n, s);
}

typedef struct { char *name; Node *n; Names params, locals; } Func;
static Func *funcs;
static int nfuncs;
static Names globals;
static int ffind(const char *s) {
    for (int i = 0; i < nfuncs; i++)
        if (!strcmp(funcs[i].name, s)) return i;
    return -1;
}

static void collect_assigned(Node *s, Names *ns, int top) {
    if (!s) return;
    switch (s->k) {
    case S_ASSIGN: if (s->a->k == N_NAME) nadd(ns, s->a->s); break;
    case S_FOR: nadd(ns, s->s); collect_assigned(s->b, ns, top); break;
    case S_WHILE: collect_assigned(s->b, ns, top); break;
    case S_IF:
        for (int i = 0; i < s->nw; i++) collect_assigned(s->w[i], ns, top);
        collect_assigned(s->c, ns, top);
        break;
    case S_BLOCK:
        for (int i = 0; i < s->nv; i++) collect_assigned(s->v[i], ns, top);
        break;
    case S_FUNC:
        if (!top) cerr(s->line, "'fonk' yalnızca en dış seviyede tanımlanabilir");
        break;
    }
}

/* =============================== KOD ÜRETİMİ =============================== */
typedef struct { char *p; size_t n, cap; } Buf;
static void bvprintf(Buf *b, const char *fmt, va_list ap) {
    va_list cp;
    va_copy(cp, ap);
    int need = vsnprintf(NULL, 0, fmt, cp);
    va_end(cp);
    if (b->n + need + 1 > b->cap) {
        b->cap = (b->n + need + 1) * 2;
        b->p = realloc(b->p, b->cap);
    }
    vsnprintf(b->p + b->n, need + 1, fmt, ap);
    b->n += need;
}
static void bprintf(Buf *b, const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    bvprintf(b, fmt, ap);
    va_end(ap);
}

static Buf *cb;              /* geçerli fonksiyon gövdesi */
static Buf out;              /* tüm çıktı */
static int depth;            /* çerçeve tabanından itibaren yığına itilen 8 baytlık değer sayısı */
static int lbl;
static int nslots;           /* yerel + gizli yuva sayısı */
static Func *curf;           /* NULL => ana program */
static int lbrk[256], lcnt[256], nloop;
static const char *A[4];     /* C çağrı kuralı argüman yazmaçları */

static void emit(const char *fmt, ...) {
    va_list ap;
    bprintf(cb, "\t");
    va_start(ap, fmt);
    bvprintf(cb, fmt, ap);
    va_end(ap);
    bprintf(cb, "\n");
}
static void label(int l) { bprintf(cb, ".L%d:\n", l); }
static int newl(void) { return ++lbl; }
static void push(const char *r) { emit("push %s", r); depth++; }
static void pop(const char *r) { emit("pop %s", r); depth--; }

/* C fonksiyonu çağır: argümanlar yazmaçlarda hazır olmalı */
static void callc(const char *fn) {
    int extra = ((depth & 1) ? 8 : 0) + (WIN ? 32 : 0);
    if (extra) emit("sub rsp, %d", extra);
    emit("call %s", fn);
    if (extra) emit("add rsp, %d", extra);
}

/* İsim karıştırma: Türkçe harfler sembolde güvenli hale getirilir */
static char *mangle(const char *pre, const char *s) {
    Buf b = {0};
    bprintf(&b, "%s", pre);
    for (const unsigned char *p = (const unsigned char *)s; *p; p++) {
        if ((*p >= 'a' && *p <= 'z') || (*p >= 'A' && *p <= 'Z') || (*p >= '0' && *p <= '9')) bprintf(&b, "%c", *p);
        else if (*p == '_') bprintf(&b, "__");
        else bprintf(&b, "_%02x", *p);
    }
    return b.p;
}

/* Sabitler (metin ve ondalık) */
typedef struct { int isstr; char *s; int len; double f; } Const;
static Const *consts;
static int nconsts;
static int const_str(char *s, int len) {
    for (int i = 0; i < nconsts; i++)
        if (consts[i].isstr && consts[i].len == len && !memcmp(consts[i].s, s, len)) return i;
    Const c = {1, s, len, 0};
    VPUSH(consts, nconsts, c);
    return nconsts - 1;
}
static int const_flt(double f) {
    for (int i = 0; i < nconsts; i++)
        if (!consts[i].isstr && !memcmp(&consts[i].f, &f, 8)) return i;
    Const c = {0, NULL, 0, f};
    VPUSH(consts, nconsts, c);
    return nconsts - 1;
}
static char **mnames;
static int nmnames;
static int mname(char *s) {
    for (int i = 0; i < nmnames; i++)
        if (!strcmp(mnames[i], s)) return i;
    VPUSH(mnames, nmnames, s);
    return nmnames - 1;
}

/* Değişken konumu */
static int slot_new(void) { return nslots++; }
static const char *slot(int i) {
    static char b[8][48];
    static int r;
    r = (r + 1) & 7;
    snprintf(b[r], 48, "qword ptr [rbp-%d]", 8 * (i + 1));
    return b[r];
}
static const char *loc(const char *name, int line) {
    static char b[8][300];
    static int r;
    r = (r + 1) & 7;
    if (curf) {
        int i = nfind(&curf->params, name);
        if (i >= 0) {
            snprintf(b[r], 300, "qword ptr [rbp+%d]", 16 + 8 * (curf->params.n - 1 - i));
            return b[r];
        }
        i = nfind(&curf->locals, name);
        if (i >= 0) return slot(i);
    }
    if (nfind(&globals, name) >= 0) {
        snprintf(b[r], 300, "qword ptr [rip+%s]", mangle("G_", name));
        return b[r];
    }
    if (ffind(name) >= 0 || builtin_id(name) >= 0)
        cerr(line, "'%s' bir fonksiyon; değer olarak kullanılamaz, çağırmak için '%s(...)' yazın", name, name);
    cerr(line, "Tanımsız isim: '%s'", name);
    return NULL;
}

static void gen(Node *e);

/* Doğruluk sınaması: rax yanlışsa Lf'ye atla */
static void cond_false(Node *e, int lf) {
    int lt = newl();
    gen(e);
    emit("cmp rax, 4");
    emit("je .L%d", lt);
    emit("cmp rax, 2");
    emit("je .L%d", lf);
    emit("mov %s, rax", A[0]);
    callc("hk_truthy");
    emit("test eax, eax");
    emit("jz .L%d", lf);
    label(lt);
}

static void slow2(const char *fn) {
    emit("mov %s, r10", A[0]);
    emit("mov %s, r11", A[1]);
    callc(fn);
}

/* r10 = sol, r11 = sağ  ->  rax */
static void binop_core(int op) {
    int ls = newl(), ld = newl();
    const char *cc = NULL, *fn = NULL;
    switch (op) {
    case OP_ADD:
        emit("mov rax, r10"); emit("and rax, r11"); emit("test al, 1"); emit("jz .L%d", ls);
        emit("lea rax, [r10-1]"); emit("add rax, r11"); emit("jo .L%d", ls); emit("jmp .L%d", ld);
        label(ls); slow2("hk_add"); label(ld);
        return;
    case OP_SUB:
        emit("mov rax, r10"); emit("and rax, r11"); emit("test al, 1"); emit("jz .L%d", ls);
        emit("mov rax, r10"); emit("sub rax, r11"); emit("jo .L%d", ls); emit("add rax, 1"); emit("jmp .L%d", ld);
        label(ls); slow2("hk_sub"); label(ld);
        return;
    case OP_MUL:
        emit("mov rax, r10"); emit("and rax, r11"); emit("test al, 1"); emit("jz .L%d", ls);
        emit("mov rax, r10"); emit("sar rax, 1"); emit("lea rdx, [r11-1]"); emit("imul rax, rdx");
        emit("jo .L%d", ls); emit("add rax, 1"); emit("jmp .L%d", ld);
        label(ls); slow2("hk_mul"); label(ld);
        return;
    case OP_DIV: slow2("hk_div"); return;
    case OP_FDIV: slow2("hk_fdiv"); return;
    case OP_MOD: slow2("hk_mod"); return;
    case OP_POW: slow2("hk_pow"); return;
    case OP_IN:
        emit("mov %s, r11", A[0]);
        emit("mov %s, r10", A[1]);
        callc("hk_contains");
        return;
    case OP_EQ: cc = "sete"; fn = "hk_eq"; break;
    case OP_NE: cc = "setne"; fn = "hk_ne"; break;
    case OP_LT: cc = "setl"; fn = "hk_lt"; break;
    case OP_GT: cc = "setg"; fn = "hk_gt"; break;
    case OP_LE: cc = "setle"; fn = "hk_le"; break;
    case OP_GE: cc = "setge"; fn = "hk_ge"; break;
    }
    emit("mov rax, r10"); emit("and rax, r11"); emit("test al, 1"); emit("jz .L%d", ls);
    emit("cmp r10, r11"); emit("%s al", cc); emit("movzx eax, al"); emit("lea rax, [rax*2+2]"); emit("jmp .L%d", ld);
    label(ls); slow2(fn); label(ld);
}

static void gen(Node *e) {
    switch (e->k) {
    case N_INT:
        emit("mov rax, %lld", (long long)(((uint64_t)e->i << 1) | 1));
        return;
    case N_FLT: emit("mov rax, qword ptr [rip+HKK%d]", const_flt(e->f)); return;
    case N_STR: emit("mov rax, qword ptr [rip+HKK%d]", const_str(e->s, e->slen)); return;
    case N_TRUE: emit("mov eax, 4"); return;
    case N_FALSE: emit("mov eax, 2"); return;
    case N_NONE: emit("xor eax, eax"); return;
    case N_NAME: emit("mov rax, %s", loc(e->s, e->line)); return;
    case N_BIN:
        gen(e->a);
        push("rax");
        gen(e->b);
        emit("mov r11, rax");
        pop("r10");
        binop_core(e->op);
        return;
    case N_AND: case N_OR: {
        int lf = newl(), le = newl(), lt = newl();
        gen(e->a);
        push("rax");
        /* doğruluk */
        emit("cmp rax, 4"); emit("je .L%d", lt);
        emit("cmp rax, 2"); emit("je .L%d", lf);
        emit("mov %s, rax", A[0]); callc("hk_truthy"); emit("test eax, eax"); emit("jz .L%d", lf);
        label(lt);
        if (e->k == N_AND) {
            pop("rax");
            gen(e->b);
            emit("jmp .L%d", le);
            depth++;
            label(lf);
            pop("rax");
        } else {
            pop("rax");
            emit("jmp .L%d", le);
            depth++;
            label(lf);
            pop("rax");
            gen(e->b);
        }
        label(le);
        return;
    }
    case N_NOT: {
        int lf = newl(), le = newl();
        cond_false(e->a, lf);
        emit("mov eax, 2");
        emit("jmp .L%d", le);
        label(lf);
        emit("mov eax, 4");
        label(le);
        return;
    }
    case N_NEG: {
        int ls = newl(), ld = newl();
        gen(e->a);
        emit("test al, 1"); emit("jz .L%d", ls);
        emit("mov r11, 2"); emit("sub r11, rax"); emit("jo .L%d", ls); emit("mov rax, r11"); emit("jmp .L%d", ld);
        label(ls); emit("mov %s, rax", A[0]); callc("hk_neg"); label(ld);
        return;
    }
    case N_CALL: {
        int f = ffind(e->s);
        int isvar = (curf && (nfind(&curf->params, e->s) >= 0 || nfind(&curf->locals, e->s) >= 0)) || nfind(&globals, e->s) >= 0;
        if (f >= 0 && !isvar) {
            if (funcs[f].params.n != e->nv)
                cerr(e->line, "'%s' %d değer bekliyor, %d verildi", e->s, funcs[f].params.n, e->nv);
            for (int i = 0; i < e->nv; i++) { gen(e->v[i]); push("rax"); }
            emit("call %s", mangle("HF_", e->s));
            if (e->nv) { emit("add rsp, %d", 8 * e->nv); depth -= e->nv; }
            return;
        }
        int b = builtin_id(e->s);
        if (b >= 0 && !isvar) {
            for (int i = 0; i < e->nv; i++) { gen(e->v[i]); push("rax"); }
            emit("mov %s, rsp", A[1]);
            emit("mov %s, %d", A[2], e->nv);
            emit("mov %s, %d", A[0], b);
            callc("hk_builtin");
            if (e->nv) { emit("add rsp, %d", 8 * e->nv); depth -= e->nv; }
            return;
        }
        if (isvar) cerr(e->line, "'%s' bir değişken, fonksiyon gibi çağrılamaz", e->s);
        cerr(e->line, "Tanımsız fonksiyon: '%s'", e->s);
        return;
    }
    case N_METHOD: {
        int m = mname(e->s);
        gen(e->a);
        push("rax");
        for (int i = 0; i < e->nv; i++) { gen(e->v[i]); push("rax"); }
        emit("mov %s, rsp", A[2]);
        emit("mov %s, %d", A[3], e->nv);
        emit("mov %s, qword ptr [rsp+%d]", A[0], 8 * e->nv);
        emit("lea %s, [rip+HKMN%d]", A[1], m);
        callc("hk_method");
        emit("add rsp, %d", 8 * (e->nv + 1));
        depth -= e->nv + 1;
        return;
    }
    case N_INDEX:
        gen(e->a);
        push("rax");
        gen(e->b);
        emit("mov %s, rax", A[1]);
        pop(A[0]);
        callc("hk_index");
        return;
    case N_SLICE:
        gen(e->a);
        push("rax");
        if (e->b) gen(e->b); else emit("xor eax, eax");
        push("rax");
        if (e->c) gen(e->c); else emit("xor eax, eax");
        emit("mov %s, rax", A[2]);
        pop(A[1]);
        pop(A[0]);
        callc("hk_slice");
        return;
    case N_LIST:
        callc("hk_list_new");
        push("rax");
        for (int i = 0; i < e->nv; i++) {
            gen(e->v[i]);
            emit("mov %s, rax", A[1]);
            emit("mov %s, qword ptr [rsp]", A[0]);
            callc("hk_list_push");
        }
        pop("rax");
        return;
    case N_DICT:
        callc("hk_dict_new");
        push("rax");
        for (int i = 0; i < e->nv; i++) {
            gen(e->v[i]);
            push("rax");
            gen(e->w[i]);
            emit("mov %s, rax", A[2]);
            pop(A[1]);
            emit("mov %s, qword ptr [rsp]", A[0]);
            callc("hk_dict_set");
        }
        pop("rax");
        return;
    }
    cerr(e->line, "İç hata: bilinmeyen ifade");
}

static void gen_stmt(Node *s);
static void gen_block(Node *b) {
    for (int i = 0; i < b->nv; i++) gen_stmt(b->v[i]);
}

static int is_range_call(Node *e) {
    return e->k == N_CALL && !strcmp(e->s, "aralık") && ffind("aralık") < 0 && e->nv >= 1 && e->nv <= 3;
}

static void gen_stmt(Node *s) {
    emit("mov dword ptr [rip+hk_line], %d", s->line);
    switch (s->k) {
    case S_EXPR: gen(s->a); return;
    case S_ASSIGN: {
        Node *t = s->a;
        if (t->k == N_NAME) {
            if (s->op < 0) gen(s->b);
            else {
                gen(t);
                push("rax");
                gen(s->b);
                emit("mov r11, rax");
                pop("r10");
                binop_core(s->op);
            }
            emit("mov %s, rax", loc(t->s, s->line));
            return;
        }
        gen(t->a);
        push("rax");
        gen(t->b);
        push("rax");
        if (s->op >= 0) {
            emit("mov %s, qword ptr [rsp+8]", A[0]);
            emit("mov %s, qword ptr [rsp]", A[1]);
            callc("hk_index");
            push("rax");
            gen(s->b);
            emit("mov r11, rax");
            pop("r10");
            binop_core(s->op);
        } else gen(s->b);
        emit("mov %s, rax", A[2]);
        pop(A[1]);
        pop(A[0]);
        callc("hk_setindex");
        return;
    }
    case S_IF: {
        int le = newl();
        for (int i = 0; i < s->nv; i++) {
            int ln = newl();
            cond_false(s->v[i], ln);
            gen_block(s->w[i]);
            emit("jmp .L%d", le);
            label(ln);
        }
        if (s->c) gen_block(s->c);
        label(le);
        return;
    }
    case S_WHILE: {
        int lt = newl(), le = newl();
        label(lt);
        cond_false(s->a, le);
        lbrk[nloop] = le; lcnt[nloop] = lt; nloop++;
        gen_block(s->b);
        nloop--;
        emit("jmp .L%d", lt);
        label(le);
        return;
    }
    case S_FOR: {
        int lt = newl(), lc = newl(), le = newl();
        const char *var = loc(s->s, s->line);
        char varb[300];
        snprintf(varb, sizeof varb, "%s", var);
        if (is_range_call(s->a)) {
            /* Hızlı yol: aralık() için liste oluşturmadan yerel sayaç */
            Node *r = s->a;
            int si = slot_new(), se = slot_new(), st = slot_new();
            int lneg = newl(), lbody = newl();
            if (r->nv == 1) emit("mov rax, 1");
            else { gen(r->v[0]); emit("mov %s, rax", A[0]); callc("hk_check_int"); }
            emit("mov %s, rax", slot(si));
            gen(r->v[r->nv == 1 ? 0 : 1]);
            emit("mov %s, rax", A[0]);
            callc("hk_check_int");
            emit("mov %s, rax", slot(se));
            if (r->nv == 3) { gen(r->v[2]); emit("mov %s, rax", A[0]); callc("hk_check_step"); }
            else emit("mov rax, 3");
            emit("mov %s, rax", slot(st));
            label(lt);
            emit("mov rax, %s", slot(si));
            emit("cmp %s, 1", slot(st));
            emit("jl .L%d", lneg);
            emit("cmp rax, %s", slot(se));
            emit("jge .L%d", le);
            emit("jmp .L%d", lbody);
            label(lneg);
            emit("cmp rax, %s", slot(se));
            emit("jle .L%d", le);
            label(lbody);
            emit("mov %s, rax", varb);
            lbrk[nloop] = le; lcnt[nloop] = lc; nloop++;
            gen_block(s->b);
            nloop--;
            label(lc);
            emit("mov rax, %s", slot(si));
            emit("add rax, %s", slot(st));
            emit("sub rax, 1");
            emit("mov %s, rax", slot(si));
            emit("jmp .L%d", lt);
            label(le);
            return;
        }
        int sl = slot_new(), sx = slot_new();
        gen(s->a);
        emit("mov %s, rax", A[0]);
        callc("hk_iter");
        emit("mov %s, rax", slot(sl));
        emit("mov %s, 0", slot(sx));
        label(lt);
        emit("mov r10, %s", slot(sl));
        emit("mov rax, %s", slot(sx));
        emit("cmp rax, qword ptr [r10+8]");
        emit("jge .L%d", le);
        emit("mov r11, qword ptr [r10+24]");
        emit("mov rax, qword ptr [r11+rax*8]");
        emit("mov %s, rax", varb);
        lbrk[nloop] = le; lcnt[nloop] = lc; nloop++;
        gen_block(s->b);
        nloop--;
        label(lc);
        emit("add %s, 1", slot(sx));
        emit("jmp .L%d", lt);
        label(le);
        return;
    }
    case S_FUNC:
        if (curf) cerr(s->line, "'fonk' yalnızca en dış seviyede tanımlanabilir");
        return;
    case S_RETURN:
        if (!curf) cerr(s->line, "'döndür' yalnızca fonk içinde kullanılabilir");
        if (s->a) gen(s->a); else emit("xor eax, eax");
        emit("jmp %s", mangle(".LR_", curf->name));
        return;
    case S_BREAK:
        if (!nloop) cerr(s->line, "'kır' yalnızca döngü içinde kullanılabilir");
        emit("jmp .L%d", lbrk[nloop - 1]);
        return;
    case S_CONTINUE:
        if (!nloop) cerr(s->line, "'devam' yalnızca döngü içinde kullanılabilir");
        emit("jmp .L%d", lcnt[nloop - 1]);
        return;
    case S_PASS: return;
    }
    cerr(s->line, "İç hata: bilinmeyen deyim");
}

static void emit_function(const char *sym, const char *retlbl, int nlocals_zero, Buf *body) {
    bprintf(&out, "\n%s:\n\tpush rbp\n\tmov rbp, rsp\n", sym);
    if (nslots) bprintf(&out, "\tsub rsp, %d\n", 8 * nslots);
    bprintf(&out, "\tand rsp, -16\n");
    for (int i = 0; i < nslots; i++) bprintf(&out, "\tmov qword ptr [rbp-%d], 0\n", 8 * (i + 1));
    (void)nlocals_zero;
    bprintf(&out, "%s", body->p ? body->p : "");
    bprintf(&out, "\txor eax, eax\n%s:\n\tmov rsp, rbp\n\tpop rbp\n\tret\n", retlbl);
}

static void bytes(const char *lab, const char *s, int n) {
    bprintf(&out, "%s:\n\t.byte ", lab);
    for (int i = 0; i < n; i++) bprintf(&out, "%d,", (unsigned char)s[i]);
    bprintf(&out, "0\n");
}

static void compile(Node **prog, int nprog) {
    if (WIN) { A[0] = "rcx"; A[1] = "rdx"; A[2] = "r8"; A[3] = "r9"; }
    else { A[0] = "rdi"; A[1] = "rsi"; A[2] = "rdx"; A[3] = "rcx"; }

    /* 1. fonksiyonları ve genel değişkenleri topla */
    for (int i = 0; i < nprog; i++) {
        Node *s = prog[i];
        if (s->k == S_FUNC) {
            if (ffind(s->s) >= 0) cerr(s->line, "'%s' zaten tanımlı", s->s);
            Func f = {0};
            f.name = s->s;
            f.n = s;
            for (int j = 0; j < s->nv; j++) {
                if (nfind(&f.params, s->v[j]->s) >= 0) cerr(s->line, "Aynı parametre iki kez: '%s'", s->v[j]->s);
                nadd(&f.params, s->v[j]->s);
            }
            VPUSH(funcs, nfuncs, f);
        } else collect_assigned(s, &globals, 1);
    }
    for (int i = 0; i < nfuncs; i++) {
        Names all = {0};
        collect_assigned(funcs[i].n->b, &all, 0);
        for (int j = 0; j < all.n; j++)
            if (nfind(&funcs[i].params, all.v[j]) < 0) nadd(&funcs[i].locals, all.v[j]);
    }

    bprintf(&out, "# HakDil %s derleyicisi tarafından üretildi\n\t.intel_syntax noprefix\n\t.text\n\t.globl hk_main\n", SURUM);

    /* 2. fonksiyonlar */
    for (int i = 0; i < nfuncs; i++) {
        Buf body = {0};
        cb = &body;
        curf = &funcs[i];
        depth = 0;
        nloop = 0;
        nslots = curf->locals.n;
        gen_block(curf->n->b);
        emit_function(mangle("HF_", curf->name), mangle(".LR_", curf->name), 0, &body);
        free(body.p);
    }

    /* 3. ana program */
    {
        Buf body = {0};
        cb = &body;
        curf = NULL;
        depth = 0;
        nloop = 0;
        nslots = 0;
        callc("hk_consts_init");
        for (int i = 0; i < nprog; i++) gen_stmt(prog[i]);
        emit_function("hk_main", ".LR_main", 0, &body);
        free(body.p);
    }

    /* 4. sabit başlatıcı */
    bprintf(&out, "\nhk_consts_init:\n\tpush rbp\n\tmov rbp, rsp\n\tsub rsp, 32\n\tand rsp, -16\n");
    for (int i = 0; i < nconsts; i++) {
        if (consts[i].isstr) {
            bprintf(&out, "\tlea %s, [rip+HKSD%d]\n\tmov %s, %d\n\tcall hk_str_new\n", A[0], i, A[1], consts[i].len);
        } else {
            uint64_t bits;
            memcpy(&bits, &consts[i].f, 8);
            bprintf(&out, "\tmov %s, %llu\n\tcall hk_flt_bits\n", A[0], (unsigned long long)bits);
        }
        bprintf(&out, "\tmov qword ptr [rip+HKK%d], rax\n", i);
    }
    bprintf(&out, "\tmov rsp, rbp\n\tpop rbp\n\tret\n");

    /* 5. veri */
    bprintf(&out, "\n\t.data\n\t.balign 8\n");
    for (int i = 0; i < globals.n; i++) bprintf(&out, "%s:\t.quad 0\n", mangle("G_", globals.v[i]));
    for (int i = 0; i < nconsts; i++) bprintf(&out, "HKK%d:\t.quad 0\n", i);
    for (int i = 0; i < nconsts; i++) {
        if (!consts[i].isstr) continue;
        char lab[32];
        snprintf(lab, sizeof lab, "HKSD%d", i);
        bytes(lab, consts[i].s, consts[i].len);
    }
    for (int i = 0; i < nmnames; i++) {
        char lab[32];
        snprintf(lab, sizeof lab, "HKMN%d", i);
        bytes(lab, mnames[i], (int)strlen(mnames[i]));
    }
    if (!WIN) bprintf(&out, "\t.section .note.GNU-stack,\"\",@progbits\n");
}

/* =============================== SÜRÜCÜ =============================== */
static char *readfile(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *s = xcalloc(n + 1);
    if (fread(s, 1, n, f) != (size_t)n) { fclose(f); return NULL; }
    fclose(f);
    return s;
}
static int exists(const char *p) {
    FILE *f = fopen(p, "rb");
    if (f) fclose(f);
    return f != NULL;
}
#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#endif
static char *dirof(const char *p);
/* derleyicinin bulunduğu klasör (PATH'ten çağrılsa bile) */
static char *exe_dir(const char *argv0) {
    char b[4096] = {0};
#ifdef _WIN32
    if (GetModuleFileNameA(NULL, b, sizeof b - 1) > 0) return dirof(b);
#else
    if (readlink("/proc/self/exe", b, sizeof b - 1) > 0) return dirof(b);
#endif
    return dirof(argv0);
}
static char *dirof(const char *p) {
    const char *s1 = strrchr(p, '/'), *s2 = strrchr(p, '\\');
    const char *s = s1 > s2 ? s1 : s2;
    if (!s) return xstrndup(".", 1);
    return xstrndup(p, s - p);
}

static void usage(void) {
    fprintf(stderr,
            "HakDil %s derleyicisi\n"
            "Kullanım:\n"
            "  hakc program.hak            çalıştırılabilir dosya üret\n"
            "  hakc program.hak -o ad      çıktı adını belirle\n"
            "  hakc -r program.hak         derle ve çalıştır\n"
            "  hakc -S program.hak         yalnızca assembly (.s) üret\n"
            "  --hedef=windows|linux       hedef sistem (varsayılan: bu sistem)\n",
            SURUM);
    exit(1);
}

int main(int argc, char **argv) {
    const char *in = NULL, *outp = NULL;
    int run = 0, asmonly = 0, cross = 0;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "-o") && i + 1 < argc) outp = argv[++i];
        else if (!strcmp(argv[i], "-r")) run = 1;
        else if (!strcmp(argv[i], "-S")) asmonly = 1;
        else if (!strcmp(argv[i], "--hedef=windows")) { cross = !WIN; WIN = 1; }
        else if (!strcmp(argv[i], "--hedef=linux")) { cross = WIN; WIN = 0; }
        else if (!strcmp(argv[i], "--surum") || !strcmp(argv[i], "--sürüm")) { printf("HakDil %s\n", SURUM); return 0; }
        else if (argv[i][0] == '-') usage();
        else in = argv[i];
    }
    if (!in) usage();
    char *src = readfile(in);
    if (!src) cerr(0, "Dosya açılamadı: %s", in);

    lex(src);
    Node **prog = NULL;
    int nprog = 0;
    while (cur()->k != TK_EOF) {
        if (cur()->k == TK_NL) { pos++; continue; }
        Node *s = stmt();
        VPUSH(prog, nprog, s);
    }
    compile(prog, nprog);

    /* çıktı adları */
    char base[1024];
    snprintf(base, sizeof base, "%s", in);
    char *dot = strrchr(base, '.');
    if (dot && dot > strrchr(base, '/') && (!strrchr(base, '\\') || dot > strrchr(base, '\\'))) *dot = 0;
    char exe[1100], asmf[1100];
    if (outp) snprintf(exe, sizeof exe, "%s", outp);
    else snprintf(exe, sizeof exe, "%s%s", base, WIN ? ".exe" : "");
    snprintf(asmf, sizeof asmf, "%s.s", asmonly && outp ? outp : base);

    FILE *f = fopen(asmf, "wb");
    if (!f) cerr(0, "Yazılamadı: %s", asmf);
    fwrite(out.p, 1, out.n, f);
    fclose(f);
    if (asmonly) { printf("Assembly yazıldı: %s\n", asmf); return 0; }

    /* bağlama: hakrt.o (yoksa hakrt.c) derleyiciyle aynı klasörde aranır */
    char *dir = exe_dir(argv[0]);
    char rt[1200];
    const char *rtname = cross && WIN ? "hakrt_win.o" : "hakrt.o";
    snprintf(rt, sizeof rt, "%s/%s", dir, rtname);
    if (!exists(rt)) snprintf(rt, sizeof rt, "%s/hakrt.c", dir);
    if (!exists(rt)) cerr(0, "Çalışma zamanı bulunamadı (%s klasöründe hakrt.o veya hakrt.c olmalı)", dir);
    const char *cc = getenv("HAKDIL_CC");
    if (!cc) cc = cross ? (WIN ? "x86_64-w64-mingw32-gcc" : "gcc") : "gcc";
    char cmd[4000];
    snprintf(cmd, sizeof cmd, "%s -O2 -o \"%s\" \"%s\" \"%s\" -lm", cc, exe, asmf, rt);
    int rc = system(cmd);
    remove(asmf);
    if (rc != 0) cerr(0, "Bağlama başarısız. GCC (Windows'ta MinGW-w64) kurulu mu?");
    if (run) {
        char rcmd[1200];
        if (WIN) snprintf(rcmd, sizeof rcmd, "\"%s\"", exe);
        else snprintf(rcmd, sizeof rcmd, "%s%s", strchr(exe, '/') ? "" : "./", exe);
        return system(rcmd) == 0 ? 0 : 1;
    }
    return 0;
}

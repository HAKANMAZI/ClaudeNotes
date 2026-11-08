"""
Kare - Instagram benzeri fotoğraf paylaşım sitesi
Kurulum:  pip install flask
Çalıştır: python app.py   ->  http://127.0.0.1:5000
"""

# ============================================================
# KÜTÜPHANELER
# ============================================================
import os        # Dosya ve klasör işlemleri için
import sqlite3   # Veritabanı (SQLite) için, Python ile birlikte gelir
import uuid      # Yüklenen fotoğraflara benzersiz isim vermek için
from functools import wraps  # "Giriş gerekli" kontrolünü yazmak için

# Flask: web uygulamasını çalıştıran kütüphane
from flask import (Flask, request, redirect, url_for, session, g, flash,
                   render_template_string, send_from_directory, abort)

# Şifreleri düz metin değil, şifrelenmiş (hash) olarak saklamak için
from werkzeug.security import generate_password_hash, check_password_hash


# ============================================================
# AYARLAR
# ============================================================
BASE = os.path.dirname(os.path.abspath(__file__))  # app.py'nin bulunduğu klasör
UPLOADS = os.path.join(BASE, "uploads")            # Fotoğrafların kaydedileceği klasör
DB = os.path.join(BASE, "kare.db")                 # Veritabanı dosyası
IZINLI = {"png", "jpg", "jpeg", "gif", "webp"}     # Kabul edilen fotoğraf türleri
os.makedirs(UPLOADS, exist_ok=True)                # uploads klasörü yoksa oluştur

app = Flask(__name__)  # Uygulamayı oluştur

# Oturum çerezlerini imzalayan gizli anahtar.
# Ortam değişkeninde SECRET_KEY varsa onu kullanır, yoksa varsayılanı.
app.secret_key = os.environ.get("SECRET_KEY", "degistir-beni")

# Yüklenebilecek en büyük dosya boyutu: on megabayt
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


# ============================================================
# VERİTABANI
# ============================================================
def db():
    """Veritabanı bağlantısını döndürür. Her istekte bir kez açılır."""
    if "db" not in g:  # g: tek bir istek boyunca veri tutan Flask nesnesi
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row            # Satırlara isimle erişim: row["username"]
        g.db.execute("PRAGMA foreign_keys = ON")  # Silinen kayda bağlı verileri de sil
    return g.db


@app.teardown_appcontext
def kapat(_):
    """İstek bitince veritabanı bağlantısını kapatır."""
    d = g.pop("db", None)
    if d:
        d.close()


def kur():
    """Tablolar yoksa oluşturur. Uygulama başlarken bir kez çalışır."""
    with sqlite3.connect(DB) as c:
        c.executescript("""
        -- Kullanıcılar
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL, bio TEXT DEFAULT '');

        -- Gönderiler (fotoğraf + açıklama)
        CREATE TABLE IF NOT EXISTS posts(
            id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            image TEXT NOT NULL, caption TEXT, created TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

        -- Beğeniler (bir kullanıcı bir gönderiyi bir kez beğenebilir)
        CREATE TABLE IF NOT EXISTS likes(
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
            PRIMARY KEY(user_id, post_id));

        -- Yorumlar
        CREATE TABLE IF NOT EXISTS comments(
            id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
            body TEXT NOT NULL, created TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

        -- Takipler (follower, followed'ı takip eder)
        CREATE TABLE IF NOT EXISTS follows(
            follower INTEGER REFERENCES users(id) ON DELETE CASCADE,
            followed INTEGER REFERENCES users(id) ON DELETE CASCADE,
            PRIMARY KEY(follower, followed));
        """)


kur()  # Tabloları hazırla (sunucuda da çalışsın diye burada çağrılır)


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================
def giris_gerekli(f):
    """Bir sayfanın üstüne konunca, giriş yapmamış kişiyi giriş sayfasına yollar."""
    @wraps(f)
    def w(*a, **k):
        if "uid" not in session:  # Oturumda kullanıcı numarası yoksa
            return redirect(url_for("giris"))
        return f(*a, **k)
    return w


def ben():
    """Giriş yapmış kullanıcının bilgilerini döndürür. Giriş yoksa None."""
    if "uid" in session:
        return db().execute("SELECT * FROM users WHERE id=?", (session["uid"],)).fetchone()


def gonderi_detay(rows):
    """Gönderilere beğeni sayısı, yorumlar ve 'ben beğendim mi' bilgisini ekler."""
    uid = session.get("uid")
    out = []
    for p in rows:
        p = dict(p)  # Satırı düzenlenebilir sözlüğe çevir
        # Toplam beğeni sayısı
        p["likes"] = db().execute("SELECT COUNT(*) FROM likes WHERE post_id=?", (p["id"],)).fetchone()[0]
        # Giriş yapan kullanıcı bu gönderiyi beğenmiş mi?
        p["liked"] = bool(db().execute("SELECT 1 FROM likes WHERE post_id=? AND user_id=?", (p["id"], uid)).fetchone())
        # Gönderinin yorumları, yazan kişinin adıyla
        p["comments"] = db().execute(
            "SELECT c.body, u.username FROM comments c JOIN users u ON u.id=c.user_id "
            "WHERE post_id=? ORDER BY c.id", (p["id"],)).fetchall()
        out.append(p)
    return out


# ============================================================
# HTML ŞABLONLARI
# ============================================================
# TEMEL: Her sayfanın ortak iskeleti (üst menü, renkler, yazı tipi).
# {{ icerik }} kısmına her sayfanın kendi içeriği yerleşir.
TEMEL = """<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kare</title>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;800&display=swap" rel="stylesheet">
<style>
:root{--zemin:#EEF1F4;--kart:#FFFFFF;--yazi:#1B2430;--soluk:#6B7684;--vurgu:#C2185B;--cizgi:#D8DEE5}
@media (prefers-color-scheme:dark){:root{--zemin:#12161C;--kart:#1B2129;--yazi:#E8ECF1;--soluk:#97A1AD;--vurgu:#F06292;--cizgi:#2C343F}}
*{box-sizing:border-box}body{margin:0;background:var(--zemin);color:var(--yazi);font-family:Manrope,system-ui,sans-serif}
a{color:inherit;text-decoration:none}
header{position:sticky;top:0;background:var(--kart);border-bottom:1px solid var(--cizgi);z-index:5}
.ust{max-width:620px;margin:auto;display:flex;align-items:center;gap:18px;padding:12px 16px}
.logo{font-weight:800;font-size:26px;letter-spacing:-1px;margin-right:auto}
.logo span{display:inline-block;width:14px;height:14px;background:var(--vurgu);margin-left:4px;border-radius:3px}
main{max-width:620px;margin:auto;padding:20px 16px}
.kart{background:var(--kart);border:1px solid var(--cizgi);border-radius:14px;margin-bottom:22px;overflow:hidden}
.bas{padding:12px 14px;font-weight:600}
.kart img{width:100%;display:block;aspect-ratio:1;object-fit:cover}
.alt{padding:10px 14px 14px}
.btn{background:var(--vurgu);color:#fff;border:0;padding:10px 16px;border-radius:9px;font:600 15px Manrope,sans-serif;cursor:pointer}
.btn.ikincil{background:transparent;color:var(--yazi);border:1px solid var(--cizgi)}
.kalp{background:none;border:0;font-size:24px;cursor:pointer;padding:0;color:var(--yazi)}
.kalp.dolu{color:var(--vurgu)}
input,textarea{width:100%;padding:10px;border:1px solid var(--cizgi);border-radius:9px;background:var(--zemin);color:var(--yazi);font:15px Manrope,sans-serif}
form.satir{display:flex;gap:8px;margin-top:8px}
.soluk{color:var(--soluk);font-size:14px}
.izgara{display:grid;grid-template-columns:repeat(3,1fr);gap:4px}
.izgara img{width:100%;aspect-ratio:1;object-fit:cover;display:block}
.uyari{background:var(--kart);border-left:4px solid var(--vurgu);padding:10px 14px;margin-bottom:16px}
:focus-visible{outline:2px solid var(--vurgu);outline-offset:2px}
</style></head><body>
<header><div class="ust"><a class="logo" href="{{ url_for('akis') }}">kare<span></span></a>
{% if me %}<a href="{{ url_for('kesfet') }}">Keşfet</a><a href="{{ url_for('yukle') }}">Paylaş</a>
<a href="{{ url_for('profil', ad=me.username) }}">@{{ me.username }}</a><a class="soluk" href="{{ url_for('cikis') }}">Çıkış</a>
{% endif %}</div></header><main>
{% for m in get_flashed_messages() %}<div class="uyari">{{ m }}</div>{% endfor %}
{{ icerik|safe }}</main></body></html>"""

# GONDERI: Gönderi listesini çizen şablon (akış ve keşfet sayfalarında kullanılır).
# Her gönderi için: kullanıcı adı, fotoğraf, beğeni düğmesi, açıklama, yorumlar, yorum kutusu.
GONDERI = """{% for p in posts %}<article class="kart">
<div class="bas"><a href="{{ url_for('profil', ad=p.username) }}">@{{ p.username }}</a></div>
<img src="{{ url_for('dosya', ad=p.image) }}" alt="{{ p.caption or 'Fotoğraf' }}">
<div class="alt">
<form method="post" action="{{ url_for('begen', pid=p.id) }}" style="display:inline">
<button class="kalp {{ 'dolu' if p.liked }}" aria-label="Beğen">{{ '♥' if p.liked else '♡' }}</button></form>
<b> {{ p.likes }} beğeni</b>
{% if p.caption %}<p><b>{{ p.username }}</b> {{ p.caption }}</p>{% endif %}
{% for c in p.comments %}<div><b>{{ c.username }}</b> {{ c.body }}</div>{% endfor %}
<form class="satir" method="post" action="{{ url_for('yorum', pid=p.id) }}">
<input name="body" placeholder="Yorum yaz…" required><button class="btn">Gönder</button></form>
{% if p.user_id == me.id %}<form method="post" action="{{ url_for('sil', pid=p.id) }}" onsubmit="return confirm('Silinsin mi?')">
<button class="btn ikincil" style="margin-top:8px">Gönderiyi sil</button></form>{% endif %}
</div></article>{% else %}<p class="soluk">{{ bos }}</p>{% endfor %}"""


def sayfa(sablon, **ctx):
    """Verilen şablonu doldurur ve TEMEL iskeletin içine yerleştirip döndürür."""
    ctx.setdefault("me", ben())  # Giriş yapan kullanıcıyı şablona ekle
    icerik = render_template_string(sablon, **ctx)
    return render_template_string(TEMEL, icerik=icerik, me=ctx["me"])


# ============================================================
# HESAP İŞLEMLERİ (kayıt, giriş, çıkış)
# ============================================================
# Kayıt ve giriş sayfalarının ortak formu
HESAP = """<div class="kart"><div class="alt"><h2>{{ baslik }}</h2>
<form method="post"><p><input name="username" placeholder="Kullanıcı adı" required></p>
<p><input name="password" type="password" placeholder="Şifre" required></p>
<button class="btn">{{ baslik }}</button></form>
<p class="soluk">{{ alt|safe }}</p></div></div>"""


@app.route("/kayit", methods=["GET", "POST"])
def kayit():
    """Yeni hesap oluşturur."""
    if request.method == "POST":  # Form gönderildiyse
        ad = request.form["username"].strip().lower()  # Boşlukları sil, küçük harfe çevir
        if not ad.isalnum():  # Sadece harf ve rakam kabul et
            flash("Kullanıcı adı sadece harf ve rakam içerebilir.")
        else:
            try:
                # Şifreyi hash'leyerek kaydet
                db().execute("INSERT INTO users(username,password) VALUES(?,?)",
                             (ad, generate_password_hash(request.form["password"])))
                db().commit()
                flash("Hesap oluşturuldu. Giriş yap.")
                return redirect(url_for("giris"))
            except sqlite3.IntegrityError:  # Aynı kullanıcı adı varsa
                flash("Bu kullanıcı adı alınmış.")
    return sayfa(HESAP, baslik="Kayıt ol", alt=f'Hesabın var mı? <a href="{url_for("giris")}"><b>Giriş yap</b></a>')


@app.route("/giris", methods=["GET", "POST"])
def giris():
    """Kullanıcı adı ve şifreyi kontrol edip oturum açar."""
    if request.method == "POST":
        u = db().execute("SELECT * FROM users WHERE username=?",
                         (request.form["username"].strip().lower(),)).fetchone()
        # Kullanıcı varsa ve şifre doğruysa
        if u and check_password_hash(u["password"], request.form["password"]):
            session["uid"] = u["id"]  # Kullanıcı numarasını oturuma yaz
            return redirect(url_for("akis"))
        flash("Kullanıcı adı veya şifre yanlış.")
    return sayfa(HESAP, baslik="Giriş yap", alt=f'Hesabın yok mu? <a href="{url_for("kayit")}"><b>Kayıt ol</b></a>')


@app.route("/cikis")
def cikis():
    """Oturumu kapatır."""
    session.clear()
    return redirect(url_for("giris"))


# ============================================================
# GÖNDERİ İŞLEMLERİ
# ============================================================
# Gönderileri, sahibinin kullanıcı adıyla birlikte getiren sorgunun başı
SORGU = "SELECT p.*, u.username FROM posts p JOIN users u ON u.id=p.user_id "


@app.route("/")
@giris_gerekli
def akis():
    """Ana sayfa: kendi gönderilerin ve takip ettiklerinin gönderileri, yeniden eskiye."""
    rows = db().execute(SORGU + "WHERE p.user_id=? OR p.user_id IN "
                        "(SELECT followed FROM follows WHERE follower=?) ORDER BY p.id DESC",
                        (session["uid"], session["uid"])).fetchall()
    return sayfa(GONDERI, posts=gonderi_detay(rows),
                 bos="Akışın boş. Keşfet'ten birilerini takip et ya da ilk fotoğrafını paylaş.")


@app.route("/kesfet")
@giris_gerekli
def kesfet():
    """Herkesin son elli gönderisi."""
    rows = db().execute(SORGU + "ORDER BY p.id DESC LIMIT 50").fetchall()
    return sayfa(GONDERI, posts=gonderi_detay(rows), bos="Henüz kimse paylaşım yapmadı.")


@app.route("/paylas", methods=["GET", "POST"])
@giris_gerekli
def yukle():
    """Fotoğraf yükleme sayfası."""
    if request.method == "POST":
        f = request.files.get("image")
        # Dosya uzantısını al (örnek: jpg)
        uz = f.filename.rsplit(".", 1)[-1].lower() if f and "." in f.filename else ""
        if uz not in IZINLI:
            flash("Fotoğraf seç: png, jpg, gif veya webp.")
        else:
            ad = f"{uuid.uuid4().hex}.{uz}"     # Benzersiz dosya adı üret
            f.save(os.path.join(UPLOADS, ad))   # Dosyayı uploads klasörüne kaydet
            db().execute("INSERT INTO posts(user_id,image,caption) VALUES(?,?,?)",
                         (session["uid"], ad, request.form.get("caption", "").strip()))
            db().commit()
            return redirect(url_for("akis"))
    return sayfa("""<div class="kart"><div class="alt"><h2>Fotoğraf paylaş</h2>
<form method="post" enctype="multipart/form-data">
<p><input type="file" name="image" accept="image/*" required></p>
<p><textarea name="caption" rows="3" placeholder="Açıklama yaz…"></textarea></p>
<button class="btn">Paylaş</button></form></div></div>""")


@app.route("/uploads/<ad>")
def dosya(ad):
    """Yüklenmiş bir fotoğrafı tarayıcıya gönderir."""
    return send_from_directory(UPLOADS, ad)


@app.post("/begen/<int:pid>")
@giris_gerekli
def begen(pid):
    """Beğeni aç/kapa: beğenildiyse kaldırır, beğenilmediyse ekler."""
    d = db()
    if d.execute("SELECT 1 FROM likes WHERE user_id=? AND post_id=?", (session["uid"], pid)).fetchone():
        d.execute("DELETE FROM likes WHERE user_id=? AND post_id=?", (session["uid"], pid))
    else:
        d.execute("INSERT INTO likes VALUES(?,?)", (session["uid"], pid))
    d.commit()
    return redirect(request.referrer or url_for("akis"))  # Geldiği sayfaya dön


@app.post("/yorum/<int:pid>")
@giris_gerekli
def yorum(pid):
    """Gönderiye yorum ekler."""
    body = request.form.get("body", "").strip()
    if body:  # Boş yorum ekleme
        db().execute("INSERT INTO comments(user_id,post_id,body) VALUES(?,?,?)", (session["uid"], pid, body))
        db().commit()
    return redirect(request.referrer or url_for("akis"))


@app.post("/sil/<int:pid>")
@giris_gerekli
def sil(pid):
    """Gönderiyi siler. Sadece gönderinin sahibi silebilir."""
    p = db().execute("SELECT * FROM posts WHERE id=?", (pid,)).fetchone()
    if not p or p["user_id"] != session["uid"]:
        abort(403)  # Yetkisiz: başkasının gönderisi
    db().execute("DELETE FROM posts WHERE id=?", (pid,))  # Beğeni ve yorumlar da otomatik silinir
    db().commit()
    try:
        os.remove(os.path.join(UPLOADS, p["image"]))  # Fotoğraf dosyasını da sil
    except OSError:
        pass
    flash("Gönderi silindi.")
    return redirect(url_for("akis"))


# ============================================================
# PROFİL
# ============================================================
@app.route("/u/<ad>", methods=["GET", "POST"])
@giris_gerekli
def profil(ad):
    """Kullanıcı profili: gönderi, takipçi ve takip sayıları, fotoğraf ızgarası.
    Kendi profilinde biyografi düzenlenir, başkasınınkinde takip edilir."""
    d = db()
    u = d.execute("SELECT * FROM users WHERE username=?", (ad,)).fetchone()
    if not u:
        abort(404)  # Böyle bir kullanıcı yok

    if request.method == "POST":
        if u["id"] == session["uid"]:
            # Kendi profili: biyografiyi kaydet (en fazla yüz elli karakter)
            d.execute("UPDATE users SET bio=? WHERE id=?", (request.form.get("bio", "")[:150], u["id"]))
        elif d.execute("SELECT 1 FROM follows WHERE follower=? AND followed=?", (session["uid"], u["id"])).fetchone():
            # Zaten takip ediyor: takibi bırak
            d.execute("DELETE FROM follows WHERE follower=? AND followed=?", (session["uid"], u["id"]))
        else:
            # Takip etmiyor: takip et
            d.execute("INSERT INTO follows VALUES(?,?)", (session["uid"], u["id"]))
        d.commit()
        return redirect(url_for("profil", ad=ad))

    # Sayı döndüren kısa yardımcı (gönderi, takipçi, takip sayıları için)
    s = lambda q: d.execute(q, (u["id"],)).fetchone()[0]

    return sayfa("""<div class="kart"><div class="alt">
<h2>@{{ u.username }}</h2>
<p><b>{{ n_post }}</b> gönderi · <b>{{ n_takipci }}</b> takipçi · <b>{{ n_takip }}</b> takip</p>
<p>{{ u.bio }}</p>
<form method="post">{% if u.id == me.id %}
<div class="satir"><input name="bio" value="{{ u.bio }}" placeholder="Biyografi"><button class="btn ikincil">Kaydet</button></div>
{% elif takip %}<button class="btn ikincil">Takibi bırak</button>{% else %}<button class="btn">Takip et</button>{% endif %}
</form></div></div>
<div class="izgara">{% for p in posts %}<img src="{{ url_for('dosya', ad=p.image) }}" alt="{{ p.caption }}">{% endfor %}</div>
{% if not posts %}<p class="soluk">Henüz gönderi yok.</p>{% endif %}""",
        u=u, posts=d.execute("SELECT * FROM posts WHERE user_id=? ORDER BY id DESC", (u["id"],)).fetchall(),
        n_post=s("SELECT COUNT(*) FROM posts WHERE user_id=?"),
        n_takipci=s("SELECT COUNT(*) FROM follows WHERE followed=?"),
        n_takip=s("SELECT COUNT(*) FROM follows WHERE follower=?"),
        takip=d.execute("SELECT 1 FROM follows WHERE follower=? AND followed=?", (session["uid"], u["id"])).fetchone())


# ============================================================
# BAŞLAT
# ============================================================
if __name__ == "__main__":
    app.run(debug=True) # Sunucuyu başlat (debug: hata ayrıntılarını gösterir)

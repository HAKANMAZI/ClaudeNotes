"""Play Kazanç - Google Play uygulama kazanç tahmini ve trend takibi."""
import os
import sqlite3
import time
from datetime import datetime

from flask import Flask, g, redirect, render_template, request, url_for, flash

from tahmin import gelir_tahmini

DEMO = os.environ.get("DEMO") == "1"
VT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "veri.db")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "play-kazanc")


# ---------- Veri kaynağı ----------
if DEMO:
    from demo import demo_ara as _ara, demo_app as _detay
else:
    from google_play_scraper import app as _gp_app, search as _gp_search

    def _ara(kelime, ulke, dil):
        return _gp_search(kelime, lang=dil, country=ulke, n_hits=30)

    def _detay(app_id, ulke, dil):
        return _gp_app(app_id, lang=dil, country=ulke)


def detay_getir(app_id, ulke="tr", dil="tr"):
    return _detay(app_id, ulke, dil)


def ara(kelime, ulke="tr", dil="tr"):
    return _ara(kelime, ulke, dil)


# ---------- Veritabanı ----------
def vt():
    if "vt" not in g:
        g.vt = sqlite3.connect(VT)
        g.vt.row_factory = sqlite3.Row
    return g.vt


@app.teardown_appcontext
def vt_kapat(_):
    d = g.pop("vt", None)
    if d:
        d.close()


def vt_kur():
    with sqlite3.connect(VT) as d:
        d.executescript("""
        CREATE TABLE IF NOT EXISTS takip (
            app_id TEXT PRIMARY KEY, baslik TEXT, ikon TEXT, eklenme REAL);
        CREATE TABLE IF NOT EXISTS anlik (
            app_id TEXT, zaman REAL, indirme INTEGER, puan REAL, oy INTEGER);
        """)


def anlik_kaydet(a):
    vt().execute("INSERT INTO anlik VALUES (?,?,?,?,?)",
                 (a["appId"], time.time(), a.get("realInstalls") or a.get("minInstalls") or 0,
                  a.get("score") or 0, a.get("ratings") or 0))
    vt().commit()


def gunluk_indirme_gecmisten(app_id):
    """Kayıtlı anlık görüntülerden günlük indirme hızını hesapla."""
    satirlar = vt().execute(
        "SELECT zaman, indirme FROM anlik WHERE app_id=? ORDER BY zaman", (app_id,)).fetchall()
    if len(satirlar) < 2:
        return None
    ilk, son = satirlar[0], satirlar[-1]
    gun = (son["zaman"] - ilk["zaman"]) / 86400
    if gun < 0.5:
        return None
    return max(0, (son["indirme"] - ilk["indirme"]) / gun)


# ---------- Şablon yardımcıları ----------
@app.template_filter("sayi")
def sayi(n):
    n = n or 0
    for esik, ek in ((1e9, " milyar"), (1e6, " milyon"), (1e3, " bin")):
        if n >= esik:
            return f"{n / esik:.1f}".rstrip("0").rstrip(".").replace(".", ",") + ek
    return str(int(n))


@app.template_filter("tarih")
def tarih(z):
    return datetime.fromtimestamp(z).strftime("%d.%m.%Y %H:%M")


# ---------- Sayfalar ----------
@app.route("/")
def anasayfa():
    kelime = request.args.get("q", "").strip()
    ulke = request.args.get("ulke", "tr")
    sonuclar = []
    if kelime:
        try:
            for s in ara(kelime, ulke):
                try:
                    a = detay_getir(s["appId"], ulke)
                except Exception:
                    continue
                a["tahmin"] = gelir_tahmini(a, ulke)
                sonuclar.append(a)
            sonuclar.sort(key=lambda x: x["tahmin"]["aylik_orta"], reverse=True)
        except Exception as e:
            flash(f"Google Play'e ulaşılamadı: {e}")
    return render_template("ara.html", kelime=kelime, ulke=ulke, sonuclar=sonuclar)


@app.route("/uygulama/<app_id>")
def uygulama(app_id):
    ulke = request.args.get("ulke", "tr")
    try:
        a = detay_getir(app_id, ulke)
    except Exception as e:
        flash(f"Uygulama bulunamadı: {e}")
        return redirect(url_for("anasayfa"))
    takipte = vt().execute("SELECT 1 FROM takip WHERE app_id=?", (app_id,)).fetchone()
    if takipte:
        anlik_kaydet(a)
    t = gelir_tahmini(a, ulke, gunluk_indirme_gecmisten(app_id))
    gecmis = vt().execute(
        "SELECT * FROM anlik WHERE app_id=? ORDER BY zaman DESC LIMIT 30", (app_id,)).fetchall()
    return render_template("uygulama.html", a=a, t=t, ulke=ulke,
                           takipte=bool(takipte), gecmis=gecmis)


@app.post("/takip/<app_id>")
def takip_ekle(app_id):
    a = detay_getir(app_id)
    vt().execute("INSERT OR REPLACE INTO takip VALUES (?,?,?,?)",
                 (app_id, a["title"], a.get("icon"), time.time()))
    vt().commit()
    anlik_kaydet(a)
    flash(f"{a['title']} takibe alındı.")
    return redirect(url_for("uygulama", app_id=app_id))


@app.post("/takip/<app_id>/sil")
def takip_sil(app_id):
    vt().execute("DELETE FROM takip WHERE app_id=?", (app_id,))
    vt().commit()
    return redirect(url_for("trendler"))


@app.post("/guncelle")
def guncelle():
    """Takipteki tüm uygulamaların güncel verisini çek (günde bir çalıştırın)."""
    adet = 0
    for r in vt().execute("SELECT app_id FROM takip").fetchall():
        try:
            anlik_kaydet(detay_getir(r["app_id"]))
            adet += 1
        except Exception:
            pass
    flash(f"{adet} uygulama güncellendi.")
    return redirect(url_for("trendler"))


@app.route("/trendler")
def trendler():
    liste = []
    for r in vt().execute("SELECT * FROM takip").fetchall():
        s = vt().execute("SELECT * FROM anlik WHERE app_id=? ORDER BY zaman",
                         (r["app_id"],)).fetchall()
        if not s:
            continue
        ilk, son = s[0], s[-1]
        gun = max((son["zaman"] - ilk["zaman"]) / 86400, 0)
        hiz = (son["indirme"] - ilk["indirme"]) / gun if gun >= 0.5 else None
        buyume = ((son["indirme"] - ilk["indirme"]) / ilk["indirme"] * 100) if ilk["indirme"] else 0
        oy_hiz = (son["oy"] - ilk["oy"]) / gun if gun >= 0.5 else None
        liste.append(dict(r) | {"indirme": son["indirme"], "puan": son["puan"], "hiz": hiz,
                                "buyume": buyume, "oy_hiz": oy_hiz, "olcum": len(s),
                                "gun": gun})
    liste.sort(key=lambda x: (x["hiz"] or 0), reverse=True)
    return render_template("trendler.html", liste=liste)


vt_kur()

if __name__ == "__main__":
    app.run(debug=True, port=5000)

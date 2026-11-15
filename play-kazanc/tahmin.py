"""Google Play uygulamaları için kaba gelir tahmini.

Not: Google Play gerçek gelir/indirme verisi paylaşmaz. Buradaki sonuçlar
kamuya açık verilerden (toplam indirme, fiyat, reklam/uygulama içi satın alma,
kategori, yayın tarihi) türetilmiş YAKLAŞIK aralıklardır.
"""
from datetime import datetime, date

GOOGLE_PAYI = 0.30  # Google komisyonu (basitleştirilmiş)

# Kategori bazlı varsayımlar: (aylık aktif oran, ödeme yapan oranı, aylık ödeyen başı harcama $)
KATEGORI = {
    "oyun":     (0.10, 0.020, 12.0),
    "sosyal":   (0.20, 0.004, 6.0),
    "verimlilik": (0.12, 0.010, 5.0),
    "eglence":  (0.10, 0.006, 6.0),
    "egitim":   (0.08, 0.010, 8.0),
    "saglik":   (0.08, 0.012, 9.0),
    "arac":     (0.06, 0.004, 4.0),
    "diger":    (0.08, 0.006, 6.0),
}

# Ülke bazlı reklam geliri: 1000 gösterim başına $ (eCPM)
ECPM = {"tr": 1.2, "us": 8.0, "de": 6.0, "gb": 6.5, "global": 3.0}

GUNLUK_GOSTERIM = 6  # aktif kullanıcı başına günlük reklam gösterimi


def kategori_grubu(genre_id: str) -> str:
    g = (genre_id or "").upper()
    if g.startswith("GAME"):
        return "oyun"
    tablo = {
        "SOCIAL": "sosyal", "COMMUNICATION": "sosyal", "DATING": "sosyal",
        "PRODUCTIVITY": "verimlilik", "BUSINESS": "verimlilik", "FINANCE": "verimlilik",
        "ENTERTAINMENT": "eglence", "MUSIC_AND_AUDIO": "eglence", "VIDEO_PLAYERS": "eglence",
        "PHOTOGRAPHY": "eglence", "EDUCATION": "egitim", "BOOKS_AND_REFERENCE": "egitim",
        "HEALTH_AND_FITNESS": "saglik", "MEDICAL": "saglik",
        "TOOLS": "arac", "PERSONALIZATION": "arac",
    }
    return tablo.get(g, "diger")


def _gun_sayisi(yayin: str | None) -> int:
    if not yayin:
        return 365
    for bicim in ("%b %d, %Y", "%d %b %Y", "%Y-%m-%d"):
        try:
            d = datetime.strptime(yayin, bicim).date()
            return max(30, (date.today() - d).days)
        except ValueError:
            continue
    return 365


def gelir_tahmini(app: dict, ulke: str = "tr", gunluk_indirme: float | None = None) -> dict:
    indirme = app.get("realInstalls") or app.get("minInstalls") or 0
    grup = kategori_grubu(app.get("genreId"))
    aktif_oran, odeyen_oran, harcama = KATEGORI[grup]
    gun = _gun_sayisi(app.get("released"))

    if gunluk_indirme is None:
        # Geçmiş veri yoksa: ömür boyu ortalama (yeni uygulamalarda yüksek çıkar)
        gunluk_indirme = indirme / gun

    # Aylık aktif kullanıcı: toplamın bir kısmı, ama son 90 günün indirmesinden az olamaz
    mau = max(indirme * aktif_oran, gunluk_indirme * 30 * 0.5)
    dau = mau * 0.3

    ucretli = 0.0
    if not app.get("free", True) and app.get("price"):
        ucretli = gunluk_indirme * 30 * float(app["price"]) * (1 - GOOGLE_PAYI)

    iap = 0.0
    if app.get("offersIAP"):
        iap = mau * odeyen_oran * harcama * (1 - GOOGLE_PAYI)

    reklam = 0.0
    if app.get("containsAds"):
        reklam = dau * GUNLUK_GOSTERIM * 30 * ECPM.get(ulke, ECPM["global"]) / 1000

    orta = ucretli + iap + reklam
    return {
        "grup": grup,
        "toplam_indirme": indirme,
        "gunluk_indirme": round(gunluk_indirme),
        "aylik_aktif": round(mau),
        "ucretli": round(ucretli),
        "iap": round(iap),
        "reklam": round(reklam),
        "aylik_dusuk": round(orta * 0.4),
        "aylik_orta": round(orta),
        "aylik_yuksek": round(orta * 2.5),
    }

"""İnternetsiz deneme için örnek veri (DEMO=1). Gerçek veri değildir."""
import random

ORNEK = [
    dict(appId="com.ornek.kelimeoyunu", title="Örnek Kelime Oyunu", developer="Demo Studio",
         genreId="GAME_WORD", genre="Kelime", realInstalls=12_400_000, score=4.5, ratings=310_000,
         free=True, price=0, offersIAP=True, containsAds=True, released="Mar 2, 2021"),
    dict(appId="com.ornek.butce", title="Örnek Bütçe Takip", developer="Demo Yazılım",
         genreId="FINANCE", genre="Finans", realInstalls=850_000, score=4.7, ratings=22_000,
         free=True, price=0, offersIAP=True, containsAds=False, released="Jan 15, 2023"),
    dict(appId="com.ornek.fener", title="Örnek El Feneri", developer="Demo Araçlar",
         genreId="TOOLS", genre="Araçlar", realInstalls=54_000_000, score=4.2, ratings=900_000,
         free=True, price=0, offersIAP=False, containsAds=True, released="Jun 1, 2016"),
    dict(appId="com.ornek.pro", title="Örnek Pro Not Defteri", developer="Demo Yazılım",
         genreId="PRODUCTIVITY", genre="Verimlilik", realInstalls=120_000, score=4.8, ratings=5_400,
         free=False, price=2.99, offersIAP=False, containsAds=False, released="Sep 9, 2022"),
]


def demo_ara(kelime, ulke, dil):
    return [{"appId": a["appId"]} for a in ORNEK]


def demo_app(app_id, ulke, dil):
    for a in ORNEK:
        if a["appId"] == app_id:
            b = dict(a, icon="https://placehold.co/96x96?text=" + a["title"][7:9],
                     summary="Demo uygulaması.", url="https://play.google.com/store/apps/details?id=" + app_id)
            b["realInstalls"] += random.randint(0, 5000)  # zamanla artış taklidi
            return b
    raise ValueError("bulunamadı")

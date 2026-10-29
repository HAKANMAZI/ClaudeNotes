"""İnternet olmadan arayüzü denemek için sahte veri (BIST_TAKIP_DEMO=1)."""

import random
from datetime import datetime, timedelta

import pandas as pd

_TITLES = [
    "Yeni İş İlişkisi",
    "İhale Sonucu Hakkında",
    "Sözleşme İmzalanması",
    "Finansal Rapor",
    "Kar Payı Dağıtım İşlemlerine İlişkin Bildirim",
    "Payların Geri Alınmasına İlişkin Bildirim",
    "Özel Durum Açıklaması (Genel)",
    "Haber ve Söylentilere İlişkin Açıklama",
    "Genel Kurul İşlemlerine İlişkin Bildirim",
    "Kredi Derecelendirmesi",
]


class DemoTicker:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self._rng = random.Random(symbol)

    @property
    def fast_info(self) -> dict:
        price = round(self._rng.uniform(20, 400), 2)
        return {
            "last_price": price,
            "previous_close": round(price / (1 + self._rng.uniform(-0.04, 0.04)), 2),
            "pe_ratio": round(self._rng.uniform(3, 25), 1),
            "pb_ratio": round(self._rng.uniform(0.5, 4), 2),
            "market_cap": self._rng.uniform(5e10, 8e11),
            "year_low": round(price * 0.7, 2),
            "year_high": round(price * 1.3, 2),
        }

    @property
    def news(self) -> pd.DataFrame:
        now = datetime.now()
        rows = []
        for _ in range(8):
            when = now - timedelta(hours=self._rng.randint(1, 24 * 30))
            rows.append({
                "Date": when.strftime("%d.%m.%Y %H:%M:%S"),
                "Title": self._rng.choice(_TITLES),
                "URL": f"https://www.kap.org.tr/tr/Bildirim/{self._rng.randint(1_000_000, 9_999_999)}",
            })
        return pd.DataFrame(rows)

    @property
    def calendar(self) -> pd.DataFrame:
        start = datetime.now() + timedelta(days=self._rng.randint(1, 40))
        return pd.DataFrame([{
            "StartDate": start.strftime("%d.%m.%Y"),
            "EndDate": (start + timedelta(days=10)).strftime("%d.%m.%Y"),
            "Subject": "Finansal Rapor",
            "Period": "9 Aylık",
            "Year": start.year,
        }])

    def history(self, period: str = "1y") -> pd.DataFrame:
        days = {"1mo": 22, "3mo": 66, "6mo": 130, "1y": 252, "2y": 504, "5y": 1260}.get(period, 252)
        index = pd.bdate_range(end=datetime.now(), periods=days)
        price, closes = self._rng.uniform(20, 400), []
        for _ in index:
            price *= 1 + self._rng.gauss(0.0005, 0.02)
            closes.append(price)
        return pd.DataFrame({"Close": closes}, index=index)

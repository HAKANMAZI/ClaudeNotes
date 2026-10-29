import pandas as pd

from bist_takip import data
from bist_takip.demo import DemoTicker
from bist_takip.watchlist import WATCHLIST


class BrokenTicker:
    def __init__(self, symbol):
        pass

    @property
    def fast_info(self):
        raise RuntimeError("ağ hatası")

    @property
    def news(self):
        raise RuntimeError("ağ hatası")


class FixedTicker:
    def __init__(self, symbol):
        pass

    fast_info = {"last_price": 110.0, "previous_close": 100.0, "pe_ratio": 5.0, "market_cap": 2e9}
    news = pd.DataFrame([
        {"Date": "01.10.2026 10:00:00", "Title": "Finansal Rapor", "URL": "u1"},
        {"Date": "02.10.2026 09:30:00", "Title": "Yeni İş İlişkisi", "URL": "u2"},
    ])


def test_watchlist_has_20_unique_companies():
    assert len(WATCHLIST) == 20
    assert len({c.ticker for c in WATCHLIST}) == 20
    assert [c.rank for c in WATCHLIST] == list(range(1, 21))


def test_quote_computes_change_and_market_cap():
    row = data.fetch_quote(WATCHLIST[0], FixedTicker)
    assert round(row["Günlük %"], 6) == 10.0
    assert row["Piyasa Değeri (mn TL)"] == 2000.0
    assert row["PD/DD"] is None
    assert row["Hata"] == ""


def test_failures_do_not_crash():
    quotes = data.fetch_quotes(WATCHLIST[:3], BrokenTicker)
    assert len(quotes) == 3
    assert quotes["Hata"].str.contains("ağ hatası").all()

    news, errors = data.fetch_all_news(WATCHLIST[:3], BrokenTicker)
    assert news.empty and len(errors) == 3


def test_news_sorted_and_categorized():
    news, errors = data.fetch_all_news(WATCHLIST[:2], FixedTicker)
    assert not errors
    assert len(news) == 4
    assert news["Tarih"].is_monotonic_decreasing
    assert news.iloc[0]["Kategori"] == "İhale / Sözleşme"


def test_parse_kap_date():
    assert data.parse_kap_date("29.12.2025 19:21:18") == pd.Timestamp(2025, 12, 29, 19, 21, 18)
    assert data.parse_kap_date("bozuk") is None


def test_demo_ticker_works_end_to_end():
    quotes = data.fetch_quotes(WATCHLIST, DemoTicker)
    assert quotes["Fiyat"].notna().all()
    news, errors = data.fetch_all_news(WATCHLIST, DemoTicker)
    assert not errors and len(news) == 160

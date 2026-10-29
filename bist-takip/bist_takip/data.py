"""Fiyat ve KAP verilerini borsapy üzerinden çeker.

Her fonksiyon bir `ticker_factory` alır; testlerde sahte nesne verilebilir.
Bir şirketin verisi alınamazsa o satır boş kalır, uygulama çökmez.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any

import pandas as pd

from bist_takip.categories import categorize
from bist_takip.watchlist import Company

TickerFactory = Callable[[str], Any]

QUOTE_COLUMNS = [
    "Sıra", "Kod", "Şirket", "Sektör", "Fiyat", "Günlük %", "F/K", "PD/DD",
    "Piyasa Değeri (mn TL)", "52H Düşük", "52H Yüksek", "Hata",
]
NEWS_COLUMNS = ["Tarih", "Kod", "Şirket", "Kategori", "Başlık", "Link"]


def default_ticker_factory(symbol: str) -> Any:
    import borsapy as bp

    return bp.Ticker(symbol)


def _get(info: Any, key: str) -> float | None:
    try:
        value = info[key]
    except Exception:
        return None
    return None if value is None or pd.isna(value) else float(value)


def fetch_quote(company: Company, ticker_factory: TickerFactory = default_ticker_factory) -> dict:
    row: dict[str, Any] = {
        "Sıra": company.rank, "Kod": company.ticker, "Şirket": company.name,
        "Sektör": company.sector, "Hata": "",
    }
    try:
        info = ticker_factory(company.ticker).fast_info
        price = _get(info, "last_price")
        prev = _get(info, "previous_close")
        market_cap = _get(info, "market_cap")
        row.update({
            "Fiyat": price,
            "Günlük %": (price / prev - 1) * 100 if price and prev else None,
            "F/K": _get(info, "pe_ratio"),
            "PD/DD": _get(info, "pb_ratio"),
            "Piyasa Değeri (mn TL)": market_cap / 1e6 if market_cap else None,
            "52H Düşük": _get(info, "year_low"),
            "52H Yüksek": _get(info, "year_high"),
        })
    except Exception as e:
        row["Hata"] = f"Fiyat alınamadı: {e}"
    return row


def fetch_quotes(companies: list[Company], ticker_factory: TickerFactory = default_ticker_factory) -> pd.DataFrame:
    rows = [fetch_quote(c, ticker_factory) for c in companies]
    return pd.DataFrame(rows).reindex(columns=QUOTE_COLUMNS)


def parse_kap_date(value: Any) -> pd.Timestamp | None:
    if isinstance(value, datetime):
        return pd.Timestamp(value)
    for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%d.%m.%Y"):
        try:
            return pd.Timestamp(datetime.strptime(str(value).strip(), fmt))
        except ValueError:
            continue
    return None


def fetch_news(company: Company, ticker_factory: TickerFactory = default_ticker_factory) -> tuple[pd.DataFrame, str]:
    """Bir şirketin son KAP bildirimleri. (tablo, hata mesajı) döner."""
    try:
        raw = ticker_factory(company.ticker).news
    except Exception as e:
        return pd.DataFrame(columns=NEWS_COLUMNS), f"{company.ticker}: KAP bildirimleri alınamadı ({e})"
    if raw is None or raw.empty:
        return pd.DataFrame(columns=NEWS_COLUMNS), ""

    df = pd.DataFrame({
        "Tarih": raw["Date"].map(parse_kap_date),
        "Kod": company.ticker,
        "Şirket": company.name,
        "Kategori": raw["Title"].map(categorize),
        "Başlık": raw["Title"],
        "Link": raw["URL"],
    })
    return df, ""


def fetch_all_news(
    companies: list[Company], ticker_factory: TickerFactory = default_ticker_factory
) -> tuple[pd.DataFrame, list[str]]:
    frames, errors = [], []
    for company in companies:
        df, error = fetch_news(company, ticker_factory)
        if error:
            errors.append(error)
        if not df.empty:
            frames.append(df)
    if not frames:
        return pd.DataFrame(columns=NEWS_COLUMNS), errors
    news = pd.concat(frames, ignore_index=True)
    return news.sort_values("Tarih", ascending=False, na_position="last").reset_index(drop=True), errors


def fetch_history(symbol: str, period: str = "1y", ticker_factory: TickerFactory = default_ticker_factory) -> pd.DataFrame:
    return ticker_factory(symbol).history(period=period)


def fetch_calendar(company: Company, ticker_factory: TickerFactory = default_ticker_factory) -> pd.DataFrame:
    """KAP'ta beklenen bildirimler (ör. finansal rapor tarihleri)."""
    try:
        return ticker_factory(company.ticker).calendar
    except Exception:
        return pd.DataFrame()

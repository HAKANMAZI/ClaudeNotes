"""BIST 100 takip uygulaması.

Çalıştırmak için:  streamlit run app.py
İnternetsiz deneme: BIST_TAKIP_DEMO=1 streamlit run app.py
"""

import os

import pandas as pd
import plotly.express as px
import streamlit as st

from bist_takip import data
from bist_takip.categories import ALL_CATEGORIES, TENDER_CATEGORY
from bist_takip.seen import load_seen, save_seen
from bist_takip.watchlist import BY_TICKER, WATCHLIST

DEMO = os.environ.get("BIST_TAKIP_DEMO") == "1"
if DEMO:
    from bist_takip.demo import DemoTicker as ticker_factory
else:
    ticker_factory = data.default_ticker_factory

st.set_page_config(page_title="BIST 100 Takip", page_icon="📈", layout="wide")


@st.cache_data(ttl=15 * 60, show_spinner="Fiyatlar alınıyor...")
def load_quotes() -> pd.DataFrame:
    return data.fetch_quotes(WATCHLIST, ticker_factory)


@st.cache_data(ttl=10 * 60, show_spinner="KAP bildirimleri alınıyor...")
def load_news() -> tuple[pd.DataFrame, list[str]]:
    return data.fetch_all_news(WATCHLIST, ticker_factory)


@st.cache_data(ttl=60 * 60, show_spinner="Grafik verisi alınıyor...")
def load_history(symbol: str, period: str) -> pd.DataFrame:
    return data.fetch_history(symbol, period, ticker_factory)


@st.cache_data(ttl=6 * 60 * 60)
def load_calendar(symbol: str) -> pd.DataFrame:
    return data.fetch_calendar(BY_TICKER[symbol], ticker_factory)


def news_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("Gösterilecek bildirim yok.")
        return
    st.dataframe(
        df[["Yeni", "Tarih", "Kod", "Kategori", "Başlık", "Link"]],
        hide_index=True,
        width="stretch",
        column_config={
            "Yeni": st.column_config.TextColumn("", width="small"),
            "Tarih": st.column_config.DatetimeColumn(format="DD.MM.YYYY HH:mm"),
            "Link": st.column_config.LinkColumn("KAP", display_text="Aç"),
        },
    )


# --- Kenar çubuğu -----------------------------------------------------------
st.sidebar.title("📈 BIST 100 Takip")
if DEMO:
    st.sidebar.warning("Demo modu: veriler sahtedir.")
if st.sidebar.button("🔄 Verileri yenile", width="stretch"):
    st.cache_data.clear()

quotes = load_quotes()
news, news_errors = load_news()

if "seen" not in st.session_state:
    st.session_state.seen = load_seen()
seen: set[str] = st.session_state.seen
news["Yeni"] = news["Link"].map(lambda link: "" if link in seen else "🆕")
new_count = int((news["Yeni"] == "🆕").sum())

st.sidebar.metric("Okunmamış bildirim", new_count)
if st.sidebar.button("✅ Tümünü okundu say", width="stretch", disabled=new_count == 0):
    seen.update(news["Link"])
    save_seen(seen)
    st.rerun()

st.sidebar.caption(
    "Veriler borsapy üzerinden KAP ve borsa kaynaklarından alınır; gecikmeli olabilir. "
    "Yatırım tavsiyesi değildir."
)

tab_summary, tab_news, tab_tenders, tab_detail = st.tabs(
    ["📊 Özet", "📰 KAP Haberleri", "🏗️ İhaleler & Sözleşmeler", "🔍 Şirket Detayı"]
)

# --- Özet --------------------------------------------------------------------
with tab_summary:
    new_by_ticker = news[news["Yeni"] == "🆕"].groupby("Kod").size()
    tenders_30d = news[
        (news["Kategori"] == TENDER_CATEGORY)
        & (news["Tarih"] >= pd.Timestamp.now() - pd.Timedelta(days=30))
    ].groupby("Kod").size()
    summary = quotes.assign(
        **{
            "Yeni Bildirim": quotes["Kod"].map(new_by_ticker).fillna(0).astype(int),
            "İhale (30g)": quotes["Kod"].map(tenders_30d).fillna(0).astype(int),
        }
    )

    changes = summary["Günlük %"].dropna()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Yükselen", int((changes > 0).sum()))
    c2.metric("Düşen", int((changes < 0).sum()))
    c3.metric("Ortalama değişim", f"{changes.mean():+.2f}%" if not changes.empty else "-")
    c4.metric("Son 30 günde ihale/sözleşme", int(summary["İhale (30g)"].sum()))

    st.dataframe(
        summary.drop(columns=["Hata"]),
        hide_index=True,
        width="stretch",
        height=740,
        column_config={
            "Fiyat": st.column_config.NumberColumn(format="%.2f ₺"),
            "Günlük %": st.column_config.NumberColumn(format="%+.2f%%"),
            "F/K": st.column_config.NumberColumn(format="%.1f"),
            "PD/DD": st.column_config.NumberColumn(format="%.2f"),
            "Piyasa Değeri (mn TL)": st.column_config.NumberColumn(format="%,.0f"),
            "52H Düşük": st.column_config.NumberColumn(format="%.2f"),
            "52H Yüksek": st.column_config.NumberColumn(format="%.2f"),
        },
    )
    failed = summary[summary["Hata"] != ""]
    if not failed.empty:
        with st.expander(f"⚠️ {len(failed)} şirketin fiyatı alınamadı"):
            st.write(failed[["Kod", "Hata"]])

# --- KAP Haberleri ---------------------------------------------------------
with tab_news:
    f1, f2, f3 = st.columns([2, 2, 1])
    tickers = f1.multiselect("Şirket", [c.ticker for c in WATCHLIST], placeholder="Hepsi")
    categories = f2.multiselect("Kategori", ALL_CATEGORIES, placeholder="Hepsi")
    only_new = f3.toggle("Sadece yeniler")

    filtered = news
    if tickers:
        filtered = filtered[filtered["Kod"].isin(tickers)]
    if categories:
        filtered = filtered[filtered["Kategori"].isin(categories)]
    if only_new:
        filtered = filtered[filtered["Yeni"] == "🆕"]
    st.caption(f"{len(filtered)} bildirim")
    news_table(filtered)

    if news_errors:
        with st.expander(f"⚠️ {len(news_errors)} şirketin bildirimleri alınamadı"):
            for error in news_errors:
                st.write(error)

# --- İhaleler & Sözleşmeler ------------------------------------------------
with tab_tenders:
    st.caption(
        "KAP'taki 'Yeni İş İlişkisi', 'İhale', 'Sözleşme', 'Sipariş' gibi başlıklı bildirimler. "
        "Detay için KAP linkini açın."
    )
    tenders = news[news["Kategori"] == TENDER_CATEGORY]
    if tenders.empty:
        st.info("Son bildirimler arasında ihale veya sözleşme yok.")
    else:
        counts = tenders.groupby("Kod").size().sort_values(ascending=False).reset_index(name="Adet")
        st.plotly_chart(
            px.bar(counts, x="Kod", y="Adet", title="Şirket bazında ihale / sözleşme bildirimi"),
            width="stretch",
        )
        news_table(tenders)

# --- Şirket Detayı -----------------------------------------------------------
with tab_detail:
    symbol = st.selectbox(
        "Şirket",
        [c.ticker for c in WATCHLIST],
        format_func=lambda t: f"{BY_TICKER[t].rank}. {t} - {BY_TICKER[t].name}",
    )
    company = BY_TICKER[symbol]
    row = quotes[quotes["Kod"] == symbol].iloc[0]

    st.subheader(f"{company.name} ({symbol})")
    st.caption(f"{company.sector} · {company.note}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Fiyat",
        f"{row['Fiyat']:.2f} ₺" if pd.notna(row["Fiyat"]) else "-",
        f"{row['Günlük %']:+.2f}%" if pd.notna(row["Günlük %"]) else None,
    )
    m2.metric("F/K", f"{row['F/K']:.1f}" if pd.notna(row["F/K"]) else "-")
    m3.metric("PD/DD", f"{row['PD/DD']:.2f}" if pd.notna(row["PD/DD"]) else "-")
    m4.metric(
        "Piyasa Değeri",
        f"{row['Piyasa Değeri (mn TL)'] / 1000:,.1f} mr ₺" if pd.notna(row["Piyasa Değeri (mn TL)"]) else "-",
    )

    periods = {"1mo": "1 Ay", "3mo": "3 Ay", "6mo": "6 Ay", "1y": "1 Yıl", "2y": "2 Yıl", "5y": "5 Yıl"}
    period = st.segmented_control("Dönem", list(periods), format_func=periods.get, default="1y")
    try:
        history = load_history(symbol, period or "1y")
        if not history.empty:
            chart_data = history.rename_axis("Tarih").reset_index()
            st.plotly_chart(
                px.line(chart_data, x="Tarih", y="Close", labels={"Close": "Kapanış (₺)"}),
                width="stretch",
            )
    except Exception as e:
        st.warning(f"Fiyat geçmişi alınamadı: {e}")

    left, right = st.columns([3, 1])
    with left:
        st.markdown("**KAP bildirimleri**")
        news_table(news[news["Kod"] == symbol])
    with right:
        st.markdown("**Beklenen bildirimler**")
        calendar = load_calendar(symbol)
        if calendar.empty:
            st.caption("Bilgi yok.")
        else:
            st.dataframe(calendar, hide_index=True)
    st.link_button("KAP şirket listesi", "https://www.kap.org.tr/tr/bist-sirketler")

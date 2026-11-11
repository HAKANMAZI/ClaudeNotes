"""Fiş Takip - Streamlit sürümü.

index.html arayüzünü Streamlit içinde tam ekran gösterir.
Veriler ve API anahtarı tarayıcıda tutulur, sunucuda veri saklanmaz.
"""
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Fiş Takip", page_icon="🧾", layout="wide", initial_sidebar_state="collapsed")
# Streamlit başlığını ve kenar boşluklarını gizle, uygulamayı tam ekran yap
st.markdown(
    """<style>
    header, [data-testid="stHeader"], [data-testid="stToolbar"], footer {display:none !important}
    .block-container {padding:0 !important; max-width:100% !important}
    iframe {width:100% !important; height:100vh !important; border:0}
    </style>""",
    unsafe_allow_html=True,
)
# Arayüz dosyasını oku ve göster
html = (Path(__file__).parent / "index.html").read_text(encoding="utf-8")
components.html(html, height=900, scrolling=True)

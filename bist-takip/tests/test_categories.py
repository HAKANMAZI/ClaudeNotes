import pytest

from bist_takip.categories import TENDER_CATEGORY, categorize, is_tender


@pytest.mark.parametrize("title", [
    "Yeni İş İlişkisi",
    "İhale Sonucu Hakkında",
    "Sözleşme İmzalanması",
    "YENİ İŞ İLİŞKİSİ",
    "Önemli Sipariş Alımı",
])
def test_tenders(title):
    assert is_tender(title)


@pytest.mark.parametrize("title, category", [
    ("Esas Sözleşme Tadili", "Genel Kurul / Yönetim"),
    ("Finansal Rapor", "Finansal Rapor"),
    ("Kar Payı Dağıtım İşlemlerine İlişkin Bildirim", "Temettü"),
    ("Payların Geri Alınmasına İlişkin Bildirim", "Geri Alım"),
    ("Borçlanma Aracı İhracına İlişkin Bildirim", "Sermaye"),
    ("Haber ve Söylentilere İlişkin Açıklama", "Haber / Söylenti"),
    ("Özel Durum Açıklaması (Genel)", "Diğer"),
    ("", "Diğer"),
])
def test_other_categories(title, category):
    assert categorize(title) == category
    assert category != TENDER_CATEGORY

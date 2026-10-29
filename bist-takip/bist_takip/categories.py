"""KAP bildirim başlıklarını kategorilere ayırır."""

# Sıra önemli: ilk eşleşen kategori kullanılır.
CATEGORY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    # "Esas Sözleşme" bir ihale değildir; ihale kontrolünden önce yakalanır.
    ("Genel Kurul / Yönetim", ("genel kurul", "esas sözleşme")),
    ("İhale / Sözleşme", (
        "ihale", "yeni iş ilişkisi", "sözleşme", "sipariş", "iş alımı",
        "proje", "anlaşma", "kontrat", "tedarik",
    )),
    ("Finansal Rapor", ("finansal rapor", "faaliyet raporu", "finansal tablo", "bilanço")),
    ("Temettü", ("kar payı", "kâr payı", "temettü")),
    ("Geri Alım", ("geri alım", "geri alınması")),
    ("Sermaye", ("sermaye artırım", "bedelsiz", "bedelli", "pay satış", "borçlanma aracı", "ihraç", "ihrac")),
    ("Yatırım / Satın Alma", (
        "yatırım", "satın alma", "devralma", "birleşme", "iştirak", "pay alım", "maddi duran varlık",
    )),
    ("Genel Kurul / Yönetim", ("yönetim kurulu", "atama", "görev değişikliği")),
    ("Dava / Ceza", ("dava", "ceza", "soruşturma", "tahkim")),
    ("Kredi Derecelendirme", ("derecelendirme", "rating")),
    ("Haber / Söylenti", ("haber ve söylenti", "söylenti")),
]

DEFAULT_CATEGORY = "Diğer"
TENDER_CATEGORY = "İhale / Sözleşme"

ALL_CATEGORIES: list[str] = list(dict.fromkeys(name for name, _ in CATEGORY_KEYWORDS)) + [DEFAULT_CATEGORY]


def _normalize(text: str) -> str:
    # Türkçe büyük harfleri doğru küçült (İ -> i, I -> ı).
    return text.replace("İ", "i").replace("I", "ı").lower()


def categorize(title: str) -> str:
    normalized = _normalize(title or "")
    for name, keywords in CATEGORY_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return name
    return DEFAULT_CATEGORY


def is_tender(title: str) -> bool:
    return categorize(title) == TENDER_CATEGORY

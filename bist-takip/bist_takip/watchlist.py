"""Takip edilen 20 şirket. Sıra, en iyi adaydan başlayarak verilmiştir."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Company:
    rank: int
    ticker: str
    name: str
    sector: str
    note: str


WATCHLIST: list[Company] = [
    Company(1, "GARAN", "Garanti BBVA", "Banka", "Sektörün en kârlı bankası, faiz indirimlerinden faydalanır"),
    Company(2, "TCELL", "Turkcell", "Telekom", "Düşük F/K, güçlü nakit akışı; veri merkezi ve fiber büyüyor"),
    Company(3, "ENKAI", "Enka İnşaat", "İnşaat / Enerji", "Net nakit, döviz bazlı gelir, borcu çok az"),
    Company(4, "AKBNK", "Akbank", "Banka", "Düşük PD/DD, faiz düşüşünde marjı en çok artabilecek bankalardan"),
    Company(5, "CCOLA", "Coca-Cola İçecek", "Gıda / İçecek", "Orta Asya ve Pakistan'da güçlü büyüme"),
    Company(6, "MGROS", "Migros", "Perakende", "Gıda perakendesi lideri, online satışları büyüyor"),
    Company(7, "YKBNK", "Yapı Kredi", "Banka", "Çok ucuz, faiz indirimlerine en hassas banka"),
    Company(8, "ISCTR", "İş Bankası", "Banka", "İştirakleriyle birlikte değeri iskontolu"),
    Company(9, "KCHOL", "Koç Holding", "Holding", "Varlık değerine göre yüksek iskonto"),
    Company(10, "FROTO", "Ford Otosan", "Otomotiv", "İhracat ağırlıklı, yüksek temettü"),
    Company(11, "TUPRS", "Tüpraş", "Enerji", "Ucuz ve temettüsü yüksek, kârı rafineri marjlarına bağlı"),
    Company(12, "ASELS", "Aselsan", "Savunma", "Sipariş birikimi yüksek, değerlemesi pahalılaştı"),
    Company(13, "BIMAS", "BİM", "Perakende", "Çok kaliteli ama nadiren ucuz"),
    Company(14, "AEFES", "Anadolu Efes", "Gıda / İçecek", "Holding iskontosu yüksek, CCOLA büyümesinden pay alıyor"),
    Company(15, "SAHOL", "Sabancı Holding", "Holding", "Varlık değerine iskonto, enerji ve banka ağırlığı"),
    Company(16, "TTRAK", "Türk Traktör", "Otomotiv", "Pazar lideri, temettüsü güçlü; tarım döngüsüne bağlı"),
    Company(17, "PGSUS", "Pegasus", "Havacılık", "Filo ve rota büyümesi; yakıt ve kur riski"),
    Company(18, "THYAO", "Türk Hava Yolları", "Havacılık", "Çok düşük F/K, döviz bazlı gelir"),
    Company(19, "TOASO", "Tofaş", "Otomotiv", "Stellantis entegrasyonu büyüme fırsatı, geçiş riski"),
    Company(20, "SISE", "Şişecam", "Sanayi", "Defter değerinin altında, kârda dalgalanma"),
]

BY_TICKER: dict[str, Company] = {c.ticker: c for c in WATCHLIST}

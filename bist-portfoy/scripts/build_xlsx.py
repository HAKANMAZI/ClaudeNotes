from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.formatting.rule import ColorScaleRule, CellIsRule, FormulaRule
from openpyxl.comments import Comment
import datetime

stocks = [
 ("ASELS","Savunma / Elektronik","Yüksek ve istikrarlı büyüyen kâr","Düşük–orta, güçlü nakit akışı","Rekor sipariş bakiyesi, ihracat artışı","Çok Güçlü"),
 ("BIMAS","Gıda Perakende","Yüksek, enflasyona dayanıklı kâr","Net nakit","Mağaza ağı büyümesi, yurt dışı operasyonlar","Çok Güçlü"),
 ("THYAO","Havacılık","Yüksek kâr, düşük F/K","Filo (kira) borcu var; güçlü nakit","Filo genişlemesi, kargo büyümesi","Güçlü"),
 ("TUPRS","Enerji / Rafineri","Güçlü, marjlara bağlı döngüsel kâr","Net nakit","Yüksek temettü, yeşil dönüşüm yatırımları","Güçlü"),
 ("FROTO","Otomotiv","Güçlü ihracat kârı","Orta (yatırım dönemi borcu)","Yeni modeller, elektrikli araç kapasitesi","Güçlü"),
 ("MGROS","Gıda Perakende","İstikrarlı kâr, artan marj","Net nakit","Online satış ve mağaza büyümesi","Güçlü"),
 ("CCOLA","İçecek","Güçlü, büyüyen kâr","Orta, kontrollü","Orta Asya / Pakistan pazar büyümesi","Güçlü"),
 ("ENKAI","İnşaat / Enerji","İstikrarlı kâr","Güçlü net nakit","Yurt dışı projeler, yüksek nakit getirisi","Çok Güçlü"),
 ("TCELL","Telekom","İstikrarlı kâr, yüksek FAVÖK marjı","Orta, döviz riski hedge'li","Veri merkezi, 5G, dijital hizmetler","Güçlü"),
 ("KCHOL","Holding","Çeşitlendirilmiş güçlü kâr","Holding solo net nakit","Grup şirketlerinde büyüme, NAV iskontosu","Güçlü"),
]
indices = [("XU100","BIST 100"),("XU030","BIST 30")]

wb = Workbook(); ws = wb.active; ws.title = "Takip"; vd = wb.create_sheet("Veri")
F = "Arial"
def font(**k): return Font(name=F, **{"size":10, **k})
thin = Side(style="thin", color="BFBFBF"); B = Border(left=thin,right=thin,top=thin,bottom=thin)
center = Alignment(horizontal="center", vertical="center", wrap_text=True)
def fill(c): return PatternFill("solid", start_color=c, end_color=c)

# --- Veri sheet: one 6-col block per symbol
def block(k): return 1+6*k
def rng(col): c=L(col); return f"Veri!${c}$3:${c}$600"
blocks = {}
for k,(t,*_) in enumerate(stocks+[(i[0],) for i in indices]):
    s = block(k)
    is_idx = k >= len(stocks)
    row = (5+(k-len(stocks))) if is_idx else (10+k)
    vd.cell(1, s, f'="{"INDEXIST" if is_idx else "IST"}:"&Takip!$A${row}').font = font(bold=True)
    if is_idx:
        vd.cell(2, s+3, f'=GOOGLEFINANCE({L(s)}1,"close",TODAY()-420,TODAY())')
        blocks[t] = dict(date=s+3, close=s+4, vol=None)
    else:
        vd.cell(2, s, f'=GOOGLEFINANCE({L(s)}1,"all",TODAY()-420,TODAY())')
        blocks[t] = dict(date=s, close=s+4, vol=s+5)
vd.cell(1, 1).comment = Comment("Bu sayfa GOOGLEFINANCE ile ~420 günlük geçmişi çeker. Elle düzenlemeyin.", "Takip")

# --- Title
ws.merge_cells("A1:AL1")
ws["A1"] = "BIST SAĞLAM 10 HİSSE — TEMEL & TEKNİK PORTFÖY TAKİP TABLOSU"
ws["A1"].font = Font(name=F, size=18, bold=True, color="1F4E9E"); ws["A1"].alignment = center
ws.row_dimensions[1].height = 36
ws.merge_cells("A2:AL2")
ws["A2"] = '="Seçim kriteri: kârlılık, düşük/kontrollü borç, güçlü gelecek beklentisi · Veriler GOOGLEFINANCE (gecikmeli) · Güncelleme: "&TEXT(NOW(),"dd.mm.yyyy hh:mm")'
ws["A2"].font = font(italic=True, color="595959"); ws["A2"].alignment = center

ws["AD3"] = "Hedef %"; ws["AE3"] = 0.30
ws["AG3"] = "Stop %";  ws["AH3"] = 0.10
for c in ("AD3","AG3"): ws[c].font = font(bold=True); ws[c].alignment = Alignment(horizontal="right")
for c in ("AE3","AH3"):
    ws[c].font = font(color="0000FF", bold=True); ws[c].fill = fill("FFFF00"); ws[c].number_format = "0%"; ws[c].border = B

# --- Group headers (row 8) and column headers (row 9)
groups = [("A","B","HİSSE","D9E1F2"),("C","H","PERFORMANS (işlem günü)","FCE4D6"),
          ("I","M","HACİM","E2EFDA"),("N","V","FİYAT & TEKNİK","DDEBF7"),
          ("W","AC","TEMEL ANALİZ (kâr · borç · beklenti)","FFF2CC"),("AD","AL","RALLİ TAKİP BÖLÜMÜ","F8CBAD")]
heads = ["Şirket","Sektör","Gün","5","15","30","60","240",
 "Günlük Hacim","10 Gün Ort. Hacim","20 Gün Ort. Hacim","50 Gün Ort. Hacim","Yıllık Hacim",
 "Yıllık Fiyat","Fiyat (₺)","MA10","MA21","MA50","MA200",">MA10","> MA21","> MA50",
 "F/K","Piyasa Değeri","Hisse Başı Kâr (₺)","Kârlılık","Borç Durumu","Gelecek Beklentisi","Temel Not",
 "Giriş Fiyatı","Giriş Tarihi","Max Fiyat","Max Kazanç","Hedef Fiyat","Stop","Getiri","R/K Oranı","XU100'e Göre"]
from openpyxl.utils import column_index_from_string as CI
for a,b,txt,col in groups:
    ws.merge_cells(f"{a}8:{b}8"); c = ws[f"{a}8"]; c.value = txt
    c.font = font(bold=True, color="1F1F1F"); c.alignment = center
    for i in range(CI(a), CI(b)+1):
        ws.cell(8,i).fill = fill(col); ws.cell(8,i).border = B
        ws.cell(9,i).fill = fill(col)
for i,h in enumerate(heads,1):
    c = ws.cell(9,i,h); c.font = font(bold=True); c.alignment = center; c.border = B
ws.row_dimensions[9].height = 32
ws.cell(9,39,"n").font = font(color="A6A6A6")

# Index header labels
ws["A4"] = "ENDEKSLER"; ws["A4"].font = font(bold=True, color="1F4E9E")

def perf_formulas(r, b, idx=False):
    C = rng(b["close"]); n = f"$AM{r}"
    sym = f'"{"INDEXIST" if idx else "IST"}:"&$A{r}'
    f = {}
    f["AM"] = f"=COUNT({C})"
    f["C"] = f'=IFERROR(GOOGLEFINANCE({sym},"changepct")/100,INDEX({C},{n})/INDEX({C},{n}-1)-1)'
    for col,N in zip("DEFGH",(5,15,30,60,240)):
        f[col] = f'=IFERROR(INDEX({C},{n})/INDEX({C},{n}-{N})-1,"")'
    f["N"] = f'=IFERROR(SPARKLINE(INDEX({C},MAX(1,{n}-249)):INDEX({C},{n}),{{"charttype","line";"color","#1a73e8";"linewidth",1.5}}),"")'
    f["O"] = f'=IFERROR(GOOGLEFINANCE({sym},"price"),INDEX({C},{n}))'
    return f

# Index rows
for j,(t,name) in enumerate(indices):
    r = 5+j; b = blocks[t]
    ws.cell(r,1,t).font = font(bold=True, italic=True); ws.cell(r,2,name).font = font(italic=True)
    for col,v in perf_formulas(r,b,True).items(): ws[f"{col}{r}"] = v
    ws[f"O{r}"].number_format = "#,##0.00"
    for col in "CDEFGH": ws[f"{col}{r}"].number_format = "0.0%"
    for i in range(1,16): ws.cell(r,i).border = B; ws.cell(r,i).fill = fill("F2F2F2")
    ws.cell(r,39).font = font(color="A6A6A6")

xu = blocks["XU100"]
xu_tbl = f"Veri!${L(xu['date'])}$3:${L(xu['close'])}$600"
start = datetime.date(2026,1,2)
for k,(t,sec,kar,borc,bek,notu) in enumerate(stocks):
    r = 10+k; b = blocks[t]
    C = rng(b["close"]); V = rng(b["vol"]); D = rng(b["date"]); n = f"$AM{r}"
    tbl = f"Veri!${L(b['date'])}$3:${L(b['close'])}$600"
    ws[f"A{r}"] = t; ws[f"B{r}"] = sec
    f = perf_formulas(r,b)
    f.update({
     "I": f'=IFERROR(GOOGLEFINANCE("IST:"&$A{r},"volume"),INDEX({V},{n}))',
     "J": f'=IFERROR(AVERAGE(INDEX({V},{n}-9):INDEX({V},{n})),"")',
     "K": f'=IFERROR(AVERAGE(INDEX({V},{n}-19):INDEX({V},{n})),"")',
     "L": f'=IFERROR(AVERAGE(INDEX({V},{n}-49):INDEX({V},{n})),"")',
     "M": f'=IFERROR(SPARKLINE(INDEX({V},MAX(1,{n}-249)):INDEX({V},{n}),{{"charttype","column";"color","#7f7f7f"}}),"")',
     "P": f'=IFERROR(AVERAGE(INDEX({C},{n}-9):INDEX({C},{n})),"")',
     "Q": f'=IFERROR(AVERAGE(INDEX({C},{n}-20):INDEX({C},{n})),"")',
     "R": f'=IFERROR(AVERAGE(INDEX({C},{n}-49):INDEX({C},{n})),"")',
     "S": f'=IFERROR(AVERAGE(INDEX({C},{n}-199):INDEX({C},{n})),"")',
     "T": f'=IF($O{r}>P{r},"▲","▼")', "U": f'=IF($O{r}>Q{r},"▲","▼")', "V": f'=IF($O{r}>R{r},"▲","▼")',
     "W": f'=IFERROR(GOOGLEFINANCE("IST:"&$A{r},"pe"),"-")',
     "X": f'=IFERROR(GOOGLEFINANCE("IST:"&$A{r},"marketcap"),"-")',
     "Y": f'=IFERROR(GOOGLEFINANCE("IST:"&$A{r},"eps"),"-")',
     "AD": f'=IFERROR(VLOOKUP($AE{r}+0.999,{tbl},5,TRUE),"")',
     "AF": f'=IFERROR(MAX(_xlfn.MAXIFS({C},{D},">="&$AE{r}),$O{r}),"")',
     "AG": f'=IFERROR($AD{r}*(1+$AE$3),"")',
     "AH": f'=IFERROR($AD{r}*(1-$AH$3),"")',
     "AI": f'=IFERROR($O{r}/$AD{r}-1,"")',
     "AJ": f'=IFERROR(MAX(0,($AG{r}-$O{r}))/($O{r}-$AH{r}),"")',
     "AK": f'=IFERROR((1+$AI{r})/($O$5/VLOOKUP($AE{r}+0.999,{xu_tbl},2,TRUE))-1,"")',
     "AL": f'=IFERROR($O{r}/$AD{r}-1,"")',
    })
    for col,v in f.items(): ws[f"{col}{r}"] = v
    ws[f"AE{r}"] = start
    ws[f"Z{r}"], ws[f"AA{r}"], ws[f"AB{r}"], ws[f"AC{r}"] = kar, borc, bek, notu
    # formats
    for col in "CDEFGH": ws[f"{col}{r}"].number_format = "0.0%"
    for col in ("AC",): pass
    for col in ("I","J","K","L"): ws[f"{col}{r}"].number_format = '#,##0.0,," Mn"'
    for col in ("O","P","Q","R","S","AD","AF","AG","AH"): ws[f"{col}{r}"].number_format = '#,##0.00'
    ws[f"W{r}"].number_format = "0.0"; ws[f"Y{r}"].number_format = "0.00"
    ws[f"X{r}"].number_format = '#,##0.0,,," Mr₺"'
    ws[f"AE{r}"].number_format = "dd.mm.yyyy"
    for col in ("AG","AI","AK","AL"): pass
    ws[f"AG{r}"].number_format = '#,##0.00'
    for col in ("AI","AK"): ws[f"{col}{r}"].number_format = "0.0%"
    ws[f"AJ{r}"].number_format = "0.00"
    for i in range(1,39):
        c = ws.cell(r,i); c.border = B
        if c.font.b is not True: c.font = font()
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=i in (26,27,28))
    ws[f"A{r}"].font = font(bold=True); ws[f"A{r}"].fill = fill("D9E1F2")
    ws[f"B{r}"].alignment = Alignment(horizontal="left", vertical="center")
    ws[f"AE{r}"].font = font(color="0000FF"); ws[f"AE{r}"].fill = fill("FFFF00")
    ws[f"AD{r}"].fill = fill("FFF2CC")
    for col in ("Z","AA","AB"): ws[f"{col}{r}"].fill = fill("FFFBEA")
    ws.cell(r,39).font = font(color="A6A6A6")
    ws.row_dimensions[r].height = 34

# Max Kazanç column AG? -> we used AF=Max Fiyat; set AG header properly
# Header mapping fix: AD Giriş, AE Tarih, AF Max Fiyat, AG Hedef... ensure headers match formulas
hdr = {"AD":"Giriş Fiyatı","AE":"Giriş Tarihi","AF":"Max Fiyat","AG":"Hedef Fiyat","AH":"Stop","AI":"Getiri","AJ":"R/K Oranı","AK":"XU100'e Göre","AL":"Max Kazanç"}
for col,h in hdr.items(): ws[f"{col}9"] = h
for r in range(10,20):
    ws[f"AL{r}"] = f'=IFERROR($AF{r}/$AD{r}-1,"")'; ws[f"AL{r}"].number_format = "0.0%"
    ws[f"AL{r}"].fill = fill("C6EFCE"); ws[f"AL{r}"].font = font(bold=True, color="006100")

# Conditional formatting
red, white, green = "F8696B", "FFFFFF", "63BE7B"
for rg in ("C5:H6","C10:C19","D10:D19","E10:E19","F10:F19","G10:G19","H10:H19","AI10:AI19","AK10:AK19"):
    ws.conditional_formatting.add(rg, ColorScaleRule(start_type="min", start_color=red, mid_type="num", mid_value=0, mid_color=white, end_type="max", end_color=green))
ws.conditional_formatting.add("T10:V19", CellIsRule(operator="equal", formula=['"▲"'], font=Font(color="00B050", bold=True)))
ws.conditional_formatting.add("T10:V19", CellIsRule(operator="equal", formula=['"▼"'], font=Font(color="FF0000", bold=True)))
ws.conditional_formatting.add("AC10:AC19", CellIsRule(operator="equal", formula=['"Çok Güçlü"'], fill=fill("63BE7B"), font=Font(color="FFFFFF", bold=True)))
ws.conditional_formatting.add("AC10:AC19", CellIsRule(operator="equal", formula=['"Güçlü"'], fill=fill("C6EFCE"), font=Font(color="006100", bold=True)))
ws.conditional_formatting.add("O10:O19", FormulaRule(formula=["$O10>$R10"], font=Font(color="00B050", bold=True)))
ws.conditional_formatting.add("O10:O19", FormulaRule(formula=["$O10<=$R10"], font=Font(color="C00000", bold=True)))
ws.conditional_formatting.add("W10:W19", FormulaRule(formula=["AND(ISNUMBER($W10),$W10<10)"], fill=fill("C6EFCE")))

# Widths
widths = {"A":9,"B":17,"I":11,"J":11,"K":11,"L":11,"M":16,"N":16,"O":10,"X":13,"Y":10,"Z":22,"AA":22,"AB":28,"AC":11,"AE":11,"AK":11}
for i in range(1,40): ws.column_dimensions[L(i)].width = widths.get(L(i), 8.5 if 3<=i<=8 else 9.5)
ws.column_dimensions["AM"].hidden = True
ws.freeze_panes = "C10"

# Notes
notes = [
 "AÇIKLAMA",
 "• Sarı hücreler (Giriş Tarihi, Hedef %, Stop %) düzenlenebilir girdilerdir. Giriş Fiyatı, giriş tarihindeki kapanıştan otomatik gelir; isterseniz üzerine kendi maliyetinizi yazın.",
 "• Şirket kodunu (A sütunu) değiştirirseniz tüm satır ve 'Veri' sayfası yeni hisseye göre güncellenir. Temel analiz metinlerini (Z–AC) elle güncelleyin.",
 "• Performans sütunları son N işlem gününün getirisidir. ▲/▼: fiyatın ilgili hareketli ortalamanın üstünde/altında olduğunu gösterir. R/K = (Hedef − Fiyat) / (Fiyat − Stop).",
 "• Temel değerlendirmeler (kârlılık, borç, beklenti) 2025–2026 ilk yarı finansallarına dayalı genel niteliktedir; son bilanço/KAP açıklamaları ile teyit edin.",
 "• Bu tablo yatırım tavsiyesi değildir. GOOGLEFINANCE verileri ~15 dk gecikmelidir.",
]
for i,t in enumerate(notes):
    c = ws.cell(22+i,1,t); c.font = font(bold=(i==0), color="404040", size=9 if i else 10)

vd.sheet_state = "visible"
wb.save("BIST_Saglam_10_Hisse_Takip.xlsx")
print("ok")

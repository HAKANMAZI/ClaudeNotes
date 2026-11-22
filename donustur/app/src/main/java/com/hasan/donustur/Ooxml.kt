package com.hasan.donustur

import android.content.Context
import android.net.Uri
import org.w3c.dom.Document
import org.w3c.dom.Element
import org.w3c.dom.Node
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.File
import java.math.BigDecimal
import java.util.zip.ZipEntry
import java.util.zip.ZipInputStream
import java.util.zip.ZipOutputStream
import javax.xml.parsers.DocumentBuilderFactory
import javax.xml.transform.OutputKeys
import javax.xml.transform.TransformerFactory
import javax.xml.transform.dom.DOMSource
import javax.xml.transform.stream.StreamResult

/** DOCX / XLSX paketlerini okuyup yazar. Dokunulmayan her şey (stil, resim, tablo) olduğu gibi kalır. */
class Paket(val parcalar: LinkedHashMap<String, ByteArray>) {

    fun xml(ad: String): Document {
        val f = DocumentBuilderFactory.newInstance().apply { isNamespaceAware = true }
        return f.newDocumentBuilder().parse(ByteArrayInputStream(parcalar[ad] ?: throw IllegalStateException("Eksik parça: $ad")))
    }

    fun yaz(ad: String, doc: Document) {
        val t = TransformerFactory.newInstance().newTransformer()
        t.setOutputProperty(OutputKeys.ENCODING, "UTF-8")
        t.setOutputProperty(OutputKeys.STANDALONE, "yes")
        val o = ByteArrayOutputStream()
        t.transform(DOMSource(doc), StreamResult(o))
        parcalar[ad] = o.toByteArray()
    }

    fun metin(ad: String): String? = parcalar[ad]?.toString(Charsets.UTF_8)
    fun metinYaz(ad: String, s: String) { parcalar[ad] = s.toByteArray(Charsets.UTF_8) }

    fun dosyayaYaz(f: File) {
        ZipOutputStream(f.outputStream().buffered()).use { z ->
            // [Content_Types].xml başta olsun
            val sira = parcalar.keys.sortedBy { if (it == "[Content_Types].xml") 0 else 1 }
            for (ad in sira) { z.putNextEntry(ZipEntry(ad)); z.write(parcalar[ad]!!); z.closeEntry() }
        }
    }

    companion object {
        fun oku(ctx: Context, uri: Uri): Paket {
            val m = LinkedHashMap<String, ByteArray>()
            ctx.contentResolver.openInputStream(uri)!!.use { ins ->
                ZipInputStream(ins).use { z ->
                    var e = z.nextEntry
                    while (e != null) { if (!e.isDirectory) m[e.name] = z.readBytes(); e = z.nextEntry }
                }
            }
            if (m.isEmpty()) throw IllegalStateException("Dosya açılamadı (eski .doc/.xls desteklenmez, .docx/.xlsx olmalı)")
            return Paket(m)
        }

        fun yeni(parcalar: Map<String, String>) = Paket(LinkedHashMap(parcalar.mapValues { it.value.toByteArray(Charsets.UTF_8) }))
    }
}

fun Element.cocuklar(ns: String, ad: String): List<Element> {
    val l = mutableListOf<Element>()
    var n: Node? = firstChild
    while (n != null) { if (n is Element && n.namespaceURI == ns && n.localName == ad) l += n; n = n.nextSibling }
    return l
}

fun Element.torunlar(ns: String, ad: String): List<Element> {
    val nl = getElementsByTagNameNS(ns, ad)
    return (0 until nl.length).map { nl.item(it) as Element }
}

// =====================================================================================
// WORD
// =====================================================================================

const val W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
private const val XML_NS = "http://www.w3.org/XML/1998/namespace"

class Paragraf(var dugum: Element?, var metin: String, var kalin: Boolean, val baslik: Boolean, val tabloda: Boolean)

class WordBelge(val paket: Paket) {
    val doc: Document = paket.xml("word/document.xml")
    val paragraflar = mutableListOf<Paragraf>()
    private val silinenler = mutableListOf<Element>()

    init {
        val govde = doc.documentElement.torunlar(W_NS, "body").first()
        for (p in govde.torunlar(W_NS, "p")) {
            val metin = p.torunlar(W_NS, "t").joinToString("") { it.textContent }
            val runlar = p.torunlar(W_NS, "r").filter { r -> r.torunlar(W_NS, "t").isNotEmpty() }
            val kalin = runlar.isNotEmpty() && runlar.all { r -> r.torunlar(W_NS, "b").any { b -> b.getAttributeNS(W_NS, "val").let { it.isEmpty() || it == "1" || it == "true" } } }
            val stil = p.torunlar(W_NS, "pStyle").firstOrNull()?.getAttributeNS(W_NS, "val") ?: ""
            val baslik = stil.contains("Heading", true) || stil.contains("Title", true) || stil.contains("Baslik", true) || stil.contains("Başlık", true)
            var a: Node? = p.parentNode; var tabloda = false
            while (a != null) { if (a is Element && a.localName == "tc") { tabloda = true; break }; a = a.parentNode }
            paragraflar += Paragraf(p, metin, kalin, baslik, tabloda)
        }
        if (paragraflar.isEmpty()) paragraflar += Paragraf(null, "", false, false, false)
    }

    fun sil(i: Int) {
        val p = paragraflar[i]
        if (p.tabloda) { p.metin = ""; return } // tablo hücresi boş kalamaz
        p.dugum?.let { silinenler += it }
        paragraflar.removeAt(i)
        if (paragraflar.isEmpty()) paragraflar += Paragraf(null, "", false, false, false)
    }

    fun ekle(sonrasina: Int, metin: String = ""): Int {
        val p = Paragraf(null, metin, false, false, false)
        paragraflar.add(sonrasina + 1, p)
        return sonrasina + 1
    }

    private fun metinAta(p: Element, s: String) {
        val ts = p.torunlar(W_NS, "t")
        if (ts.isEmpty()) {
            if (s.isEmpty()) return
            val r = doc.createElementNS(W_NS, "w:r")
            val t = doc.createElementNS(W_NS, "w:t")
            r.appendChild(t); p.appendChild(r)
            t.textContent = s; t.setAttributeNS(XML_NS, "xml:space", "preserve")
            return
        }
        ts[0].textContent = s
        ts[0].setAttributeNS(XML_NS, "xml:space", "preserve")
        for (t in ts.drop(1)) t.textContent = ""
    }

    private fun kalinAta(p: Element, kalin: Boolean) {
        for (r in p.torunlar(W_NS, "r")) {
            var rpr = r.cocuklar(W_NS, "rPr").firstOrNull()
            if (rpr == null) {
                if (!kalin) continue
                rpr = doc.createElementNS(W_NS, "w:rPr")
                r.insertBefore(rpr, r.firstChild)
            }
            rpr!!.cocuklar(W_NS, "b").forEach { rpr.removeChild(it) }
            if (kalin) rpr.insertBefore(doc.createElementNS(W_NS, "w:b"), rpr.firstChild)
        }
    }

    private fun yeniDugum(onceki: Element?): Element {
        val govde = doc.documentElement.torunlar(W_NS, "body").first()
        // Önceki paragrafın biçimini (stil, yazı tipi) kopyala, metnini boşalt
        val p = if (onceki != null && onceki.localName == "p") onceki.cloneNode(true) as Element else doc.createElementNS(W_NS, "w:p")
        if (onceki != null) onceki.parentNode.insertBefore(p, onceki.nextSibling)
        else {
            val sect = govde.cocuklar(W_NS, "sectPr").firstOrNull()
            govde.insertBefore(p, sect)
        }
        // Resim vb. kopyalanmasın: metin içermeyen run'ları sil
        p.torunlar(W_NS, "r").filter { it.torunlar(W_NS, "t").isEmpty() }.forEach { it.parentNode.removeChild(it) }
        return p
    }

    /** Değişiklikleri XML'e işleyip paketi dosyaya yazar. */
    fun kaydet(f: File) {
        silinenler.forEach { it.parentNode?.removeChild(it) }
        silinenler.clear()
        // Enter ile bölünmüş paragrafları ayır
        val duz = mutableListOf<Paragraf>()
        for (p in paragraflar) {
            val parcalar = p.metin.split('\n')
            duz += p.also { it.metin = parcalar[0] }
            parcalar.drop(1).forEach { duz += Paragraf(null, it, p.kalin, false, false) }
        }
        paragraflar.clear(); paragraflar += duz
        var onceki: Element? = null
        for (p in paragraflar) {
            val d = p.dugum ?: yeniDugum(onceki).also { p.dugum = it; metinAta(it, ""); }
            val mevcut = d.torunlar(W_NS, "t").joinToString("") { it.textContent }
            if (mevcut != p.metin) metinAta(d, p.metin)
            val simdikiKalin = d.torunlar(W_NS, "r").let { rs -> rs.isNotEmpty() && rs.all { r -> r.cocuklar(W_NS, "rPr").firstOrNull()?.cocuklar(W_NS, "b")?.isNotEmpty() == true } }
            if (p.kalin != simdikiKalin) kalinAta(d, p.kalin)
            onceki = d
        }
        paket.yaz("word/document.xml", doc)
        paket.dosyayaYaz(f)
    }

    fun duzMetin(): String = paragraflar.joinToString("\n") { it.metin }

    companion object {
        fun yeni(): Paket = Paket.yeni(mapOf(
            "[Content_Types].xml" to """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>""",
            "_rels/.rels" to """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>""",
            "word/document.xml" to """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="$W_NS"><w:body><w:p><w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="24"/></w:rPr><w:t></w:t></w:r></w:p><w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1417" w:right="1417" w:bottom="1417" w:left="1417" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr></w:body></w:document>"""
        ))
    }
}

// =====================================================================================
// EXCEL
// =====================================================================================

const val S_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
private const val R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

class Sayfa(val ad: String, val yol: String)

class ExcelBelge(val paket: Paket) {
    val sayfalar = mutableListOf<Sayfa>()
    private val ortak = mutableListOf<String>()
    private val acik = HashMap<String, Document>()
    /** sayfa yolu → (satır, sütun) → yeni değer */
    private val degisiklik = HashMap<String, HashMap<Pair<Int, Int>, String>>()

    init {
        val wb = paket.xml("xl/workbook.xml")
        val rels = paket.metin("xl/_rels/workbook.xml.rels") ?: ""
        val hedefler = Regex("<Relationship[^>]*>").findAll(rels).associate { m ->
            val id = Regex("Id=\"([^\"]+)\"").find(m.value)?.groupValues?.get(1) ?: ""
            val t = Regex("Target=\"([^\"]+)\"").find(m.value)?.groupValues?.get(1) ?: ""
            id to t
        }
        for (s in wb.documentElement.torunlar(S_NS, "sheet")) {
            val id = s.getAttributeNS(R_NS, "id")
            val t = hedefler[id] ?: continue
            val yol = if (t.startsWith("/")) t.drop(1) else "xl/" + t.removePrefix("./")
            if (paket.parcalar.containsKey(yol)) sayfalar += Sayfa(s.getAttribute("name"), yol)
        }
        if (sayfalar.isEmpty()) throw IllegalStateException("Çalışma sayfası bulunamadı")
        paket.parcalar["xl/sharedStrings.xml"]?.let {
            val d = paket.xml("xl/sharedStrings.xml")
            for (si in d.documentElement.cocuklar(S_NS, "si")) ortak += si.torunlar(S_NS, "t").joinToString("") { it.textContent }
        }
    }

    private fun sayfaDoc(s: Sayfa) = acik.getOrPut(s.yol) { paket.xml(s.yol) }

    /** Sayfadaki tüm dolu hücreler: (satır, sütun) → gösterilecek değer. Formüller "=..." ile. */
    fun hucreler(s: Sayfa): HashMap<Pair<Int, Int>, String> {
        val m = HashMap<Pair<Int, Int>, String>()
        val veri = sayfaDoc(s).documentElement.torunlar(S_NS, "sheetData").firstOrNull() ?: return m
        var otoSatir = 0
        for (satir in veri.cocuklar(S_NS, "row")) {
            val r = satir.getAttribute("r").toIntOrNull()?.minus(1) ?: otoSatir
            otoSatir = r + 1
            var otoSutun = 0
            for (c in satir.cocuklar(S_NS, "c")) {
                val ref = c.getAttribute("r")
                val sut = if (ref.isNotEmpty()) sutunNo(ref) else otoSutun
                otoSutun = sut + 1
                val deger = hucreDegeri(c)
                if (deger.isNotEmpty()) m[r to sut] = deger
            }
        }
        degisiklik[s.yol]?.let { m.putAll(it) }
        return m
    }

    /** Formül varsa formülün kendisi, yoksa değer. */
    fun formulVeyaDeger(s: Sayfa, satir: Int, sutun: Int): String {
        degisiklik[s.yol]?.get(satir to sutun)?.let { return it }
        val c = hucreBul(s, satir, sutun, false) ?: return ""
        c.cocuklar(S_NS, "f").firstOrNull()?.textContent?.takeIf { it.isNotEmpty() }?.let { return "=$it" }
        return hucreDegeri(c, formulGoster = false)
    }

    private fun hucreDegeri(c: Element, formulGoster: Boolean = false): String {
        val t = c.getAttribute("t")
        val v = c.cocuklar(S_NS, "v").firstOrNull()?.textContent ?: ""
        val f = c.cocuklar(S_NS, "f").firstOrNull()?.textContent ?: ""
        if (formulGoster && f.isNotEmpty() && v.isEmpty()) return "=$f"
        return when (t) {
            "s" -> ortak.getOrElse(v.toIntOrNull() ?: -1) { "" }
            "inlineStr" -> c.torunlar(S_NS, "t").joinToString("") { it.textContent }
            "b" -> if (v == "1") "DOĞRU" else "YANLIŞ"
            "str", "e" -> v
            else -> if (v.isEmpty() && f.isNotEmpty()) "=$f" else sayiGoster(v)
        }
    }

    fun degistir(s: Sayfa, satir: Int, sutun: Int, deger: String) {
        degisiklik.getOrPut(s.yol) { HashMap() }[satir to sutun] = deger
    }

    val degistiMi: Boolean get() = degisiklik.values.any { it.isNotEmpty() }

    private fun hucreBul(s: Sayfa, satir: Int, sutun: Int, olustur: Boolean): Element? {
        val doc = sayfaDoc(s)
        val ws = doc.documentElement
        var veri = ws.torunlar(S_NS, "sheetData").firstOrNull()
        if (veri == null) {
            if (!olustur) return null
            veri = doc.createElementNS(S_NS, "sheetData"); ws.appendChild(veri)
        }
        val rNo = satir + 1
        var row: Element? = null
        var sonraki: Element? = null
        for (r in veri!!.cocuklar(S_NS, "row")) {
            val n = r.getAttribute("r").toIntOrNull() ?: continue
            if (n == rNo) { row = r; break }
            if (n > rNo) { sonraki = r; break }
        }
        if (row == null) {
            if (!olustur) return null
            row = doc.createElementNS(S_NS, "row"); row.setAttribute("r", rNo.toString())
            veri.insertBefore(row, sonraki)
        }
        val ref = sutunHarf(sutun) + rNo
        var sonrakiC: Element? = null
        for (c in row!!.cocuklar(S_NS, "c")) {
            val cr = c.getAttribute("r")
            if (cr == ref) return c
            if (cr.isNotEmpty() && sutunNo(cr) > sutun) { sonrakiC = c; break }
        }
        if (!olustur) return null
        val c = doc.createElementNS(S_NS, "c"); c.setAttribute("r", ref)
        row.insertBefore(c, sonrakiC)
        return c
    }

    fun kaydet(f: File) {
        for ((yol, d) in degisiklik) {
            val s = sayfalar.first { it.yol == yol }
            val doc = sayfaDoc(s)
            for ((k, deger) in d) {
                val c = hucreBul(s, k.first, k.second, true)!!
                c.cocuklar(S_NS, "f").forEach { c.removeChild(it) }
                c.cocuklar(S_NS, "v").forEach { c.removeChild(it) }
                c.cocuklar(S_NS, "is").forEach { c.removeChild(it) }
                c.removeAttribute("t")
                val sayi = deger.replace(',', '.').toBigDecimalOrNull()
                when {
                    deger.isEmpty() -> {}
                    deger.startsWith("=") && deger.length > 1 -> {
                        c.appendChild(doc.createElementNS(S_NS, "f").apply { textContent = deger.drop(1) })
                    }
                    sayi != null && !deger.startsWith("+") &&
                        !(deger.length > 1 && deger.startsWith("0") && deger[1].isDigit()) -> // 0532… gibi numaralar yazı kalsın
                        c.appendChild(doc.createElementNS(S_NS, "v").apply { textContent = sayi!!.toPlainString() })
                    else -> {
                        c.setAttribute("t", "inlineStr")
                        val isEl = doc.createElementNS(S_NS, "is")
                        val t = doc.createElementNS(S_NS, "t")
                        t.textContent = deger; t.setAttributeNS(XML_NS, "xml:space", "preserve")
                        isEl.appendChild(t); c.appendChild(isEl)
                    }
                }
            }
            // dimension etiketini kaldır (Excel yeniden hesaplar)
            doc.documentElement.cocuklar(S_NS, "dimension").forEach { doc.documentElement.removeChild(it) }
            paket.yaz(yol, doc)
        }
        // Formül zinciri eskidi: Excel'in onarım uyarısı vermemesi için kaldır, açılışta yeniden hesaplat
        if (degisiklik.isNotEmpty()) {
            paket.parcalar.remove("xl/calcChain.xml")
            paket.metin("xl/_rels/workbook.xml.rels")?.let { paket.metinYaz("xl/_rels/workbook.xml.rels", it.replace(Regex("<Relationship[^>]*calcChain[^>]*/>"), "")) }
            paket.metin("[Content_Types].xml")?.let { paket.metinYaz("[Content_Types].xml", it.replace(Regex("<Override[^>]*calcChain[^>]*/>"), "")) }
            val wb = paket.xml("xl/workbook.xml")
            val kok = wb.documentElement
            var calc = kok.cocuklar(S_NS, "calcPr").firstOrNull()
            if (calc == null) {
                calc = wb.createElementNS(S_NS, "calcPr")
                val sonra = setOf("oleSize", "customWorkbookViews", "pivotCaches", "smartTagPr", "smartTagTypes", "webPublishing", "fileRecoveryPr", "webPublishObjects", "extLst")
                var n: Node? = kok.firstChild; var once: Node? = null
                while (n != null) { if (n is Element && n.localName in sonra) { once = n; break }; n = n.nextSibling }
                kok.insertBefore(calc, once)
            }
            calc!!.setAttribute("fullCalcOnLoad", "1")
            paket.yaz("xl/workbook.xml", wb)
        }
        degisiklik.clear()
        acik.clear()
        paket.dosyayaYaz(f)
    }

    companion object {
        fun sutunNo(ref: String): Int {
            var n = 0
            for (ch in ref) { if (ch.isLetter()) n = n * 26 + (ch.uppercaseChar() - 'A' + 1) else break }
            return (n - 1).coerceAtLeast(0)
        }

        fun sutunHarf(i: Int): String {
            var n = i + 1; val sb = StringBuilder()
            while (n > 0) { val m = (n - 1) % 26; sb.insert(0, ('A' + m)); n = (n - 1) / 26 }
            return sb.toString()
        }

        fun sayiGoster(v: String): String {
            val d = v.toBigDecimalOrNull() ?: return v
            return try {
                val y = d.round(java.math.MathContext(12)).stripTrailingZeros()
                if (y.compareTo(BigDecimal.ZERO) == 0) "0" else y.toPlainString()
            } catch (e: Exception) { v }
        }

        fun yeni(): Paket = Paket.yeni(mapOf(
            "[Content_Types].xml" to """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>""",
            "_rels/.rels" to """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>""",
            "xl/workbook.xml" to """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="$S_NS" xmlns:r="$R_NS"><sheets><sheet name="Sayfa1" sheetId="1" r:id="rId1"/></sheets></workbook>""",
            "xl/_rels/workbook.xml.rels" to """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>""",
            "xl/worksheets/sheet1.xml" to """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="$S_NS"><sheetData/></worksheet>"""
        ))
    }
}

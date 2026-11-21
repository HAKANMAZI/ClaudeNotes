package com.hasan.donustur

import android.content.Context
import android.text.Html
import org.json.JSONArray
import org.json.JSONObject
import org.xmlpull.v1.XmlPullParser
import android.util.Xml
import java.io.ByteArrayInputStream
import java.util.zip.ZipInputStream

/** Office (DOCX/XLSX/PPTX/ODT), EPUB, Markdown, CSV, JSON, altyazı işlemleri — Office gerekmeden. */
object Metin {

    /** ZIP içindeki dosyaları ad → bayt olarak okur. */
    private fun zipOku(ctx: Context, g: Girdi, filtre: (String) -> Boolean): Map<String, ByteArray> {
        val m = sortedMapOf<String, ByteArray>(compareBy<String>({ dogalSira(it).first }, { dogalSira(it).second }))
        ctx.contentResolver.openInputStream(g.uri)!!.use { ins ->
            ZipInputStream(ins).use { z ->
                var e = z.nextEntry
                while (e != null) {
                    if (!e.isDirectory && filtre(e.name)) m[e.name] = z.readBytes()
                    e = z.nextEntry
                }
            }
        }
        return m
    }

    // slide10.xml slide2.xml'den sonra gelsin
    private fun dogalSira(s: String): Pair<String, Int> {
        val sayi = Regex("(\\d+)\\.xml$").find(s)?.groupValues?.get(1)?.toIntOrNull() ?: 0
        return s.replace(Regex("\\d+\\.xml$"), "") to sayi
    }

    /** XML'den metin: paragraf etiketinde satır sonu, metin etiketlerinde içerik. */
    private fun xmlMetin(bayt: ByteArray, metinEtiketi: Set<String>, paragrafEtiketi: Set<String>, sekme: Set<String> = emptySet()): String {
        val sb = StringBuilder()
        val p = Xml.newPullParser()
        p.setFeature(XmlPullParser.FEATURE_PROCESS_NAMESPACES, false)
        p.setInput(ByteArrayInputStream(bayt), "UTF-8")
        var metinde = false
        var t = p.eventType
        while (t != XmlPullParser.END_DOCUMENT) {
            when (t) {
                XmlPullParser.START_TAG -> {
                    val ad = p.name
                    if (ad in metinEtiketi) metinde = true
                    if (ad in sekme) sb.append('\t')
                }
                XmlPullParser.TEXT -> if (metinde) sb.append(p.text)
                XmlPullParser.END_TAG -> {
                    val ad = p.name
                    if (ad in metinEtiketi) metinde = false
                    if (ad in paragrafEtiketi) sb.append('\n')
                }
            }
            t = p.next()
        }
        return sb.toString()
    }

    fun docx(ctx: Context, g: Girdi): String {
        val z = zipOku(ctx, g) { it == "word/document.xml" }
        val b = z["word/document.xml"] ?: throw IllegalStateException("Geçerli bir DOCX değil")
        return xmlMetin(b, setOf("w:t"), setOf("w:p"), setOf("w:tab"))
    }

    fun pptx(ctx: Context, g: Girdi): String {
        val z = zipOku(ctx, g) { it.startsWith("ppt/slides/slide") && it.endsWith(".xml") }
        if (z.isEmpty()) throw IllegalStateException("Geçerli bir PPTX değil")
        var no = 1
        return z.values.joinToString("\n") { "— Slayt ${no++} —\n" + xmlMetin(it, setOf("a:t"), setOf("a:p")) }
    }

    fun odt(ctx: Context, g: Girdi): String {
        val z = zipOku(ctx, g) { it == "content.xml" }
        val b = z["content.xml"] ?: throw IllegalStateException("Geçerli bir ODT değil")
        return xmlMetin(b, setOf("text:p", "text:h", "text:span"), setOf("text:p", "text:h"))
    }

    fun epub(ctx: Context, g: Girdi): String {
        val z = zipOku(ctx, g) { it.endsWith(".xhtml") || it.endsWith(".html") || it.endsWith(".htm") }
        return z.values.joinToString("\n\n") { htmlMetin(String(it, Charsets.UTF_8)) }
    }

    /** XLSX → satırlar (ilk sayfa). */
    fun xlsx(ctx: Context, g: Girdi): List<List<String>> {
        val z = zipOku(ctx, g) { it == "xl/sharedStrings.xml" || it == "xl/worksheets/sheet1.xml" }
        val ortak = mutableListOf<String>()
        z["xl/sharedStrings.xml"]?.let { b ->
            val p = Xml.newPullParser(); p.setInput(ByteArrayInputStream(b), "UTF-8")
            var sb: StringBuilder? = null; var tde = false
            var t = p.eventType
            while (t != XmlPullParser.END_DOCUMENT) {
                when (t) {
                    XmlPullParser.START_TAG -> when (p.name) { "si" -> sb = StringBuilder(); "t" -> tde = true }
                    XmlPullParser.TEXT -> if (tde) sb?.append(p.text)
                    XmlPullParser.END_TAG -> when (p.name) { "t" -> tde = false; "si" -> ortak.add(sb.toString()) }
                }
                t = p.next()
            }
        }
        val sayfa = z["xl/worksheets/sheet1.xml"] ?: throw IllegalStateException("Geçerli bir XLSX değil")
        val satirlar = mutableListOf<MutableList<String>>()
        val p = Xml.newPullParser(); p.setInput(ByteArrayInputStream(sayfa), "UTF-8")
        var satir: MutableList<String>? = null
        var hucreTur = ""; var hucreSut = 0; var deger = StringBuilder(); var vde = false
        var t = p.eventType
        while (t != XmlPullParser.END_DOCUMENT) {
            when (t) {
                XmlPullParser.START_TAG -> when (p.name) {
                    "row" -> satir = mutableListOf()
                    "c" -> {
                        hucreTur = p.getAttributeValue(null, "t") ?: ""
                        hucreSut = sutunNo(p.getAttributeValue(null, "r") ?: "")
                        deger = StringBuilder()
                    }
                    "v", "t" -> vde = true
                }
                XmlPullParser.TEXT -> if (vde) deger.append(p.text)
                XmlPullParser.END_TAG -> when (p.name) {
                    "v", "t" -> vde = false
                    "c" -> {
                        val s = satir ?: mutableListOf()
                        while (s.size < hucreSut) s.add("")
                        val d = deger.toString()
                        s.add(if (hucreTur == "s") ortak.getOrElse(d.toIntOrNull() ?: -1) { "" } else d)
                    }
                    "row" -> satir?.let { satirlar.add(it) }
                }
            }
            t = p.next()
        }
        return satirlar
    }

    private fun sutunNo(ref: String): Int {
        var n = 0
        for (ch in ref) { if (ch.isLetter()) n = n * 26 + (ch.uppercaseChar() - 'A' + 1) else break }
        return (n - 1).coerceAtLeast(0)
    }

    // ---------- CSV ----------
    fun csvOku(metin: String): List<List<String>> {
        val ilk = metin.lineSequence().firstOrNull() ?: ""
        val ayirici = if (ilk.count { it == ';' } > ilk.count { it == ',' }) ';' else ','
        val sonuc = mutableListOf<List<String>>()
        var satir = mutableListOf<String>(); val h = StringBuilder(); var tirnak = false; var i = 0
        while (i < metin.length) {
            val c = metin[i]
            if (tirnak) {
                if (c == '"') { if (i + 1 < metin.length && metin[i + 1] == '"') { h.append('"'); i++ } else tirnak = false } else h.append(c)
            } else when (c) {
                '"' -> tirnak = true
                ayirici -> { satir.add(h.toString()); h.clear() }
                '\n' -> { satir.add(h.toString()); h.clear(); sonuc.add(satir); satir = mutableListOf() }
                '\r' -> {}
                else -> h.append(c)
            }
            i++
        }
        if (h.isNotEmpty() || satir.isNotEmpty()) { satir.add(h.toString()); sonuc.add(satir) }
        return sonuc
    }

    fun csvYaz(satirlar: List<List<String>>): String = satirlar.joinToString("\n") { s ->
        s.joinToString(",") { v -> if (v.any { it == ',' || it == '"' || it == '\n' }) "\"" + v.replace("\"", "\"\"") + "\"" else v }
    }

    fun tabloHtml(satirlar: List<List<String>>, baslik: String): String {
        val sb = StringBuilder("<!DOCTYPE html><html><head><meta charset='utf-8'><title>")
            .append(Html.escapeHtml(baslik)).append("</title><style>table{border-collapse:collapse;font-family:sans-serif}td,th{border:1px solid #999;padding:4px 8px}th{background:#eee}</style></head><body><table>")
        satirlar.forEachIndexed { i, s ->
            sb.append("<tr>")
            s.forEach { v -> val e = if (i == 0) "th" else "td"; sb.append("<$e>").append(Html.escapeHtml(v)).append("</$e>") }
            sb.append("</tr>")
        }
        return sb.append("</table></body></html>").toString()
    }

    fun tabloMetin(satirlar: List<List<String>>): String = satirlar.joinToString("\n") { it.joinToString("   |   ") }

    fun csvdenJson(satirlar: List<List<String>>): String {
        if (satirlar.isEmpty()) return "[]"
        val basliklar = satirlar[0]
        val dizi = JSONArray()
        for (s in satirlar.drop(1)) {
            val o = JSONObject()
            basliklar.forEachIndexed { i, b -> o.put(b.ifBlank { "sutun${i + 1}" }, s.getOrElse(i) { "" }) }
            dizi.put(o)
        }
        return dizi.toString(2)
    }

    fun jsondanCsv(metin: String): String {
        val dizi = when (val k = org.json.JSONTokener(metin).nextValue()) {
            is JSONArray -> k
            is JSONObject -> JSONArray().put(k)
            else -> throw IllegalStateException("JSON dizi ya da nesne olmalı")
        }
        val basliklar = linkedSetOf<String>()
        for (i in 0 until dizi.length()) dizi.optJSONObject(i)?.keys()?.forEach { basliklar.add(it) }
        val satirlar = mutableListOf(basliklar.toList())
        for (i in 0 until dizi.length()) {
            val o = dizi.optJSONObject(i) ?: continue
            satirlar.add(basliklar.map { o.opt(it)?.toString() ?: "" })
        }
        return csvYaz(satirlar)
    }

    fun jsonGuzel(metin: String): String = when (val k = org.json.JSONTokener(metin).nextValue()) {
        is JSONArray -> k.toString(2)
        is JSONObject -> k.toString(2)
        else -> metin
    }

    // ---------- Markdown / HTML ----------
    fun htmlMetin(html: String): String =
        Html.fromHtml(html, Html.FROM_HTML_MODE_LEGACY).toString()

    /** Basit Markdown → HTML (başlık, kalın, italik, liste, kod, bağlantı). */
    fun mdHtml(md: String, baslik: String): String {
        val sb = StringBuilder("<!DOCTYPE html><html><head><meta charset='utf-8'><title>")
            .append(Html.escapeHtml(baslik)).append("</title><style>body{font-family:sans-serif;max-width:800px;margin:auto;padding:16px}pre{background:#f4f4f4;padding:8px}</style></head><body>\n")
        var listede = false; var kodda = false
        for (ham in md.lines()) {
            if (ham.trim().startsWith("```")) { sb.append(if (kodda) "</pre>\n" else "<pre>"); kodda = !kodda; continue }
            if (kodda) { sb.append(Html.escapeHtml(ham)).append('\n'); continue }
            val s = ham.trimEnd()
            val madde = Regex("^\\s*([-*+]|\\d+\\.)\\s+(.*)").find(s)
            if (madde == null && listede) { sb.append("</ul>\n"); listede = false }
            when {
                s.startsWith("#") -> {
                    val n = s.takeWhile { it == '#' }.length.coerceAtMost(6)
                    sb.append("<h$n>").append(satirIci(s.drop(n).trim())).append("</h$n>\n")
                }
                madde != null -> {
                    if (!listede) { sb.append("<ul>\n"); listede = true }
                    sb.append("<li>").append(satirIci(madde.groupValues[2])).append("</li>\n")
                }
                s.isBlank() -> sb.append("\n")
                else -> sb.append("<p>").append(satirIci(s)).append("</p>\n")
            }
        }
        if (listede) sb.append("</ul>\n")
        if (kodda) sb.append("</pre>\n")
        return sb.append("</body></html>").toString()
    }

    private fun satirIci(s: String): String {
        var h = Html.escapeHtml(s)
        h = h.replace(Regex("\\*\\*(.+?)\\*\\*"), "<b>$1</b>")
        h = h.replace(Regex("\\*(.+?)\\*"), "<i>$1</i>")
        h = h.replace(Regex("`(.+?)`"), "<code>$1</code>")
        h = h.replace(Regex("\\[(.+?)]\\((.+?)\\)"), "<a href=\"$2\">$1</a>")
        return h
    }

    // ---------- Altyazı ----------
    fun srtVtt(srt: String): String =
        "WEBVTT\n\n" + srt.replace("\r", "").replace(Regex("(\\d\\d:\\d\\d:\\d\\d),(\\d\\d\\d)"), "$1.$2")

    fun vttSrt(vtt: String): String {
        val bloklar = vtt.replace("\r", "").split(Regex("\n\\s*\n"))
            .map { it.trim() }.filter { it.contains("-->") }
        return bloklar.mapIndexed { i, b ->
            val satirlar = b.lines().dropWhile { !it.contains("-->") }
            val zaman = satirlar[0].replace(Regex("(\\d\\d:\\d\\d)\\.(\\d\\d\\d)"), "$1,$2")
                .let { if (Regex("^\\d\\d:\\d\\d,").containsMatchIn(it)) "00:$it" else it }
                .replace(Regex(" --> (\\d\\d:\\d\\d,)"), " --> 00:$1")
                .substringBefore(" align").substringBefore(" position").substringBefore(" line")
            "${i + 1}\n$zaman\n" + satirlar.drop(1).joinToString("\n")
        }.joinToString("\n\n") + "\n"
    }
}

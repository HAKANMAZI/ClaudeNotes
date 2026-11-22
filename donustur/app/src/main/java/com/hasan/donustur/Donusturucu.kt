package com.hasan.donustur

import android.content.Context
import android.graphics.Bitmap
import java.io.File
import java.util.zip.ZipEntry
import java.util.zip.ZipInputStream
import java.util.zip.ZipOutputStream

data class Hedef(val kod: String, val etiket: String, val coklu: Boolean = false)

/** Dosya türüne göre gidebileceği biçimler ve araçlar. */
object Donusturucu {

    val GORSEL = setOf("jpg", "jpeg", "png", "webp", "heic", "heif", "avif", "bmp", "gif")
    val BELGE = setOf("docx", "odt", "epub")
    val METIN = setOf("txt", "log", "xml", "md", "markdown", "html", "htm", "json", "csv", "srt", "vtt", "ini", "yaml", "yml")
    val VIDEO = setOf("mp4", "mov", "mkv", "webm", "3gp", "m4v")
    val SES = setOf("mp3", "m4a", "aac", "wav", "flac", "ogg", "opus", "amr")

    private val ETIKET = linkedMapOf(
        "duzenle" to "✏️ Düzenle",
        "jpg" to "JPG", "png" to "PNG", "webp" to "WEBP", "pdf" to "PDF",
        "tekpdf" to "Hepsi tek PDF", "txt" to "TXT", "html" to "HTML", "csv" to "CSV", "json" to "JSON",
        "jsonguzel" to "Düzenli JSON", "vtt" to "WebVTT", "srt" to "SRT",
        "m4a" to "M4A (ses)", "wav" to "WAV", "sessiz" to "Sessiz MP4", "kare" to "Kare → JPG", "kareler" to "5 kare → JPG",
        "dondur" to "Döndür 90°", "aynala" to "Aynala", "gri" to "Siyah-beyaz",
        "k11" to "Kırp 1:1", "k43" to "Kırp 4:3", "k169" to "Kırp 16:9", "yari" to "Yarı boyut",
        "bol" to "Sayfalara böl", "kucult" to "PDF küçült", "sayfano" to "Sayfa numarası",
        "cikar" to "ZIP'i aç", "zip" to "ZIP yap"
    )
    private val COKLU = setOf("tekpdf", "zip")

    fun kategori(g: Girdi): String = when (val e = g.uzanti) {
        in GORSEL -> "gorsel"
        "pdf" -> "pdf"
        in BELGE -> "belge"
        "pptx" -> "sunum"
        "xlsx" -> "tablo"
        in VIDEO -> "video"
        in SES -> "ses"
        "zip" -> "arsiv"
        in METIN -> e
        else -> "diger"
    }

    private fun kodlar(g: Girdi): List<String> = when (val k = kategori(g)) {
        "gorsel" -> listOf("jpg", "png", "webp", "pdf", "tekpdf", "dondur", "aynala", "gri", "k11", "k43", "k169", "yari")
        "pdf" -> listOf("duzenle", "jpg", "png", "txt", "tekpdf", "bol", "kucult", "sayfano")
        "belge" -> (if (g.uzanti == "docx") listOf("duzenle") else emptyList()) + listOf("pdf", "txt", "tekpdf")
        "sunum" -> listOf("pdf", "txt", "tekpdf")
        "tablo" -> listOf("duzenle", "csv", "json", "html", "pdf", "tekpdf")
        "csv" -> listOf("duzenle", "json", "html", "pdf", "tekpdf")
        "json" -> listOf("duzenle", "csv", "jsonguzel", "pdf", "tekpdf")
        "md", "markdown" -> listOf("duzenle", "html", "pdf", "txt", "tekpdf")
        "html", "htm" -> listOf("duzenle", "pdf", "txt", "tekpdf")
        "srt" -> listOf("duzenle", "vtt", "txt", "pdf")
        "vtt" -> listOf("duzenle", "srt", "txt", "pdf")
        "video" -> listOf("m4a", "wav", "sessiz", "kare", "kareler")
        "ses" -> listOf("wav", "m4a")
        "arsiv" -> listOf("cikar")
        "diger" -> emptyList()
        else -> if (k in METIN) listOf("duzenle", "pdf", "tekpdf") else emptyList()
    } + "zip"

    /** Seçilen dosyaların hepsine uyan hedefler. */
    fun hedefler(girdiler: List<Girdi>): List<Hedef> {
        if (girdiler.isEmpty()) return emptyList()
        var ortak = kodlar(girdiler[0]).toSet()
        for (g in girdiler.drop(1)) ortak = ortak intersect kodlar(g).toSet()
        if (girdiler.size > 1) ortak = ortak - "duzenle"
        else ortak = ortak - "tekpdf"
        return ETIKET.keys.filter { it in ortak }.map { Hedef(it, ETIKET[it]!!, it in COKLU) }
    }

    // --------------------------------------------------------------------------------

    class Rapor { val ciktilar = mutableListOf<Cikti>(); val hatalar = mutableListOf<String>() }

    fun calistir(ctx: Context, girdiler: List<Girdi>, h: Hedef, durum: (String) -> Unit): Rapor {
        val r = Rapor()
        if (h.coklu) {
            try {
                durum("İşleniyor…")
                r.ciktilar += when (h.kod) {
                    "zip" -> zipYap(ctx, girdiler)
                    else -> tekPdf(ctx, girdiler, durum)
                }
            } catch (e: Throwable) { r.hatalar += "${h.etiket}: ${e.message ?: e.javaClass.simpleName}" }
            return r
        }
        // Dosyalar tek tek: biri hata verirse diğerleri devam eder
        girdiler.forEachIndexed { i, g ->
            durum("${i + 1}/${girdiler.size}: ${g.ad}")
            try { r.ciktilar += tekDosya(ctx, g, h.kod, durum) }
            catch (e: Throwable) { r.hatalar += "${g.ad}: ${e.message ?: e.javaClass.simpleName}" }
        }
        Dosya.temizle(ctx)
        return r
    }

    private fun gorselIslem(ctx: Context, g: Girdi, f: (Bitmap) -> Bitmap, ek: String): Cikti {
        val bmp = f(Gorsel.ac(ctx, g))
        val bicim = if (g.uzanti in setOf("png", "webp")) g.uzanti else "jpg"
        return Dosya.yazKaydet(ctx, "${g.kok}_$ek.$bicim") { Gorsel.yaz(bmp, it, bicim) }
    }

    private fun metinKaydet(ctx: Context, ad: String, metin: String) = Dosya.yazKaydet(ctx, ad) { it.writeText(metin) }

    /** Herhangi bir desteklenen dosyadan düz metin. */
    fun metinCikar(ctx: Context, g: Girdi): String = when (kategori(g)) {
        "pdf" -> PdfIslem.metin(ctx, Dosya.yerelKopya(ctx, g))
        "belge" -> when (g.uzanti) { "docx" -> Metin.docx(ctx, g); "odt" -> Metin.odt(ctx, g); else -> Metin.epub(ctx, g) }
        "sunum" -> Metin.pptx(ctx, g)
        "tablo" -> Metin.tabloMetin(Metin.xlsx(ctx, g))
        "csv" -> Metin.tabloMetin(Metin.csvOku(Dosya.metinOku(ctx, g)))
        "html", "htm" -> Metin.htmlMetin(Dosya.metinOku(ctx, g))
        "json" -> Metin.jsonGuzel(Dosya.metinOku(ctx, g))
        "srt", "vtt" -> Dosya.metinOku(ctx, g).lines()
            .filterNot { it.contains("-->") || it.trim().matches(Regex("\\d+")) || it.startsWith("WEBVTT") }
            .joinToString("\n").replace(Regex("\n{3,}"), "\n\n")
        else -> Dosya.metinOku(ctx, g)
    }

    /** Bir dosyayı geçici PDF'ye çevirir (tek PDF için). */
    private fun pdfDosyasi(ctx: Context, g: Girdi): File = when (kategori(g)) {
        "pdf" -> Dosya.yerelKopya(ctx, g)
        "gorsel" -> Dosya.gecici(ctx, "p_${System.nanoTime()}.pdf").also { Gorsel.gorsellerdenPdf(sequenceOf(Gorsel.ac(ctx, g, 2500)), it) }
        "md", "markdown" -> Dosya.gecici(ctx, "p_${System.nanoTime()}.pdf").also {
            Gorsel.metindenPdf(android.text.Html.fromHtml(Metin.mdHtml(Dosya.metinOku(ctx, g), g.kok), android.text.Html.FROM_HTML_MODE_LEGACY), it)
        }
        "html", "htm" -> Dosya.gecici(ctx, "p_${System.nanoTime()}.pdf").also {
            Gorsel.metindenPdf(android.text.Html.fromHtml(Dosya.metinOku(ctx, g), android.text.Html.FROM_HTML_MODE_LEGACY), it)
        }
        "tablo", "csv" -> Dosya.gecici(ctx, "p_${System.nanoTime()}.pdf").also { Gorsel.metindenPdf(metinCikar(ctx, g), it, 9f) }
        else -> Dosya.gecici(ctx, "p_${System.nanoTime()}.pdf").also { Gorsel.metindenPdf(metinCikar(ctx, g), it) }
    }

    private fun tekDosya(ctx: Context, g: Girdi, kod: String, durum: (String) -> Unit): List<Cikti> {
        val kat = kategori(g)
        return when (kod) {
            "jpg", "png", "webp" -> if (kat == "pdf") {
                val liste = mutableListOf<Cikti>()
                Gorsel.pdfSayfalari(Dosya.yerelKopya(ctx, g)) { i, bmp ->
                    durum("${g.ad} — sayfa ${i + 1}")
                    liste += Dosya.yazKaydet(ctx, "${g.kok}_s${i + 1}.$kod") { Gorsel.yaz(bmp, it, kod) }
                    bmp.recycle()
                }
                liste
            } else listOf(Dosya.yazKaydet(ctx, "${g.kok}.$kod") { Gorsel.yaz(Gorsel.ac(ctx, g), it, kod) })

            "pdf" -> listOf(Dosya.kaydet(ctx, pdfDosyasi(ctx, g), "${g.kok}.pdf"))
            "dondur" -> listOf(gorselIslem(ctx, g, { Gorsel.dondur(it, 90f) }, "donmus"))
            "aynala" -> listOf(gorselIslem(ctx, g, Gorsel::aynala, "ayna"))
            "gri" -> listOf(gorselIslem(ctx, g, Gorsel::gri, "sb"))
            "k11" -> listOf(gorselIslem(ctx, g, { Gorsel.kirp(it, 1, 1) }, "1x1"))
            "k43" -> listOf(gorselIslem(ctx, g, { Gorsel.kirp(it, 4, 3) }, "4x3"))
            "k169" -> listOf(gorselIslem(ctx, g, { Gorsel.kirp(it, 16, 9) }, "16x9"))
            "yari" -> listOf(gorselIslem(ctx, g, { Gorsel.olcekle(it, 0.5f) }, "kucuk"))

            "txt" -> listOf(metinKaydet(ctx, "${g.kok}.txt", metinCikar(ctx, g)))
            "html" -> listOf(metinKaydet(ctx, "${g.kok}.html", when (kat) {
                "tablo" -> Metin.tabloHtml(Metin.xlsx(ctx, g), g.kok)
                "csv" -> Metin.tabloHtml(Metin.csvOku(Dosya.metinOku(ctx, g)), g.kok)
                else -> Metin.mdHtml(Dosya.metinOku(ctx, g), g.kok)
            }))
            "csv" -> listOf(metinKaydet(ctx, "${g.kok}.csv",
                if (kat == "tablo") Metin.csvYaz(Metin.xlsx(ctx, g)) else Metin.jsondanCsv(Dosya.metinOku(ctx, g))))
            "json" -> listOf(metinKaydet(ctx, "${g.kok}.json", Metin.csvdenJson(
                if (kat == "tablo") Metin.xlsx(ctx, g) else Metin.csvOku(Dosya.metinOku(ctx, g)))))
            "jsonguzel" -> listOf(metinKaydet(ctx, "${g.kok}_duzenli.json", Metin.jsonGuzel(Dosya.metinOku(ctx, g))))
            "vtt" -> listOf(metinKaydet(ctx, "${g.kok}.vtt", Metin.srtVtt(Dosya.metinOku(ctx, g))))
            "srt" -> listOf(metinKaydet(ctx, "${g.kok}.srt", Metin.vttSrt(Dosya.metinOku(ctx, g))))

            "bol" -> {
                val liste = mutableListOf<Cikti>()
                PdfIslem.bol(ctx, Dosya.yerelKopya(ctx, g)) { i, f -> liste += Dosya.kaydet(ctx, f, "${g.kok}_s${i + 1}.pdf") }
                liste
            }
            "kucult" -> listOf(Dosya.yazKaydet(ctx, "${g.kok}_kucuk.pdf") { PdfIslem.kucult(ctx, Dosya.yerelKopya(ctx, g), it) })
            "sayfano" -> listOf(Dosya.yazKaydet(ctx, "${g.kok}_numarali.pdf") { PdfIslem.sayfaNumarasi(ctx, Dosya.yerelKopya(ctx, g), it) })

            "m4a" -> listOf(Dosya.yazKaydet(ctx, "${g.kok}.m4a") { Medya.izKopyala(Dosya.yerelKopya(ctx, g), it, true) })
            "sessiz" -> listOf(Dosya.yazKaydet(ctx, "${g.kok}_sessiz.mp4") { Medya.izKopyala(Dosya.yerelKopya(ctx, g), it, false) })
            "wav" -> listOf(Dosya.yazKaydet(ctx, "${g.kok}.wav") { Medya.wav(Dosya.yerelKopya(ctx, g), it) { y -> durum("${g.ad} — %$y") } })
            "kare", "kareler" -> Medya.kareler(Dosya.yerelKopya(ctx, g), if (kod == "kare") 1 else 5).mapIndexed { i, bmp ->
                Dosya.yazKaydet(ctx, "${g.kok}_kare${i + 1}.jpg") { Gorsel.yaz(bmp, it, "jpg") }
            }
            "cikar" -> zipAc(ctx, g)
            else -> throw IllegalStateException("Bu dosya için desteklenmiyor")
        }
    }

    private fun tekPdf(ctx: Context, girdiler: List<Girdi>, durum: (String) -> Unit): List<Cikti> {
        // Hepsi görselse tek seferde; karışıksa her birini PDF yapıp birleştir
        val ad = (if (girdiler.size == 1) girdiler[0].kok else "birlesik_${girdiler.size}_dosya") + ".pdf"
        if (girdiler.all { kategori(it) == "gorsel" }) {
            return listOf(Dosya.yazKaydet(ctx, ad) { f ->
                Gorsel.gorsellerdenPdf(girdiler.asSequence().mapIndexed { i, g -> durum("Görsel ${i + 1}/${girdiler.size}"); Gorsel.ac(ctx, g, 2500) }, f)
            })
        }
        val pdfler = girdiler.mapIndexed { i, g -> durum("PDF'ye çevriliyor ${i + 1}/${girdiler.size}"); pdfDosyasi(ctx, g) }
        durum("Birleştiriliyor…")
        val c = Dosya.yazKaydet(ctx, ad) { PdfIslem.birlestir(ctx, pdfler, it) }
        Dosya.temizle(ctx)
        return listOf(c)
    }

    private fun zipYap(ctx: Context, girdiler: List<Girdi>): List<Cikti> {
        val ad = (if (girdiler.size == 1) girdiler[0].kok else "arsiv_${girdiler.size}_dosya") + ".zip"
        return listOf(Dosya.yazKaydet(ctx, ad) { f ->
            ZipOutputStream(f.outputStream().buffered()).use { z ->
                val kullanilan = mutableSetOf<String>()
                for (g in girdiler) {
                    var isim = g.ad; var n = 2
                    while (!kullanilan.add(isim)) isim = "${g.kok} ($n).${g.uzanti}".also { n++ }
                    z.putNextEntry(ZipEntry(isim))
                    ctx.contentResolver.openInputStream(g.uri)!!.use { it.copyTo(z) }
                    z.closeEntry()
                }
            }
        })
    }

    private fun zipAc(ctx: Context, g: Girdi): List<Cikti> {
        val liste = mutableListOf<Cikti>()
        ctx.contentResolver.openInputStream(g.uri)!!.use { ins ->
            ZipInputStream(ins).use { z ->
                var e = z.nextEntry
                while (e != null) {
                    if (!e.isDirectory) {
                        val isim = e.name.substringAfterLast('/')
                        if (isim.isNotBlank() && !isim.startsWith(".")) {
                            val f = Dosya.gecici(ctx, "z_${System.nanoTime()}")
                            f.outputStream().use { z.copyTo(it) }
                            liste += Dosya.kaydet(ctx, f, isim)
                        }
                    }
                    e = z.nextEntry
                }
            }
        }
        if (liste.isEmpty()) throw IllegalStateException("ZIP boş")
        return liste
    }
}

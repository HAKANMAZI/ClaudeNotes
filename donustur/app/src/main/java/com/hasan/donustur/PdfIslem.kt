package com.hasan.donustur

import android.content.Context
import android.graphics.Bitmap
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader
import com.tom_roush.pdfbox.multipdf.PDFMergerUtility
import com.tom_roush.pdfbox.io.MemoryUsageSetting
import com.tom_roush.pdfbox.pdmodel.PDDocument
import com.tom_roush.pdfbox.pdmodel.PDPage
import com.tom_roush.pdfbox.pdmodel.PDPageContentStream
import com.tom_roush.pdfbox.pdmodel.common.PDRectangle
import com.tom_roush.pdfbox.pdmodel.encryption.AccessPermission
import com.tom_roush.pdfbox.pdmodel.encryption.StandardProtectionPolicy
import com.tom_roush.pdfbox.pdmodel.font.PDFont
import com.tom_roush.pdfbox.pdmodel.font.PDType0Font
import com.tom_roush.pdfbox.pdmodel.graphics.image.JPEGFactory
import com.tom_roush.pdfbox.pdmodel.graphics.image.LosslessFactory
import com.tom_roush.pdfbox.pdmodel.graphics.state.PDExtendedGraphicsState
import com.tom_roush.pdfbox.text.PDFTextStripper
import com.tom_roush.pdfbox.util.Matrix
import java.io.File

/** PDF düzenleme işlemleri (PdfBox). Türkçe karakter için DejaVuSans gömülür. */
object PdfIslem {

    @Volatile private var hazir = false

    fun hazirla(ctx: Context) {
        if (!hazir) { PDFBoxResourceLoader.init(ctx.applicationContext); hazir = true }
    }

    fun ac(ctx: Context, f: File, sifre: String = ""): PDDocument {
        hazirla(ctx)
        return PDDocument.load(f, sifre)
    }

    private fun yazitipi(ctx: Context, doc: PDDocument): PDFont =
        ctx.assets.open("DejaVuSans.ttf").use { PDType0Font.load(doc, it) }

    fun sayfaSayisi(ctx: Context, f: File): Int = ac(ctx, f).use { it.numberOfPages }

    fun metin(ctx: Context, f: File): String = ac(ctx, f).use { PDFTextStripper().getText(it) }

    fun birlestir(ctx: Context, dosyalar: List<File>, cikti: File) {
        hazirla(ctx)
        val m = PDFMergerUtility()
        dosyalar.forEach { m.addSource(it) }
        m.destinationFileName = cikti.absolutePath
        m.mergeDocuments(MemoryUsageSetting.setupMainMemoryOnly())
    }

    /** Seçili sayfaları (0 tabanlı) yeni PDF'ye alır. */
    fun sayfalariAl(ctx: Context, f: File, sayfalar: List<Int>, cikti: File) {
        ac(ctx, f).use { doc ->
            PDDocument().use { yeni ->
                for (i in sayfalar) yeni.importPage(doc.getPage(i))
                yeni.save(cikti)
            }
        }
    }

    fun sayfalariSil(ctx: Context, f: File, sayfalar: List<Int>, cikti: File) {
        ac(ctx, f).use { doc ->
            if (sayfalar.size >= doc.numberOfPages) throw IllegalStateException("Tüm sayfalar silinemez")
            for (i in sayfalar.sortedDescending()) doc.removePage(i)
            doc.save(cikti)
        }
    }

    fun dondur(ctx: Context, f: File, sayfalar: List<Int>, derece: Int, cikti: File) {
        ac(ctx, f).use { doc ->
            for (i in sayfalar) { val p = doc.getPage(i); p.rotation = ((p.rotation + derece) % 360 + 360) % 360 }
            doc.save(cikti)
        }
    }

    /** Sayfaları yeni sıraya dizer (ör. ters çevirme, taşıma). */
    fun yenidenSirala(ctx: Context, f: File, sira: List<Int>, cikti: File) = sayfalariAl(ctx, f, sira, cikti)

    /** Her sayfayı ayrı PDF yapar. */
    fun bol(ctx: Context, f: File, her: (Int, File) -> Unit) {
        ac(ctx, f).use { doc ->
            for (i in 0 until doc.numberOfPages) {
                val c = Dosya.gecici(ctx, "bol_${System.nanoTime()}.pdf")
                PDDocument().use { y -> y.importPage(doc.getPage(i)); y.save(c) }
                her(i, c)
            }
        }
    }

    private fun renk(cs: PDPageContentStream, argb: Int) =
        cs.setNonStrokingColor(((argb shr 16) and 255) / 255f, ((argb shr 8) and 255) / 255f, (argb and 255) / 255f)

    private fun akis(doc: PDDocument, p: PDPage) = PDPageContentStream(doc, p, PDPageContentStream.AppendMode.APPEND, true, true)

    /** Seçili sayfalara yazı ekler. xOran/yOran: sayfanın sol-üstünden oran (0..1). */
    fun yaziEkle(ctx: Context, f: File, sayfalar: List<Int>, yazi: String, boyut: Float, xOran: Float, yOran: Float, argb: Int, cikti: File) {
        ac(ctx, f).use { doc ->
            val font = yazitipi(ctx, doc)
            val satirlar = yazi.lines()
            for (i in sayfalar) {
                val p = doc.getPage(i)
                val k = p.cropBox
                val x = k.lowerLeftX + k.width * xOran
                val y = k.upperRightY - k.height * yOran - boyut
                akis(doc, p).use { cs ->
                    renk(cs, argb)
                    cs.beginText()
                    cs.setFont(font, boyut)
                    cs.newLineAtOffset(x, y)
                    satirlar.forEachIndexed { n, s -> if (n > 0) cs.newLineAtOffset(0f, -boyut * 1.2f); cs.showText(s) }
                    cs.endText()
                }
            }
            doc.save(cikti)
        }
    }

    /** Tüm sayfalara çapraz, yarı saydam filigran. */
    fun filigran(ctx: Context, f: File, yazi: String, cikti: File) {
        ac(ctx, f).use { doc ->
            val font = yazitipi(ctx, doc)
            val gs = PDExtendedGraphicsState().apply { nonStrokingAlphaConstant = 0.25f }
            for (p in doc.pages) {
                val k = p.cropBox
                val boyut = minOf(k.width, k.height) / maxOf(4f, yazi.length * 0.55f)
                val w = font.getStringWidth(yazi) / 1000 * boyut
                akis(doc, p).use { cs ->
                    cs.setGraphicsStateParameters(gs)
                    cs.setNonStrokingColor(0.8f, 0.1f, 0.1f)
                    cs.beginText()
                    cs.setFont(font, boyut)
                    val aci = Math.atan2(k.height.toDouble(), k.width.toDouble())
                    val cx = k.lowerLeftX + k.width / 2; val cy = k.lowerLeftY + k.height / 2
                    val dx = (w / 2 * Math.cos(aci)).toFloat(); val dy = (w / 2 * Math.sin(aci)).toFloat()
                    cs.setTextMatrix(Matrix.getRotateInstance(aci, cx - dx, cy - dy))
                    cs.showText(yazi)
                    cs.endText()
                }
            }
            doc.save(cikti)
        }
    }

    /** Sayfa numarası: "1 / 10" alt ortada. */
    fun sayfaNumarasi(ctx: Context, f: File, cikti: File) {
        ac(ctx, f).use { doc ->
            val font = yazitipi(ctx, doc)
            val n = doc.numberOfPages
            doc.pages.forEachIndexed { i, p ->
                val s = "${i + 1} / $n"
                val w = font.getStringWidth(s) / 1000 * 10f
                val k = p.cropBox
                akis(doc, p).use { cs ->
                    cs.setNonStrokingColor(0.3f, 0.3f, 0.3f)
                    cs.beginText(); cs.setFont(font, 10f)
                    cs.newLineAtOffset(k.lowerLeftX + (k.width - w) / 2, k.lowerLeftY + 18f)
                    cs.showText(s); cs.endText()
                }
            }
            doc.save(cikti)
        }
    }

    /** İmza / logo / resim ekler. Konum ve genişlik sayfaya oranla. */
    fun resimEkle(ctx: Context, f: File, sayfalar: List<Int>, bmp: Bitmap, xOran: Float, yOran: Float, wOran: Float, cikti: File) {
        ac(ctx, f).use { doc ->
            val img = if (bmp.hasAlpha()) LosslessFactory.createFromImage(doc, bmp) else JPEGFactory.createFromImage(doc, bmp, 0.9f)
            for (i in sayfalar) {
                val p = doc.getPage(i)
                val k = p.cropBox
                val w = k.width * wOran
                val h = w * bmp.height / bmp.width
                val x = k.lowerLeftX + k.width * xOran
                val y = k.upperRightY - k.height * yOran - h
                akis(doc, p).use { it.drawImage(img, x, y, w, h) }
            }
            doc.save(cikti)
        }
    }

    /** Beyaz kutu ile alan kapatma (karartma/silgi) — seçili sayfalarda konuma göre. */
    fun alanKapat(ctx: Context, f: File, sayfalar: List<Int>, xOran: Float, yOran: Float, wOran: Float, hOran: Float, siyah: Boolean, cikti: File) {
        ac(ctx, f).use { doc ->
            for (i in sayfalar) {
                val p = doc.getPage(i)
                val k = p.cropBox
                akis(doc, p).use { cs ->
                    if (siyah) cs.setNonStrokingColor(0f, 0f, 0f) else cs.setNonStrokingColor(1f, 1f, 1f)
                    cs.addRect(k.lowerLeftX + k.width * xOran, k.upperRightY - k.height * (yOran + hOran), k.width * wOran, k.height * hOran)
                    cs.fill()
                }
            }
            doc.save(cikti)
        }
    }

    fun sifrele(ctx: Context, f: File, sifre: String, cikti: File) {
        ac(ctx, f).use { doc ->
            val pol = StandardProtectionPolicy(sifre, sifre, AccessPermission())
            pol.encryptionKeyLength = 128
            doc.protect(pol)
            doc.save(cikti)
        }
    }

    fun sifreKaldir(ctx: Context, f: File, sifre: String, cikti: File) {
        ac(ctx, f, sifre).use { doc ->
            doc.isAllSecurityToBeRemoved = true
            doc.save(cikti)
        }
    }

    /** Başlık/yazar bilgisini temizler ya da değiştirir. */
    fun bilgi(ctx: Context, f: File, baslik: String, yazar: String, cikti: File) {
        ac(ctx, f).use { doc ->
            val b = doc.documentInformation
            b.title = baslik.ifBlank { null }
            b.author = yazar.ifBlank { null }
            b.producer = "Dönüştür"
            doc.save(cikti)
        }
    }

    /** Sayfaları JPEG'e çevirip yeniden kurar: boyutu çok küçültür (metin seçilemez olur). */
    fun kucult(ctx: Context, f: File, cikti: File, kalite: Int = 60) {
        val doc = PDDocument()
        try {
            hazirla(ctx)
            Gorsel.pdfSayfalari(f, 1.4f) { _, bmp ->
                val sayfa = PDPage(PDRectangle(bmp.width / 1.4f, bmp.height / 1.4f))
                doc.addPage(sayfa)
                val img = JPEGFactory.createFromImage(doc, bmp, kalite / 100f)
                akis(doc, sayfa).use { it.drawImage(img, 0f, 0f, sayfa.mediaBox.width, sayfa.mediaBox.height) }
                bmp.recycle()
            }
            doc.save(cikti)
        } finally { doc.close() }
    }
}

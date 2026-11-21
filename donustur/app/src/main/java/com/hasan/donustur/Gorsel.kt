package com.hasan.donustur

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.ColorMatrix
import android.graphics.ColorMatrixColorFilter
import android.graphics.ImageDecoder
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.pdf.PdfDocument
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import android.text.Layout
import android.text.StaticLayout
import android.text.TextPaint
import java.io.File
import java.io.FileOutputStream

object Gorsel {

    const val A4_G = 595
    const val A4_Y = 842

    /** HEIC, AVIF, WEBP, PNG, JPG, BMP, GIF… cihazın desteklediği her görseli açar. */
    fun ac(ctx: Context, g: Girdi, enBuyuk: Int = 4096): Bitmap {
        val kaynak = ImageDecoder.createSource(ctx.contentResolver, g.uri)
        return ImageDecoder.decodeBitmap(kaynak) { dec, bilgi, _ ->
            dec.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
            val w = bilgi.size.width
            val h = bilgi.size.height
            val m = maxOf(w, h)
            if (m > enBuyuk) {
                val o = enBuyuk.toFloat() / m
                dec.setTargetSize((w * o).toInt().coerceAtLeast(1), (h * o).toInt().coerceAtLeast(1))
            }
        }
    }

    fun yaz(bmp: Bitmap, f: File, bicim: String, kalite: Int = 90) {
        val (fmt, bmp2) = when (bicim) {
            "png" -> Bitmap.CompressFormat.PNG to bmp
            "webp" -> Bitmap.CompressFormat.WEBP_LOSSY to bmp
            else -> Bitmap.CompressFormat.JPEG to beyazZemin(bmp) // JPG saydamlık desteklemez
        }
        FileOutputStream(f).use { bmp2.compress(fmt, kalite, it) }
    }

    fun beyazZemin(bmp: Bitmap): Bitmap {
        if (!bmp.hasAlpha()) return bmp
        val out = Bitmap.createBitmap(bmp.width, bmp.height, Bitmap.Config.ARGB_8888)
        Canvas(out).apply { drawColor(Color.WHITE); drawBitmap(bmp, 0f, 0f, null) }
        return out
    }

    fun dondur(bmp: Bitmap, derece: Float): Bitmap {
        val m = Matrix().apply { postRotate(derece) }
        return Bitmap.createBitmap(bmp, 0, 0, bmp.width, bmp.height, m, true)
    }

    fun aynala(bmp: Bitmap): Bitmap {
        val m = Matrix().apply { postScale(-1f, 1f) }
        return Bitmap.createBitmap(bmp, 0, 0, bmp.width, bmp.height, m, true)
    }

    fun gri(bmp: Bitmap): Bitmap {
        val out = Bitmap.createBitmap(bmp.width, bmp.height, Bitmap.Config.ARGB_8888)
        val p = Paint().apply { colorFilter = ColorMatrixColorFilter(ColorMatrix().apply { setSaturation(0f) }) }
        Canvas(out).drawBitmap(bmp, 0f, 0f, p)
        return out
    }

    /** Ortadan en-boy oranına kırpar (1:1, 4:3, 16:9 …). */
    fun kirp(bmp: Bitmap, oranG: Int, oranY: Int): Bitmap {
        val hedef = oranG.toFloat() / oranY
        val mevcut = bmp.width.toFloat() / bmp.height
        return if (mevcut > hedef) {
            val w = (bmp.height * hedef).toInt()
            Bitmap.createBitmap(bmp, (bmp.width - w) / 2, 0, w, bmp.height)
        } else {
            val h = (bmp.width / hedef).toInt()
            Bitmap.createBitmap(bmp, 0, (bmp.height - h) / 2, bmp.width, h)
        }
    }

    fun olcekle(bmp: Bitmap, oran: Float): Bitmap =
        Bitmap.createScaledBitmap(bmp, (bmp.width * oran).toInt().coerceAtLeast(1), (bmp.height * oran).toInt().coerceAtLeast(1), true)

    /** Görselleri A4 sayfalara yerleştirip tek PDF yapar. */
    fun gorsellerdenPdf(bitmaps: Sequence<Bitmap>, f: File) {
        val doc = PdfDocument()
        var no = 1
        for (bmp in bitmaps) {
            val yatay = bmp.width > bmp.height
            val pw = if (yatay) A4_Y else A4_G
            val ph = if (yatay) A4_G else A4_Y
            val sayfa = doc.startPage(PdfDocument.PageInfo.Builder(pw, ph, no++).create())
            val kenar = 20f
            val o = minOf((pw - 2 * kenar) / bmp.width, (ph - 2 * kenar) / bmp.height)
            val w = bmp.width * o
            val h = bmp.height * o
            val m = Matrix().apply { postScale(o, o); postTranslate((pw - w) / 2, (ph - h) / 2) }
            sayfa.canvas.drawBitmap(bmp, m, Paint(Paint.FILTER_BITMAP_FLAG))
            doc.finishPage(sayfa)
            bmp.recycle()
        }
        FileOutputStream(f).use { doc.writeTo(it) }
        doc.close()
    }

    /** Düz metni (Türkçe karakterli) çok sayfalı A4 PDF'ye yazar. */
    fun metindenPdf(metin: CharSequence, f: File, yaziBoyu: Float = 11f) {
        val doc = PdfDocument()
        val kenar = 40
        val genislik = A4_G - 2 * kenar
        val yukseklik = A4_Y - 2 * kenar
        val boya = TextPaint(Paint.ANTI_ALIAS_FLAG).apply { textSize = yaziBoyu; color = Color.BLACK }
        val layout = StaticLayout.Builder.obtain(metin, 0, metin.length, boya, genislik)
            .setAlignment(Layout.Alignment.ALIGN_NORMAL).setLineSpacing(2f, 1f).build()
        var satir = 0
        var no = 1
        do {
            val sayfa = doc.startPage(PdfDocument.PageInfo.Builder(A4_G, A4_Y, no++).create())
            val ust = layout.getLineTop(satir)
            var son = satir
            while (son < layout.lineCount && layout.getLineBottom(son) - ust <= yukseklik) son++
            if (son == satir) son = satir + 1
            val alt = layout.getLineBottom(son - 1)
            val c = sayfa.canvas
            c.save()
            c.translate(kenar.toFloat(), (kenar - ust).toFloat())
            c.clipRect(0, ust, genislik, alt)
            layout.draw(c)
            c.restore()
            doc.finishPage(sayfa)
            satir = son
        } while (satir < layout.lineCount)
        FileOutputStream(f).use { doc.writeTo(it) }
        doc.close()
    }

    /** PDF sayfalarını tek tek resme çevirir. */
    fun pdfSayfalari(pdf: File, olcek: Float = 2f, sifreliIse: () -> Unit = {}, her: (Int, Bitmap) -> Unit) {
        val pfd = ParcelFileDescriptor.open(pdf, ParcelFileDescriptor.MODE_READ_ONLY)
        val r = try { PdfRenderer(pfd) } catch (e: SecurityException) { pfd.close(); sifreliIse(); throw IllegalStateException("PDF şifreli. Önce 'Şifre kaldır' kullanın.") }
        r.use {
            for (i in 0 until it.pageCount) {
                it.openPage(i).use { s ->
                    val bmp = Bitmap.createBitmap((s.width * olcek).toInt(), (s.height * olcek).toInt(), Bitmap.Config.ARGB_8888)
                    bmp.eraseColor(Color.WHITE)
                    s.render(bmp, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                    her(i, bmp)
                }
            }
        }
    }
}

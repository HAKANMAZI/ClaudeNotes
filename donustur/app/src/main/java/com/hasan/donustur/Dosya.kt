package com.hasan.donustur

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Environment
import android.provider.MediaStore
import android.provider.OpenableColumns
import android.webkit.MimeTypeMap
import java.io.File

/** Seçilen bir dosya: Uri + adı + uzantısı. */
data class Girdi(val uri: Uri, val ad: String) {
    val uzanti: String get() = ad.substringAfterLast('.', "").lowercase()
    val kok: String get() = ad.substringBeforeLast('.')
}

/** Kaydedilen çıktı. */
data class Cikti(val uri: Uri, val ad: String, val mime: String)

object Dosya {

    fun girdi(ctx: Context, uri: Uri): Girdi {
        var ad: String? = null
        try {
            ctx.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use {
                if (it.moveToFirst()) ad = it.getString(0)
            }
        } catch (_: Exception) { }
        if (ad.isNullOrBlank()) ad = uri.lastPathSegment?.substringAfterLast('/') ?: "dosya"
        // Uzantısız gelirse MIME türünden tahmin et
        if (!ad!!.contains('.')) {
            val mime = ctx.contentResolver.getType(uri)
            val ext = MimeTypeMap.getSingleton().getExtensionFromMimeType(mime)
            if (ext != null) ad = "$ad.$ext"
        }
        return Girdi(uri, ad!!)
    }

    fun mime(ad: String): String {
        val ext = ad.substringAfterLast('.', "").lowercase()
        return when (ext) {
            "md" -> "text/markdown"
            "srt" -> "application/x-subrip"
            "vtt" -> "text/vtt"
            "m4a" -> "audio/mp4"
            else -> MimeTypeMap.getSingleton().getMimeTypeFromExtension(ext) ?: "application/octet-stream"
        }
    }

    /** Geçici çalışma dosyası. */
    fun gecici(ctx: Context, ad: String): File {
        val klasor = File(ctx.cacheDir, "is").apply { mkdirs() }
        return File(klasor, ad)
    }

    /** Uri içeriğini geçici dosyaya kopyalar (MediaExtractor, PdfRenderer vb. için). */
    fun yerelKopya(ctx: Context, g: Girdi): File {
        val f = gecici(ctx, "girdi_" + System.nanoTime() + "_" + g.ad.replace('/', '_'))
        ctx.contentResolver.openInputStream(g.uri)!!.use { i -> f.outputStream().use { o -> i.copyTo(o) } }
        return f
    }

    /** Dosyayı İndirilenler/Donustur klasörüne kaydeder. */
    fun kaydet(ctx: Context, kaynak: File, ad: String): Cikti {
        val mime = mime(ad)
        val degerler = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, ad)
            put(MediaStore.MediaColumns.MIME_TYPE, mime)
            put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/Donustur")
            put(MediaStore.MediaColumns.IS_PENDING, 1)
        }
        val cr = ctx.contentResolver
        val uri = cr.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, degerler)
            ?: throw IllegalStateException("Kaydedilemedi: $ad")
        cr.openOutputStream(uri)!!.use { o -> kaynak.inputStream().use { it.copyTo(o) } }
        degerler.clear()
        degerler.put(MediaStore.MediaColumns.IS_PENDING, 0)
        cr.update(uri, degerler, null, null)
        kaynak.delete()
        return Cikti(uri, ad, mime)
    }

    /** Geçici dosyayı oluşturup bir yazma işlemiyle doldurup kaydeder. */
    fun yazKaydet(ctx: Context, ad: String, yaz: (File) -> Unit): Cikti {
        val f = gecici(ctx, "cikti_" + System.nanoTime())
        yaz(f)
        return kaydet(ctx, f, ad)
    }

    fun metinOku(ctx: Context, g: Girdi): String =
        ctx.contentResolver.openInputStream(g.uri)!!.use { it.readBytes().toString(Charsets.UTF_8) }

    fun temizle(ctx: Context) {
        File(ctx.cacheDir, "is").deleteRecursively()
    }
}

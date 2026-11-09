package com.hasan.ekrantemizle

import android.content.ContentResolver
import android.content.ContentUris
import android.content.ContentValues
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.provider.MediaStore
import android.util.Size

data class Foto(
    val id: Long,
    val uri: Uri,
    val yol: String?,
    val eklenme: Long,     // saniye
    val silinme: Long      // çöpteyse kalıcı silinme zamanı (saniye), değilse 0
)

object Temizleyici {

    /** Kaç gün sonra çöpe atılsın */
    const val GUN = 2L

    private val TABLO = MediaStore.Images.Media.EXTERNAL_CONTENT_URI

    /** Şu an çöpe atılmayı bekleyen ekran görüntüleri */
    fun adaylar(ctx: Context): List<Foto> {
        val esik = System.currentTimeMillis() / 1000 - GUN * 24 * 60 * 60
        return sorgu(
            ctx,
            "${MediaStore.MediaColumns.RELATIVE_PATH} LIKE ? " +
                    "AND ${MediaStore.MediaColumns.DATE_ADDED} < ? " +
                    "AND ${MediaStore.MediaColumns.IS_FAVORITE} = 0",
            arrayOf("%Screenshots%", esik.toString()),
            copte = false
        )
    }

    /** Çöp kutusundaki ekran görüntüleri */
    fun copteki(ctx: Context): List<Foto> = sorgu(
        ctx,
        "${MediaStore.MediaColumns.RELATIVE_PATH} LIKE ?",
        arrayOf("%Screenshots%"),
        copte = true
    )

    /** Otomatik temizlik: tüm adayları çöpe atar */
    fun temizle(ctx: Context): Int = copeAt(ctx, adaylar(ctx))

    fun copeAt(ctx: Context, liste: List<Foto>) =
        guncelle(ctx, liste, MediaStore.MediaColumns.IS_TRASHED, 1)

    fun geriAl(ctx: Context, liste: List<Foto>) =
        guncelle(ctx, liste, MediaStore.MediaColumns.IS_TRASHED, 0)

    /** Favoriye ekler; favoriler hiç çöpe atılmaz */
    fun koru(ctx: Context, liste: List<Foto>) =
        guncelle(ctx, liste, MediaStore.MediaColumns.IS_FAVORITE, 1)

    /** Küçük/büyük resim yükler */
    fun resim(ctx: Context, foto: Foto, boyut: Int): Bitmap? {
        try {
            return ctx.contentResolver.loadThumbnail(foto.uri, Size(boyut, boyut * 2), null)
        } catch (e: Exception) {
            // Çöpteki dosyalarda olmayabilir; dosyadan oku
        }
        val yol = foto.yol ?: return null
        val sinir = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(yol, sinir)
        var oran = 1
        while (sinir.outWidth / (oran * 2) >= boyut && sinir.outHeight / (oran * 2) >= boyut) oran *= 2
        return BitmapFactory.decodeFile(yol, BitmapFactory.Options().apply { inSampleSize = oran })
    }

    private fun sorgu(ctx: Context, secim: String, arg: Array<String>, copte: Boolean): List<Foto> {
        val b = Bundle().apply {
            putString(ContentResolver.QUERY_ARG_SQL_SELECTION, secim)
            putStringArray(ContentResolver.QUERY_ARG_SQL_SELECTION_ARGS, arg)
            putString(ContentResolver.QUERY_ARG_SQL_SORT_ORDER, "${MediaStore.MediaColumns.DATE_ADDED} DESC")
            putInt(
                MediaStore.QUERY_ARG_MATCH_TRASHED,
                if (copte) MediaStore.MATCH_ONLY else MediaStore.MATCH_EXCLUDE
            )
        }
        val kolonlar = arrayOf(
            MediaStore.MediaColumns._ID,
            MediaStore.MediaColumns.DATA,
            MediaStore.MediaColumns.DATE_ADDED,
            MediaStore.MediaColumns.DATE_EXPIRES
        )
        val sonuc = mutableListOf<Foto>()
        ctx.contentResolver.query(TABLO, kolonlar, b, null)?.use { c ->
            while (c.moveToNext()) {
                val id = c.getLong(0)
                sonuc += Foto(
                    id = id,
                    uri = ContentUris.withAppendedId(TABLO, id),
                    yol = c.getString(1),
                    eklenme = c.getLong(2),
                    silinme = if (c.isNull(3)) 0 else c.getLong(3)
                )
            }
        }
        return sonuc
    }

    private fun guncelle(ctx: Context, liste: List<Foto>, kolon: String, deger: Int): Int {
        val cv = ContentValues().apply { put(kolon, deger) }
        // Çöpteki dosyalara da ulaşabilmek için
        val ek = Bundle().apply {
            putInt(MediaStore.QUERY_ARG_MATCH_TRASHED, MediaStore.MATCH_INCLUDE)
        }
        var n = 0
        for (f in liste) {
            try {
                if (ctx.contentResolver.update(f.uri, cv, ek) > 0) n++
            } catch (e: Exception) {
                // İzin yoksa veya dosya yoksa atla
            }
        }
        return n
    }
}

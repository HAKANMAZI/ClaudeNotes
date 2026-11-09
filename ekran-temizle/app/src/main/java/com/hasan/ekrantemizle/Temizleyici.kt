package com.hasan.ekrantemizle

import android.content.ContentUris
import android.content.ContentValues
import android.content.Context
import android.provider.MediaStore

object Temizleyici {

    /** Kaç gün sonra çöpe atılsın */
    const val GUN = 2L

    /**
     * "Screenshots" klasöründeki, GUN günden eski ve favori olmayan
     * ekran görüntülerini çöp kutusuna atar. Atılan sayıyı döner.
     * Android çöpteki dosyaları otuz gün sonra kendisi siler.
     */
    fun temizle(context: Context): Int {
        val esik = System.currentTimeMillis() / 1000 - GUN * 24 * 60 * 60
        val cr = context.contentResolver
        val tablo = MediaStore.Images.Media.EXTERNAL_CONTENT_URI

        val kolonlar = arrayOf(MediaStore.Images.Media._ID)
        val secim = "${MediaStore.Images.Media.RELATIVE_PATH} LIKE ? " +
                "AND ${MediaStore.Images.Media.DATE_ADDED} < ? " +
                "AND ${MediaStore.Images.Media.IS_FAVORITE} = 0"
        val argumanlar = arrayOf("%Screenshots%", esik.toString())

        val copeAt = ContentValues().apply {
            put(MediaStore.MediaColumns.IS_TRASHED, 1)
        }

        var atilan = 0
        // Sorgu zaten çöpteki dosyaları getirmez
        cr.query(tablo, kolonlar, secim, argumanlar, null)?.use { c ->
            val idKol = c.getColumnIndexOrThrow(MediaStore.Images.Media._ID)
            while (c.moveToNext()) {
                val uri = ContentUris.withAppendedId(tablo, c.getLong(idKol))
                try {
                    if (cr.update(uri, copeAt, null, null) > 0) atilan++
                } catch (e: SecurityException) {
                    // İzin yoksa bu dosyayı atla
                }
            }
        }
        return atilan
    }
}

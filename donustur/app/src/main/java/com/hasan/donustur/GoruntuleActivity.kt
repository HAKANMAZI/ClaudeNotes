package com.hasan.donustur

import android.app.Activity
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.MediaController
import android.widget.ScrollView
import android.widget.TextView
import android.widget.VideoView
import java.util.concurrent.Executors
import java.util.zip.ZipInputStream

/** Dosya açıcı: görsel, PDF, belge/metin, ses/video, ZIP içeriği. */
class GoruntuleActivity : Activity() {

    private val arka = Executors.newSingleThreadExecutor()
    @Volatile private var kapandi = false
    private lateinit var g: Girdi
    private lateinit var icerik: FrameLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val uri = intent.data ?: run { finish(); return }
        g = Dosya.girdi(this, uri)
        title = g.ad

        val kok = dikey(this).apply { setBackgroundColor(Color.rgb(245, 247, 252)) }
        val ust = yatay(this)
        ust.ekle(buton("🔁 Dönüştür") {
            startActivity(Intent(this, MainActivity::class.java).setAction(Intent.ACTION_SEND)
                .putExtra(Intent.EXTRA_STREAM, uri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION))
        }, 1f)
        if (g.uzanti in Duzenle.DUZENLENIR) ust.ekle(buton("✏️ Düzenle", 0xFFD84315.toInt()) { Duzenle.ac(this, uri) }, 1f)
        ust.ekle(buton("Paylaş", 0xFF00897B.toInt()) { paylas(listOf(uri), Dosya.mime(g.ad)) }, 1f)
        ust.ekle(buton("Başka uygulama", Color.GRAY) { disaridaAc(uri, Dosya.mime(g.ad)) }, 1f)
        kok.ekle(ust)
        icerik = FrameLayout(this)
        kok.addView(icerik, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f))
        setContentView(kok)
        goster()
    }

    override fun onDestroy() { kapandi = true; arka.shutdownNow(); super.onDestroy() }

    private fun goster() {
        when (Donusturucu.kategori(g)) {
            "gorsel" -> arkada({ Gorsel.ac(this, g, 3000) }) { bmp ->
                icerik.addView(ScrollView(this).apply { addView(ImageView(this@GoruntuleActivity).apply { setImageBitmap(bmp); adjustViewBounds = true }) })
            }
            "pdf" -> pdfGoster()
            "video", "ses" -> {
                val v = VideoView(this)
                val mc = MediaController(this); mc.setAnchorView(v); v.setMediaController(mc)
                v.setVideoURI(g.uri)
                v.setOnPreparedListener { v.start(); mc.show(0) }
                v.setOnErrorListener { _, _, _ -> mesaj("Bu medya oynatılamadı"); true }
                icerik.addView(v, FrameLayout.LayoutParams(-1, -1, Gravity.CENTER))
            }
            "arsiv" -> arkada({
                val sb = StringBuilder()
                contentResolver.openInputStream(g.uri)!!.use { ZipInputStream(it).use { z ->
                    var e = z.nextEntry; var n = 0
                    while (e != null) { sb.append(if (e.isDirectory) "📁 " else "📄 ").append(e.name).append('\n'); n++; e = z.nextEntry }
                    sb.insert(0, "$n öğe\n\n")
                } }
                sb.toString()
            }) { metinGoster(it) }
            "diger" -> arkada({ Dosya.metinOku(this, g).take(200_000) }) { metinGoster(it) }
            else -> arkada({ Donusturucu.metinCikar(this, g).take(500_000) }) { metinGoster(it) }
        }
    }

    private fun metinGoster(s: String) {
        icerik.addView(ScrollView(this).apply {
            addView(TextView(this@GoruntuleActivity).apply {
                text = s; textSize = 14f; setTextIsSelectable(true)
                setTextColor(Color.rgb(20, 20, 20)); setPadding(dp(12), dp(12), dp(12), dp(12))
            })
        })
    }

    private fun pdfGoster() {
        val sayfalar = dikey(this)
        val bilgi = yazi("Açılıyor…", 13f).apply { gravity = Gravity.CENTER }
        sayfalar.ekle(bilgi)
        icerik.addView(ScrollView(this).apply { addView(sayfalar) })
        val genislik = resources.displayMetrics.widthPixels
        arka.execute {
            try {
                val f = Dosya.yerelKopya(this, g)
                var adet = 0
                Gorsel.pdfSayfalari(f, 1f) { i, ham ->
                    if (kapandi || i >= 40) { ham.recycle(); if (i == 40) runOnUiThread { sayfalar.ekle(yazi("İlk 40 sayfa gösterildi. Tamamı için 'Başka uygulama'.", 13f)) }; return@pdfSayfalari }
                    val o = genislik.toFloat() / ham.width
                    val bmp: Bitmap = Gorsel.olcekle(ham, o.coerceAtMost(1.5f))
                    ham.recycle()
                    adet = i + 1
                    runOnUiThread {
                        sayfalar.ekle(ImageView(this).apply { setImageBitmap(bmp); adjustViewBounds = true; setBackgroundColor(Color.WHITE) })
                        bilgi.text = "$adet sayfa"
                    }
                }
                f.delete()
            } catch (e: Throwable) {
                runOnUiThread { bilgi.text = "Açılamadı: ${e.message}" }
            }
        }
    }

    private fun <T> arkada(is_: () -> T, sonra: (T) -> Unit) {
        val bekle = yazi("Açılıyor…").apply { gravity = Gravity.CENTER }
        icerik.addView(bekle)
        arka.execute {
            try {
                val s = is_()
                runOnUiThread { if (!kapandi) { icerik.removeView(bekle); sonra(s) } }
            } catch (e: Throwable) {
                runOnUiThread { bekle.text = "Önizlenemedi: ${e.message}\n\n'Başka uygulama' ile açabilirsiniz." }
            }
        }
        bekle.visibility = View.VISIBLE
    }
}

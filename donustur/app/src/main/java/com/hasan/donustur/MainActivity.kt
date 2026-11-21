package com.hasan.donustur

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.TextView
import java.util.concurrent.Executors

class MainActivity : Activity() {

    private val SECIM = 1
    private val PDF_SECIM = 2
    private val AC_SECIM = 3

    private val arka = Executors.newSingleThreadExecutor()
    private val secilenler = mutableListOf<Girdi>()

    private lateinit var liste: TextView
    private lateinit var hedefKutu: LinearLayout
    private lateinit var durum: TextView
    private lateinit var cark: ProgressBar
    private lateinit var sonucKutu: LinearLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val kok = dikey(this).apply { setPadding(dp(12), dp(12), dp(12), dp(24)) }

        kok.ekle(yazi("Dönüştür", 26f, true).apply { setTextColor(MAVI) })
        kok.ekle(yazi("Her şeyi her şeye çevirir · İnternetsiz · Reklamsız", 13f).apply { setTextColor(Color.GRAY) })

        val ust = yatay(this)
        ust.ekle(buton("📂 Dosya seç") { sec(SECIM, "*/*", true) }, 1f)
        ust.ekle(buton("✏️ PDF Düzenle", 0xFFD84315.toInt()) { pdfDuzenle() }, 1f)
        ust.ekle(buton("👁 Dosya aç", 0xFF2E7D32.toInt()) { sec(AC_SECIM, "*/*", false) }, 1f)
        kok.ekle(ust)

        liste = yazi("Henüz dosya seçilmedi.\nİpucu: Galeri ya da Dosyalar'dan Paylaş → Dönüştür de kullanabilirsiniz.", 14f).apply { setTextColor(Color.DKGRAY) }
        kok.ekle(liste)

        hedefKutu = dikey(this)
        kok.ekle(hedefKutu)

        val d = yatay(this)
        cark = ProgressBar(this).apply { visibility = View.GONE }
        durum = yazi("", 14f)
        d.ekle(cark); d.ekle(durum, 1f)
        kok.ekle(d)

        sonucKutu = dikey(this)
        kok.ekle(sonucKutu)

        kok.ekle(yazi("Çıktılar: İndirilenler/Donustur klasörü", 12f).apply { setTextColor(Color.GRAY); gravity = Gravity.CENTER })
        kok.ekle(buton("Desteklenen biçimler", Color.GRAY) { bicimler() })

        setContentView(ScrollView(this).apply { addView(kok); setBackgroundColor(Color.rgb(245, 247, 252)) })
        gelenDosyalar(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        gelenDosyalar(intent)
    }

    /** Paylaş menüsünden gelen dosyalar. */
    @Suppress("DEPRECATION")
    private fun gelenDosyalar(i: Intent?) {
        if (i == null) return
        val uriler = mutableListOf<Uri>()
        when (i.action) {
            Intent.ACTION_SEND -> (if (Build.VERSION.SDK_INT >= 33) i.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java) else i.getParcelableExtra<Uri>(Intent.EXTRA_STREAM))?.let { uriler += it }
            Intent.ACTION_SEND_MULTIPLE -> (if (Build.VERSION.SDK_INT >= 33) i.getParcelableArrayListExtra(Intent.EXTRA_STREAM, Uri::class.java) else i.getParcelableArrayListExtra<Uri>(Intent.EXTRA_STREAM))?.let { uriler += it }
        }
        if (uriler.isNotEmpty()) dosyalariAyarla(uriler)
    }

    private fun sec(kod: Int, tur: String, coklu: Boolean) {
        val i = Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType(tur)
        if (coklu) i.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true)
        startActivityForResult(i, kod)
    }

    @Deprecated("Activity API")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (resultCode != RESULT_OK || data == null) return
        val uriler = mutableListOf<Uri>()
        data.clipData?.let { c -> for (k in 0 until c.itemCount) uriler += c.getItemAt(k).uri }
        if (uriler.isEmpty()) data.data?.let { uriler += it }
        if (uriler.isEmpty()) return
        when (requestCode) {
            SECIM -> dosyalariAyarla(uriler)
            PDF_SECIM -> startActivity(Intent(this, PdfDuzenleActivity::class.java).setData(uriler[0]).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION))
            AC_SECIM -> startActivity(Intent(this, GoruntuleActivity::class.java).setData(uriler[0]).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION))
        }
    }

    private fun pdfDuzenle() {
        val pdf = secilenler.firstOrNull { it.uzanti == "pdf" }
        if (pdf != null && secilenler.size == 1) {
            startActivity(Intent(this, PdfDuzenleActivity::class.java).setData(pdf.uri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION))
        } else sec(PDF_SECIM, "application/pdf", false)
    }

    private fun dosyalariAyarla(uriler: List<Uri>) {
        secilenler.clear()
        uriler.forEach { secilenler += Dosya.girdi(this, it) }
        liste.text = "Seçilen (${secilenler.size}):\n" + secilenler.take(12).joinToString("\n") { "• " + it.ad } +
            (if (secilenler.size > 12) "\n… ve ${secilenler.size - 12} dosya daha" else "")
        sonucKutu.removeAllViews()
        durum.text = ""
        hedefleriGoster()
    }

    private fun hedefleriGoster() {
        hedefKutu.removeAllViews()
        val h = Donusturucu.hedefler(secilenler)
        if (h.isEmpty()) return
        hedefKutu.ekle(yazi("Neye dönüştürülsün?", 16f, true))
        val araclar = setOf("dondur", "aynala", "gri", "k11", "k43", "k169", "yari", "bol", "kucult", "sayfano", "cikar")
        val bicim = h.filter { it.kod !in araclar }
        val arac = h - bicim.toSet()
        hedefKutu.ekle(izgara(bicim.map { hd -> buton(hd.etiket, if (hd.kod == "duzenle") 0xFFD84315.toInt() else MAVI) { baslat(hd) } }))
        if (arac.isNotEmpty()) {
            hedefKutu.ekle(yazi("Araçlar", 16f, true))
            hedefKutu.ekle(izgara(arac.map { hd -> buton(hd.etiket, if (hd.kod == "duzenle") 0xFFD84315.toInt() else 0xFF5E35B1.toInt()) { baslat(hd) } }))
        }
    }

    private fun baslat(h: Hedef) {
        if (h.kod == "duzenle") { pdfDuzenle(); return }
        val girdiler = secilenler.toList()
        cark.visibility = View.VISIBLE
        durum.text = "Başlıyor…"
        sonucKutu.removeAllViews()
        arka.execute {
            val r = Donusturucu.calistir(this, girdiler, h) { s -> runOnUiThread { durum.text = s } }
            runOnUiThread { sonuclariGoster(r) }
        }
    }

    private fun sonuclariGoster(r: Donusturucu.Rapor) {
        cark.visibility = View.GONE
        durum.text = "✅ ${r.ciktilar.size} dosya hazır" + if (r.hatalar.isNotEmpty()) " · ⚠️ ${r.hatalar.size} hata" else ""
        r.hatalar.forEach { sonucKutu.ekle(yazi("⚠️ $it", 13f).apply { setTextColor(Color.rgb(180, 30, 30)) }) }
        if (r.ciktilar.size > 1) sonucKutu.ekle(buton("Hepsini paylaş (${r.ciktilar.size})", 0xFF00897B.toInt()) { paylas(r.ciktilar.map { it.uri }) })
        for (c in r.ciktilar.take(100)) {
            val s = yatay(this)
            s.ekle(yazi(c.ad, 14f), 1f)
            s.ekle(buton("Aç", 0xFF2E7D32.toInt()) {
                startActivity(Intent(this, GoruntuleActivity::class.java).setDataAndType(c.uri, c.mime).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION))
            })
            s.ekle(buton("Paylaş", 0xFF00897B.toInt()) { paylas(listOf(c.uri), c.mime) })
            sonucKutu.ekle(s)
        }
    }

    private fun bicimler() {
        AlertDialog.Builder(this).setTitle("Desteklenen biçimler").setMessage(
            """
            🖼 Görsel: JPG, PNG, WEBP, HEIC, AVIF, BMP, GIF → JPG, PNG, WEBP, PDF · döndür, aynala, siyah-beyaz, kırp (1:1, 4:3, 16:9), küçült
            📄 PDF → JPG, PNG, TXT · birleştir, böl, küçült, sayfa no · Düzenle: yazı, filigran, imza, resim, karartma, döndür, sil, sırala, ayıkla, şifrele/şifre kaldır
            📝 DOCX, ODT, EPUB, PPTX → PDF, TXT (Office gerekmez)
            📊 XLSX → CSV, JSON, HTML, PDF · CSV ↔ JSON
            🔤 TXT, Markdown, HTML, XML, JSON → PDF, HTML, TXT
            💬 Altyazı: SRT ↔ WebVTT
            🎬 Video: MP4, MOV, MKV, WEBM, 3GP → M4A, WAV, sessiz MP4, kare (JPG)
            🎵 Ses: MP3, M4A, AAC, FLAC, OGG, OPUS, WAV → WAV, M4A
            🗜 Her şey → ZIP · ZIP'i aç
            🔀 Karışık dosyalar → Hepsi tek PDF
            """.trimIndent()
        ).setPositiveButton("Tamam", null).show()
    }
}

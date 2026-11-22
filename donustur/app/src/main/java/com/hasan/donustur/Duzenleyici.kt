package com.hasan.donustur

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import java.io.File
import java.util.concurrent.Executors

/** Dosyayı türüne göre doğru düzenleyicide açar. */
object Duzenle {
    val DUZENLENIR = setOf("pdf", "docx", "xlsx", "csv", "txt", "md", "markdown", "json", "xml", "html", "htm", "srt", "vtt", "log", "ini", "yaml", "yml")

    fun ac(a: Activity, uri: Uri) {
        val g = Dosya.girdi(a, uri)
        val hedef = when (g.uzanti) {
            "pdf" -> PdfDuzenleActivity::class.java
            "docx" -> WordActivity::class.java
            "xlsx", "csv" -> TabloActivity::class.java
            "doc", "xls", "ppt" -> { a.mesaj("Eski .${g.uzanti} biçimi düzenlenemez. Word/Excel'de .${g.uzanti}x olarak kaydedin."); return }
            else -> if (g.uzanti in DUZENLENIR || g.uzanti.isEmpty()) MetinDuzenleActivity::class.java
                    else { a.mesaj("Bu tür düzenlenemiyor: .${g.uzanti}"); return }
        }
        a.startActivity(Intent(a, hedef).setData(uri)
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION))
    }

    /** Yeni boş belge: tur = docx / xlsx / txt */
    fun yeni(a: Activity, tur: String) {
        val hedef = when (tur) { "docx" -> WordActivity::class.java; "xlsx" -> TabloActivity::class.java; else -> MetinDuzenleActivity::class.java }
        a.startActivity(Intent(a, hedef).putExtra("yeni", tur))
    }
}

/** Word / Excel / Metin düzenleyicilerinin ortak iskeleti: üst çubuk, kaydet, farklı kaydet, paylaş. */
abstract class DuzenleyiciActivity : Activity() {

    protected val arka = Executors.newSingleThreadExecutor()
    protected var uri: Uri? = null
    protected var ad = "yeni_belge"
    protected abstract val uzanti: String
    protected var degisti = false
        set(v) { field = v; baslikYaz() }

    protected lateinit var kok: LinearLayout
    protected lateinit var cark: ProgressBar
    protected lateinit var durum: TextView

    /** Belgeyi f dosyasına yazar (arka planda çağrılır). */
    protected abstract fun dosyayaYaz(f: File)
    protected abstract fun duzMetin(): String
    protected abstract fun yukle()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        uri = intent.data
        uri?.let { ad = Dosya.girdi(this, it).kok }
        kok = dikey(this).apply { setBackgroundColor(Color.rgb(245, 247, 252)) }
        val ust = yatay(this)
        cark = ProgressBar(this).apply { visibility = View.GONE }
        durum = yazi("", 13f)
        ust.ekle(buton("💾 Kaydet", 0xFF2E7D32.toInt()) { kaydet(false) })
        ust.ekle(buton("Farklı kaydet", 0xFF00897B.toInt()) { sor("Farklı kaydet", "Dosya adı", ad) { s -> if (s.isNotBlank()) { ad = s.trim(); kaydet(true) } } })
        ust.ekle(buton("PDF", 0xFFD84315.toInt()) { pdfOlarak() })
        ust.ekle(buton("Paylaş", MAVI) { paylasKaydet() })
        ekAraclar(ust)
        ust.ekle(cark); ust.ekle(durum)
        kok.ekle(HorizontalScrollView(this).apply { addView(ust); isHorizontalScrollBarEnabled = false }, kenar = 0)
        baslikYaz()
        yukle()
    }

    /** Alt sınıflar üst çubuğa düğme ekleyebilir. */
    protected open fun ekAraclar(cubuk: LinearLayout) {}

    override fun onDestroy() { arka.shutdownNow(); super.onDestroy() }

    protected fun baslikYaz() { title = (if (degisti) "● " else "") + "$ad.$uzanti" }

    protected fun isle(mesajBasta: String, is_: () -> Unit) {
        cark.visibility = View.VISIBLE; durum.text = mesajBasta
        arka.execute {
            try { is_() }
            catch (e: Throwable) { runOnUiThread { mesaj("Hata: ${e.message ?: e.javaClass.simpleName}") } }
            finally { runOnUiThread { cark.visibility = View.GONE; durum.text = "" } }
        }
    }

    /** Kaydet: mümkünse aslının üzerine; değilse İndirilenler/Donustur'a kopya. */
    protected fun kaydet(farkli: Boolean, sonra: (Uri) -> Unit = {}) {
        onceKaydet()
        isle("Kaydediliyor…") {
            val f = Dosya.gecici(this, "kayit_${System.nanoTime()}.$uzanti")
            dosyayaYaz(f)
            val u = uri
            if (!farkli && u != null && Dosya.uzerineYaz(this, u, f)) {
                f.delete()
                runOnUiThread { degisti = false; mesaj("Kaydedildi ✓"); sonra(u) }
            } else {
                val c = Dosya.kaydet(this, f, "$ad.$uzanti")
                uri = c.uri
                runOnUiThread {
                    degisti = false
                    mesaj(if (!farkli && u != null) "Asıl dosyaya yazma izni yok. Kopya kaydedildi: İndirilenler/Donustur/${c.ad}" else "Kaydedildi: İndirilenler/Donustur/${c.ad}")
                    sonra(c.uri)
                }
            }
        }
    }

    /** Ekrandaki son değişiklikleri modele aktarır (UI iş parçacığında). */
    protected open fun onceKaydet() {}

    private fun paylasKaydet() = kaydet(false) { u -> paylas(listOf(u), Dosya.mime("$ad.$uzanti")) }

    private fun pdfOlarak() {
        onceKaydet()
        val metin = duzMetin()
        isle("PDF yapılıyor…") {
            val c = Dosya.yazKaydet(this, "$ad.pdf") { Gorsel.metindenPdf(metin, it) }
            runOnUiThread {
                AlertDialog.Builder(this).setTitle("PDF hazır").setMessage("İndirilenler/Donustur/${c.ad}")
                    .setPositiveButton("Aç") { _, _ -> disaridaAc(c.uri, "application/pdf") }
                    .setNeutralButton("Paylaş") { _, _ -> paylas(listOf(c.uri), "application/pdf") }
                    .setNegativeButton("Tamam", null).show()
            }
        }
    }

    @Deprecated("Activity API")
    override fun onBackPressed() {
        onceKaydet()
        if (!degisti) { super.onBackPressed(); return }
        AlertDialog.Builder(this).setTitle("Değişiklikler kaydedilsin mi?")
            .setPositiveButton("Kaydet") { _, _ -> kaydet(false) { finish() } }
            .setNegativeButton("Kaydetme") { _, _ -> finish() }
            .setNeutralButton("Vazgeç", null).show()
    }
}

/** Başka uygulamadan "Düzenle / Birlikte aç" ile gelen dosyayı uygun düzenleyiciye yollar. */
class DuzenleYonlendir : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        intent.data?.let { Duzenle.ac(this, it) }
        finish()
    }
}

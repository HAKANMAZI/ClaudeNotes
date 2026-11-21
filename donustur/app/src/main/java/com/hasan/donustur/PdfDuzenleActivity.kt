package com.hasan.donustur

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.os.Bundle
import android.os.ParcelFileDescriptor
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.BaseAdapter
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.GridView
import android.widget.HorizontalScrollView
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.RadioButton
import android.widget.RadioGroup
import android.widget.TextView
import com.tom_roush.pdfbox.pdmodel.encryption.InvalidPasswordException
import java.io.File
import java.util.concurrent.Executors

/** PDF düzenleyici: sayfa küçük resimleri + seçim + işlemler + geri al. */
class PdfDuzenleActivity : Activity() {

    private val RESIM_SEC = 10
    private val PDF_SEC = 11

    private val arka = Executors.newSingleThreadExecutor()
    private var calisma: File? = null
    private val gecmis = ArrayDeque<File>()
    private var ad = "belge"
    private var sayfaSayisi = 0
    private val secili = sortedSetOf<Int>()
    private var kucukler: List<Bitmap> = emptyList()

    private lateinit var bilgi: TextView
    private lateinit var cark: ProgressBar
    private lateinit var izgara: GridView
    private lateinit var adapter: SayfaAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val uri = intent.data ?: run { finish(); return }
        val g = Dosya.girdi(this, uri)
        ad = g.kok
        title = "PDF Düzenle — ${g.ad}"

        val kok = dikey(this).apply { setBackgroundColor(Color.rgb(240, 242, 248)) }
        val ust = yatay(this)
        cark = ProgressBar(this)
        bilgi = yazi("Açılıyor…", 14f)
        ust.ekle(cark); ust.ekle(bilgi, 1f)
        ust.ekle(buton("↩ Geri al", Color.GRAY) { geriAl() })
        ust.ekle(buton("💾 Kaydet", 0xFF2E7D32.toInt()) { kaydet(false) })
        kok.ekle(ust)

        kok.ekle(araclar(listOf(
            "☑ Tümü" to { tumunuSec() },
            "↻ Döndür" to { uygula("Döndürüldü") { f, c -> PdfIslem.dondur(this, f, hedef(), 90, c) } },
            "🗑 Sil" to { sil() },
            "📤 Ayıkla" to { ayikla() },
            "🔀 Sırala" to { sirala() },
            "⇅ Ters" to { uygula("Ters çevrildi") { f, c -> PdfIslem.yenidenSirala(this, f, (0 until sayfaSayisi).reversed().toList(), c) } },
            "➕ PDF ekle" to { sec(PDF_SEC, "application/pdf") }
        )))
        kok.ekle(araclar(listOf(
            "🔤 Yazı" to { yaziEkle() },
            "🖊 İmza" to { imzaAt() },
            "🖼 Resim" to { sec(RESIM_SEC, "image/*") },
            "⬛ Karart" to { alan(true) },
            "⬜ Beyazla" to { alan(false) },
            "💧 Filigran" to { sor("Filigran", "ör. GİZLİ, TASLAK", "TASLAK") { s -> if (s.isNotBlank()) uygula("Filigran eklendi") { f, c -> PdfIslem.filigran(this, f, s, c) } } },
            "# Sayfa no" to { uygula("Sayfa numarası eklendi") { f, c -> PdfIslem.sayfaNumarasi(this, f, c) } }
        )))
        kok.ekle(araclar(listOf(
            "🔒 Şifrele" to { sor("PDF şifresi", "Şifre", sifre = true) { s -> if (s.isNotEmpty()) sifrele(s) } },
            "🗜 Küçült" to { uygula("Küçültüldü (sayfalar resme çevrildi)") { f, c -> PdfIslem.kucult(this, f, c) } },
            "ℹ Bilgi" to { bilgiDuzenle() },
            "📝 Metni al" to { metniAl() },
            "Paylaş" to { kaydet(true) }
        )))

        kok.ekle(yazi("Sayfaya dokunarak seçin. Seçim yoksa işlem tüm sayfalara uygulanır.", 12f).apply { setTextColor(Color.GRAY); setPadding(dp(8), 0, 0, 0) })

        adapter = SayfaAdapter()
        izgara = GridView(this).apply {
            numColumns = 3; this.adapter = this@PdfDuzenleActivity.adapter
            verticalSpacing = dp(6); horizontalSpacing = dp(6); setPadding(dp(6), dp(6), dp(6), dp(6))
            setOnItemClickListener { _, _, i, _ -> if (!secili.remove(i)) secili.add(i); bilgiYaz(); this@PdfDuzenleActivity.adapter.notifyDataSetChanged() }
        }
        kok.addView(izgara, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(kok)

        arkada {
            val f = Dosya.yerelKopya(this, g)
            hazirla(f)
        }
    }

    override fun onDestroy() { arka.shutdownNow(); super.onDestroy() }

    private fun araclar(liste: List<Pair<String, () -> Unit>>): View {
        val s = yatay(this)
        liste.forEach { (y, t) -> s.ekle(buton(y, 0xFF37474F.toInt(), t), kenar = 3) }
        return HorizontalScrollView(this).apply { addView(s); isHorizontalScrollBarEnabled = false }
    }

    // ----------------------------------------------------------------------------

    /** Şifreliyse şifre sorar; değilse küçük resimleri hazırlar. Arka planda çağrılır. */
    private fun hazirla(f: File) {
        try {
            val sifreli = PdfIslem.ac(this, f).use { it.isEncrypted }
            if (sifreli) {
                val c = Dosya.gecici(this, "c_${System.nanoTime()}.pdf")
                PdfIslem.sifreKaldir(this, f, "", c); f.delete()
                yukle(c)
            } else yukle(f)
        } catch (e: InvalidPasswordException) {
            runOnUiThread {
                sor("Bu PDF şifreli", "Şifreyi girin", sifre = true) { s ->
                    arkada {
                        val c = Dosya.gecici(this, "c_${System.nanoTime()}.pdf")
                        try { PdfIslem.sifreKaldir(this, f, s, c); yukle(c) }
                        catch (e2: InvalidPasswordException) { runOnUiThread { mesaj("Şifre yanlış") }; hazirla(f) }
                    }
                }
            }
        }
    }

    private fun yukle(f: File) {
        calisma = f
        val liste = mutableListOf<Bitmap>()
        Gorsel.pdfSayfalari(f, 0.35f) { i, b -> if (i < 400) liste.add(b) else b.recycle() }
        sayfaSayisi = PdfIslem.sayfaSayisi(this, f)
        runOnUiThread {
            kucukler = liste
            secili.retainAll { it < sayfaSayisi }
            adapter.notifyDataSetChanged()
            bilgiYaz()
        }
    }

    private fun bilgiYaz() {
        bilgi.text = "$sayfaSayisi sayfa" + (if (secili.isNotEmpty()) " · ${secili.size} seçili" else "") +
            (if (gecmis.isNotEmpty()) " · ${gecmis.size} değişiklik" else "")
    }

    private fun hedef(): List<Int> = if (secili.isEmpty()) (0 until sayfaSayisi).toList() else secili.toList()

    private fun arkada(is_: () -> Unit) {
        cark.visibility = View.VISIBLE
        arka.execute {
            try { is_() }
            catch (e: Throwable) { runOnUiThread { mesaj("Hata: ${e.message ?: e.javaClass.simpleName}") } }
            finally { runOnUiThread { cark.visibility = View.GONE } }
        }
    }

    /** Bir işlemi çalışma dosyasına uygular; eski hali geri alma için saklanır. */
    private fun uygula(sonucMesaji: String, secimiTemizle: Boolean = false, is_: (File, File) -> Unit) {
        val f = calisma ?: return
        arkada {
            val c = Dosya.gecici(this, "c_${System.nanoTime()}.pdf")
            is_(f, c)
            gecmis.addLast(f)
            if (gecmis.size > 15) gecmis.removeFirst().delete()
            if (secimiTemizle) runOnUiThread { secili.clear() }
            yukle(c)
            runOnUiThread { mesaj(sonucMesaji) }
        }
    }

    private fun geriAl() {
        val onceki = gecmis.removeLastOrNull() ?: run { mesaj("Geri alınacak bir şey yok"); return }
        val simdiki = calisma
        arkada { yukle(onceki); simdiki?.delete() }
    }

    private fun tumunuSec() {
        if (secili.size == sayfaSayisi) secili.clear() else { secili.clear(); secili.addAll(0 until sayfaSayisi) }
        adapter.notifyDataSetChanged(); bilgiYaz()
    }

    private fun sil() {
        if (secili.isEmpty()) { mesaj("Önce silinecek sayfaları seçin"); return }
        val s = secili.toList()
        uygula("${s.size} sayfa silindi", true) { f, c -> PdfIslem.sayfalariSil(this, f, s, c) }
    }

    private fun ayikla() {
        if (secili.isEmpty()) { mesaj("Önce sayfaları seçin"); return }
        val f = calisma ?: return
        val s = secili.toList()
        arkada {
            val c = Dosya.yazKaydet(this, "${ad}_secilen_${s.size}_sayfa.pdf") { PdfIslem.sayfalariAl(this, f, s, it) }
            runOnUiThread { mesaj("Kaydedildi: İndirilenler/Donustur/${c.ad}") }
        }
    }

    /** "3,1,2,5-8" gibi yeni sıra; ya da seçilenleri başa al. */
    private fun sirala() {
        val varsayilan = if (secili.isNotEmpty()) (secili.map { it + 1 } + (1..sayfaSayisi).filter { it - 1 !in secili }).joinToString(",") else "1-$sayfaSayisi"
        sor("Yeni sayfa sırası", "ör. 3,1,2,5-8", varsayilan) { s ->
            try {
                val sira = mutableListOf<Int>()
                s.split(',').map { it.trim() }.filter { it.isNotEmpty() }.forEach { p ->
                    if (p.contains('-')) {
                        val (a, b) = p.split('-').map { it.trim().toInt() }
                        if (a <= b) sira.addAll((a..b).map { it - 1 }) else sira.addAll((a downTo b).map { it - 1 })
                    } else sira += p.toInt() - 1
                }
                require(sira.isNotEmpty() && sira.all { it in 0 until sayfaSayisi })
                uygula("Sayfalar yeniden sıralandı", true) { f, c -> PdfIslem.yenidenSirala(this, f, sira, c) }
            } catch (e: Exception) { mesaj("Sıra anlaşılamadı. Örnek: 3,1,2,5-8 (1-$sayfaSayisi arası)") }
        }
    }

    // ---------- konum seçimli işlemler ----------

    private fun sayfaResmi(i: Int, genislik: Int = 900): Bitmap =
        ParcelFileDescriptor.open(calisma!!, ParcelFileDescriptor.MODE_READ_ONLY).use { pfd ->
            PdfRenderer(pfd).use { r ->
                r.openPage(i).use { p ->
                    val o = genislik.toFloat() / p.width
                    val b = Bitmap.createBitmap(genislik, (p.height * o).toInt(), Bitmap.Config.ARGB_8888)
                    b.eraseColor(Color.WHITE)
                    p.render(b, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                    b
                }
            }
        }

    /** İlk hedef sayfayı gösterip dokunma/sürükleme ile yer seçtirir. */
    private fun konumSec(ipucu: String, ek: View? = null, tamam: (FloatArray) -> Unit) {
        if (calisma == null) return
        val ilk = hedef().first()
        val v = KutuSecView(this, sayfaResmi(ilk), ipucu)
        val kap = dikey(this)
        ek?.let { kap.ekle(it) }
        kap.ekle(v)
        val coklu = hedef().size
        AlertDialog.Builder(this).setTitle("Sayfa ${ilk + 1}" + if (coklu > 1) " (aynı yer $coklu sayfaya)" else "")
            .setView(kap)
            .setPositiveButton("Uygula") { _, _ -> v.secim?.let(tamam) ?: mesaj("Sayfada bir yere dokunun") }
            .setNegativeButton("Vazgeç", null).show()
    }

    private fun yaziEkle() {
        if (calisma == null) return
        val e = EditText(this).apply { hint = "Eklenecek yazı (çok satır olabilir)"; minLines = 2 }
        val boylar = listOf(10f, 14f, 18f, 24f, 36f)
        val renkler = listOf("Siyah" to Color.BLACK, "Kırmızı" to Color.rgb(200, 0, 0), "Mavi" to Color.rgb(0, 60, 200))
        val boyGrup = RadioGroup(this).apply { orientation = RadioGroup.HORIZONTAL }
        boylar.forEachIndexed { i, b -> boyGrup.addView(RadioButton(this).apply { id = 100 + i; text = b.toInt().toString(); isChecked = i == 1 }) }
        val renkGrup = RadioGroup(this).apply { orientation = RadioGroup.HORIZONTAL }
        renkler.forEachIndexed { i, (r, _) -> renkGrup.addView(RadioButton(this).apply { id = 200 + i; text = r; isChecked = i == 0 }) }
        val kap = dikey(this).apply { setPadding(dp(12), 0, dp(12), 0) }
        kap.ekle(e); kap.ekle(yazi("Boyut", 13f)); kap.ekle(boyGrup); kap.ekle(yazi("Renk", 13f)); kap.ekle(renkGrup)
        AlertDialog.Builder(this).setTitle("Yazı ekle").setView(kap)
            .setPositiveButton("Yerini seç") { _, _ ->
                val metin = e.text.toString()
                if (metin.isBlank()) return@setPositiveButton
                val boy = boylar[(boyGrup.checkedRadioButtonId - 100).coerceIn(0, boylar.size - 1)]
                val renk = renkler[(renkGrup.checkedRadioButtonId - 200).coerceIn(0, renkler.size - 1)].second
                val s = hedef()
                konumSec("Yazının başlayacağı yere dokunun") { k ->
                    uygula("Yazı eklendi") { f, c -> PdfIslem.yaziEkle(this, f, s, metin, boy, k[0], k[1], renk, c) }
                }
            }.setNegativeButton("Vazgeç", null).show()
    }

    private fun imzaAt() {
        if (calisma == null) return
        val imza = ImzaView(this)
        val kap = dikey(this).apply { setPadding(dp(12), 0, dp(12), 0) }
        kap.ekle(yazi("Parmağınızla imzanızı atın:", 13f)); kap.ekle(imza)
        kap.ekle(buton("Temizle", Color.GRAY) { imza.temizle() })
        AlertDialog.Builder(this).setTitle("İmza").setView(kap)
            .setPositiveButton("Yerini seç") { _, _ ->
                if (imza.bos) { mesaj("İmza boş"); return@setPositiveButton }
                resimYerlestir(imza.bitmap(), "İmza")
            }.setNegativeButton("Vazgeç", null).show()
    }

    private fun resimYerlestir(bmp: Bitmap, ne: String) {
        val s = hedef()
        konumSec("$ne için alanı parmakla çizin (genişlik önemli)") { k ->
            val w = if (k[2] < 0.02f) 0.3f else k[2]
            uygula("$ne eklendi") { f, c -> PdfIslem.resimEkle(this, f, s, bmp, k[0], k[1], w, c) }
        }
    }

    private fun alan(siyah: Boolean) {
        if (calisma == null) return
        val s = hedef()
        konumSec(if (siyah) "Karartılacak alanı çizin" else "Silinecek (beyazlanacak) alanı çizin") { k ->
            if (k[2] < 0.01f || k[3] < 0.005f) { mesaj("Bir alan çizin"); return@konumSec }
            uygula(if (siyah) "Alan karartıldı" else "Alan beyazlandı") { f, c -> PdfIslem.alanKapat(this, f, s, k[0], k[1], k[2], k[3], siyah, c) }
        }
    }

    private fun sifrele(sifre: String) {
        val f = calisma ?: return
        arkada {
            val c = Dosya.yazKaydet(this, "${ad}_sifreli.pdf") { PdfIslem.sifrele(this, f, sifre, it) }
            runOnUiThread { mesaj("Şifreli kopya kaydedildi: İndirilenler/Donustur/${c.ad}") }
        }
    }

    private fun bilgiDuzenle() {
        val f = calisma ?: return
        sor("Başlık", "Belge başlığı (boş = sil)", ad) { b ->
            sor("Yazar", "Yazar (boş = sil)") { y -> uygula("Bilgiler güncellendi") { ff, c -> PdfIslem.bilgi(this, ff, b, y, c) } }
        }
        f.exists()
    }

    private fun metniAl() {
        val f = calisma ?: return
        arkada {
            val c = Dosya.yazKaydet(this, "$ad.txt") { it.writeText(PdfIslem.metin(this, f)) }
            runOnUiThread { mesaj("Metin kaydedildi: ${c.ad}") }
        }
    }

    private fun kaydet(paylasilsin: Boolean) {
        val f = calisma ?: return
        arkada {
            val kopya = Dosya.gecici(this, "k_${System.nanoTime()}.pdf")
            f.copyTo(kopya, true)
            val c = Dosya.kaydet(this, kopya, "${ad}_duzenlendi.pdf")
            runOnUiThread {
                if (paylasilsin) paylas(listOf(c.uri), "application/pdf")
                else AlertDialog.Builder(this).setTitle("Kaydedildi")
                    .setMessage("İndirilenler/Donustur/${c.ad}")
                    .setPositiveButton("Aç") { _, _ -> disaridaAc(c.uri, "application/pdf") }
                    .setNeutralButton("Paylaş") { _, _ -> paylas(listOf(c.uri), "application/pdf") }
                    .setNegativeButton("Tamam", null).show()
            }
        }
    }

    // ---------- dosya seçimi (resim / eklenecek PDF) ----------

    private fun sec(kod: Int, tur: String) {
        if (calisma == null) return
        startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType(tur), kod)
    }

    @Deprecated("Activity API")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        val uri: Uri = data?.data ?: return
        if (resultCode != RESULT_OK) return
        val g = Dosya.girdi(this, uri)
        when (requestCode) {
            RESIM_SEC -> arkada {
                val bmp = Gorsel.ac(this, g, 2000)
                runOnUiThread { resimYerlestir(bmp, "Resim") }
            }
            PDF_SEC -> uygula("${g.ad} sona eklendi") { f, c ->
                val ek = Dosya.yerelKopya(this, g)
                PdfIslem.birlestir(this, listOf(f, ek), c)
                ek.delete()
            }
        }
    }

    // ---------- küçük resim ızgarası ----------

    inner class SayfaAdapter : BaseAdapter() {
        override fun getCount() = kucukler.size
        override fun getItem(i: Int) = kucukler[i]
        override fun getItemId(i: Int) = i.toLong()
        override fun getView(i: Int, eski: View?, ust: ViewGroup?): View {
            val kutu = (eski as? FrameLayout) ?: FrameLayout(this@PdfDuzenleActivity).apply {
                addView(ImageView(context).apply { adjustViewBounds = true; scaleType = ImageView.ScaleType.FIT_CENTER },
                    FrameLayout.LayoutParams(-1, dp(170)))
                addView(TextView(context).apply {
                    setTextColor(Color.WHITE); textSize = 12f; setPadding(dp(6), dp(2), dp(6), dp(2))
                }, FrameLayout.LayoutParams(-2, -2, Gravity.BOTTOM or Gravity.END))
            }
            val img = kutu.getChildAt(0) as ImageView
            val no = kutu.getChildAt(1) as TextView
            img.setImageBitmap(kucukler[i])
            val sec = i in secili
            no.text = if (sec) "✓ ${i + 1}" else "${i + 1}"
            no.setBackgroundColor(if (sec) MAVI else Color.argb(160, 0, 0, 0))
            kutu.setPadding(dp(4), dp(4), dp(4), dp(4))
            kutu.setBackgroundColor(if (sec) MAVI else Color.WHITE)
            return kutu
        }
    }
}

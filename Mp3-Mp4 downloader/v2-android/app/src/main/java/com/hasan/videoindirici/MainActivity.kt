package com.hasan.videoindirici

import android.app.DownloadManager
import android.content.ClipboardManager
import android.content.ContentValues
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.view.View
import android.view.WindowManager
import android.webkit.MimeTypeMap
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.lifecycleScope
import com.google.android.material.button.MaterialButtonToggleGroup
import com.google.android.material.card.MaterialCardView
import com.google.android.material.chip.Chip
import com.google.android.material.chip.ChipGroup
import com.google.android.material.progressindicator.LinearProgressIndicator
import com.google.android.material.snackbar.Snackbar
import com.google.android.material.textfield.TextInputEditText
import com.google.android.material.textfield.TextInputLayout
import com.yausername.ffmpeg.FFmpeg
import com.yausername.youtubedl_android.YoutubeDL
import com.yausername.youtubedl_android.YoutubeDLRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.net.URL

class MainActivity : AppCompatActivity() {

    private enum class Bicim { MP4, MP3, M4A }

    private lateinit var link: TextInputEditText
    private lateinit var bicimGrup: MaterialButtonToggleGroup
    private lateinit var bicimAciklama: TextView
    private lateinit var kaliteBaslik: TextView
    private lateinit var kalite: ChipGroup
    private lateinit var onizleme: MaterialCardView
    private lateinit var kapak: ImageView
    private lateinit var baslik: TextView
    private lateinit var altBilgi: TextView
    private lateinit var cubuk: LinearProgressIndicator
    private lateinit var durum: TextView
    private lateinit var iptal: Button
    private lateinit var ac: Button
    private lateinit var indir: Button
    private lateinit var guncelle: Button
    private lateinit var motorDurum: TextView

    private var hazir = false
    private var calisiyor = false
    private var sonDosya: Uri? = null
    private var sonTur: String? = null
    private val islemNo = "indirme"

    private val videoKalite = listOf("En iyi", "1080p", "720p", "480p", "360p")
    private val mp3Kalite = listOf("320 kbps", "192 kbps", "128 kbps")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        setContentView(R.layout.activity_main)

        link = findViewById(R.id.link)
        bicimGrup = findViewById(R.id.bicim)
        bicimAciklama = findViewById(R.id.bicimAciklama)
        kaliteBaslik = findViewById(R.id.kaliteBaslik)
        kalite = findViewById(R.id.kalite)
        onizleme = findViewById(R.id.onizleme)
        kapak = findViewById(R.id.kapak)
        baslik = findViewById(R.id.baslik)
        altBilgi = findViewById(R.id.altBilgi)
        cubuk = findViewById(R.id.cubuk)
        durum = findViewById(R.id.durum)
        iptal = findViewById(R.id.iptal)
        ac = findViewById(R.id.ac)
        indir = findViewById(R.id.indir)
        guncelle = findViewById(R.id.guncelle)
        motorDurum = findViewById(R.id.motorDurum)

        // Durum çubuğu altına taşmasın
        val ust = findViewById<View>(R.id.ust)
        val ustBosluk = ust.paddingTop
        ViewCompat.setOnApplyWindowInsetsListener(ust) { v, ic ->
            val bar = ic.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(v.paddingLeft, ustBosluk + bar.top, v.paddingRight, v.paddingBottom)
            findViewById<View>(R.id.kok).setPadding(0, 0, 0, bar.bottom)
            ic
        }

        findViewById<TextInputLayout>(R.id.linkKutu).setEndIconOnClickListener {
            val pano = getSystemService(ClipboardManager::class.java)
            val metin = pano.primaryClip?.getItemAt(0)?.coerceToText(this)?.toString()
            if (metin.isNullOrBlank()) Toast.makeText(this, "Panoda link yok", Toast.LENGTH_SHORT).show()
            else link.setText(linkiAyikla(metin))
        }

        bicimGrup.addOnButtonCheckedListener { _, _, secili -> if (secili) bicimDegisti() }
        bicimDegisti()

        indir.isEnabled = false
        indir.setOnClickListener { baslat() }
        iptal.setOnClickListener { YoutubeDL.getInstance().destroyProcessById(islemNo) }
        ac.setOnClickListener { dosyayiAc() }
        guncelle.setOnClickListener { motoruGuncelle(elle = true) }
        findViewById<Button>(R.id.klasor).setOnClickListener {
            try { startActivity(Intent(DownloadManager.ACTION_VIEW_DOWNLOADS)) }
            catch (e: Exception) { Toast.makeText(this, "İndirilenler / VideoIndirici", Toast.LENGTH_LONG).show() }
        }

        paylasilanLink(intent)
        kur()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        paylasilanLink(intent)
    }

    private fun secilenBicim() = when (bicimGrup.checkedButtonId) {
        R.id.mp3 -> Bicim.MP3
        R.id.m4a -> Bicim.M4A
        else -> Bicim.MP4
    }

    /** Biçim değişince kalite seçeneklerini yenile */
    private fun bicimDegisti() {
        val b = secilenBicim()
        bicimAciklama.text = when (b) {
            Bicim.MP4 -> "Görüntü + ses. Her cihazda oynar."
            Bicim.MP3 -> "Sadece ses. Müzik çalarlarda, arabada çalar."
            Bicim.M4A -> "Sadece ses, orijinal kalite. Daha küçük dosya, dönüştürme yok."
        }
        val liste = when (b) {
            Bicim.MP4 -> videoKalite
            Bicim.MP3 -> mp3Kalite
            Bicim.M4A -> emptyList()
        }
        kalite.removeAllViews()
        liste.forEachIndexed { i, ad ->
            val c = Chip(this).apply {
                id = View.generateViewId()
                text = ad
                isCheckable = true
                isCheckedIconVisible = true
                // MP3 için varsayılan 192 kbps, video için "En iyi"
                isChecked = if (b == Bicim.MP3) i == 1 else i == 0
            }
            kalite.addView(c)
        }
        val v = if (liste.isEmpty()) View.GONE else View.VISIBLE
        kalite.visibility = v
        kaliteBaslik.visibility = v
    }

    private fun secilenKalite(): String =
        kalite.findViewById<Chip>(kalite.checkedChipId)?.text?.toString() ?: ""

    private fun paylasilanLink(i: Intent?) {
        if (i?.action == Intent.ACTION_SEND) {
            i.getStringExtra(Intent.EXTRA_TEXT)?.let { link.setText(linkiAyikla(it)) }
        }
    }

    private fun linkiAyikla(metin: String): String =
        Regex("https?://\\S+").find(metin)?.value ?: metin.trim()

    /** yt-dlp ve ffmpeg'i ilk açılışta hazırla */
    private fun kur() {
        lifecycleScope.launch {
            val hata = withContext(Dispatchers.IO) {
                try {
                    YoutubeDL.getInstance().init(applicationContext)
                    FFmpeg.getInstance().init(applicationContext)
                    null
                } catch (e: Exception) { e.message }
            }
            if (hata != null) {
                indir.text = "Kurulum hatası"
                motorDurum.text = hata
                return@launch
            }
            hazir = true
            indir.isEnabled = true
            indir.text = "İNDİR"
            motoruGuncelle(elle = false)
        }
    }

    private fun motoruGuncelle(elle: Boolean) {
        if (!hazir) return
        guncelle.isEnabled = false
        motorDurum.text = "İndirme motoru denetleniyor..."
        lifecycleScope.launch {
            val sonuc = withContext(Dispatchers.IO) {
                try {
                    val s = YoutubeDL.getInstance().updateYoutubeDL(applicationContext, YoutubeDL.UpdateChannel._STABLE)
                    if (s == YoutubeDL.UpdateStatus.DONE) "İndirme motoru güncellendi ✔" else "İndirme motoru güncel ✔"
                } catch (e: Exception) { "Güncelleme yapılamadı (internet?)" }
            }
            guncelle.isEnabled = !calisiyor
            motorDurum.text = sonuc
            if (elle) Toast.makeText(this@MainActivity, sonuc, Toast.LENGTH_SHORT).show()
        }
    }

    private fun baslat() {
        val url = link.text?.toString()?.trim().orEmpty()
        if (url.isEmpty()) {
            Toast.makeText(this, "Lütfen bir link girin", Toast.LENGTH_SHORT).show()
            return
        }
        // Güvenlik: sadece http/https link kabul et (komut gibi metinler geçemez)
        if (!Regex("^https?://[^\\s]+$", RegexOption.IGNORE_CASE).matches(url)) {
            Toast.makeText(this, "Geçerli bir link değil (https:// ile başlamalı)", Toast.LENGTH_LONG).show()
            return
        }
        val bicim = secilenBicim()
        val secilen = secilenKalite()

        val gecici = File(cacheDir, "indirme").apply { deleteRecursively(); mkdirs() }
        val istek = YoutubeDLRequest(url).apply {
            addOption("--ignore-config")   // dışarıdan ayar dosyası okunmasın
            addOption("--no-exec")         // indirme sonrası komut çalıştırılmasın
            addOption("--no-playlist")
            addOption("--no-mtime")
            addOption("-o", "${gecici.absolutePath}/%(title).150B.%(ext)s")
            when (bicim) {
                Bicim.MP3 -> {
                    addOption("-f", "bestaudio/best")
                    addOption("-x")
                    addOption("--audio-format", "mp3")
                    addOption("--audio-quality", secilen.substringBefore(" ") + "K")
                }
                Bicim.M4A -> {
                    addOption("-f", "bestaudio[ext=m4a]/bestaudio/best")
                    addOption("-x")
                    addOption("--audio-format", "m4a")
                }
                Bicim.MP4 -> {
                    val f = if (secilen == "En iyi" || secilen.isEmpty()) "bestvideo+bestaudio/best"
                    else {
                        val h = secilen.removeSuffix("p")
                        "bestvideo[height<=$h]+bestaudio/best[height<=$h]/best"
                    }
                    addOption("-f", f)
                    addOption("--merge-output-format", "mp4")
                }
            }
        }

        durumuAyarla(true)
        lifecycleScope.launch {
            // 1) Video bilgisi: başlık, kapak, süre
            baslik.text = "Video bilgisi alınıyor..."
            altBilgi.text = ""
            kapak.setImageDrawable(null)
            withContext(Dispatchers.IO) {
                try {
                    val bilgi = YoutubeDL.getInstance().getInfo(url)
                    val resim: Bitmap? = try {
                        bilgi.thumbnail?.takeIf { it.startsWith("https://") }?.let { URL(it).openStream().use { s -> BitmapFactory.decodeStream(s) } }
                    } catch (e: Exception) { null }
                    runOnUiThread {
                        baslik.text = bilgi.title ?: "Başlıksız"
                        val sure = bilgi.duration
                        val sureYazi = if (sure > 0) "%d:%02d".format(sure / 60, sure % 60) else ""
                        altBilgi.text = listOfNotNull(bilgi.uploader, sureYazi.ifEmpty { null }).joinToString("  •  ")
                        resim?.let { kapak.setImageBitmap(it) }
                    }
                } catch (e: Exception) {
                    runOnUiThread { baslik.text = url }
                }
            }

            // 2) İndirme
            val mesaj = withContext(Dispatchers.IO) {
                try {
                    YoutubeDL.getInstance().execute(istek, islemNo) { yuzde, kalan, _ ->
                        runOnUiThread {
                            if (yuzde >= 0) {
                                cubuk.isIndeterminate = false
                                cubuk.setProgressCompat(yuzde.toInt(), true)
                                val k = if (kalan > 0) "  •  ${kalan} sn kaldı" else ""
                                durum.text = "İndiriliyor %${yuzde.toInt()}$k"
                            }
                        }
                    }
                    runOnUiThread {
                        cubuk.isIndeterminate = true
                        durum.text = if (bicim == Bicim.MP4) "Birleştiriliyor..." else "Dönüştürülüyor..."
                    }
                    val dosyalar = gecici.listFiles()?.filter { it.isFile && !it.name.endsWith(".part") }.orEmpty()
                    if (dosyalar.isEmpty()) "Dosya bulunamadı"
                    else {
                        dosyalar.forEach { kaydet(it) }
                        "TAMAM"
                    }
                } catch (e: YoutubeDL.CanceledException) {
                    "İptal edildi"
                } catch (e: Exception) {
                    "Hata: " + (e.message?.lines()?.lastOrNull { it.isNotBlank() } ?: "bilinmeyen")
                } finally {
                    gecici.deleteRecursively()
                }
            }
            durumuAyarla(false)
            cubuk.isIndeterminate = false
            if (mesaj == "TAMAM") {
                cubuk.setProgressCompat(100, true)
                durum.text = "Tamamlandı ✔"
                ac.visibility = View.VISIBLE
                Snackbar.make(indir, "İndirilenler / VideoIndirici klasörüne kaydedildi", Snackbar.LENGTH_LONG)
                    .setAction("Aç") { dosyayiAc() }.show()
            } else {
                cubuk.setProgressCompat(0, false)
                durum.text = mesaj
            }
        }
    }

    /** Dosyayı telefonun İndirilenler/VideoIndirici klasörüne kopyala */
    private fun kaydet(f: File) {
        val uzanti = f.extension.lowercase()
        val tur = MimeTypeMap.getSingleton().getMimeTypeFromExtension(uzanti)
            ?: when (uzanti) { "mp3" -> "audio/mpeg"; "m4a" -> "audio/mp4"; else -> "video/mp4" }
        val bilgi = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, f.name)
            put(MediaStore.MediaColumns.MIME_TYPE, tur)
            put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/VideoIndirici")
            put(MediaStore.MediaColumns.IS_PENDING, 1)
        }
        val uri = contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, bilgi)
            ?: throw Exception("Kaydedilemedi")
        contentResolver.openOutputStream(uri)!!.use { cikis -> f.inputStream().use { it.copyTo(cikis) } }
        bilgi.clear()
        bilgi.put(MediaStore.MediaColumns.IS_PENDING, 0)
        contentResolver.update(uri, bilgi, null, null)
        sonDosya = uri
        sonTur = tur
    }

    private fun dosyayiAc() {
        val uri = sonDosya ?: return
        try {
            startActivity(Intent(Intent.ACTION_VIEW).setDataAndType(uri, sonTur)
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION))
        } catch (e: Exception) {
            Toast.makeText(this, "Açacak uygulama bulunamadı", Toast.LENGTH_SHORT).show()
        }
    }

    private fun durumuAyarla(evet: Boolean) {
        calisiyor = evet
        indir.isEnabled = !evet
        indir.text = if (evet) "İndiriliyor..." else "İNDİR"
        guncelle.isEnabled = !evet
        iptal.visibility = if (evet) View.VISIBLE else View.GONE
        if (evet) {
            onizleme.visibility = View.VISIBLE
            ac.visibility = View.GONE
            cubuk.isIndeterminate = true
            durum.text = "Başlıyor..."
            window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        } else {
            window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
    }
}

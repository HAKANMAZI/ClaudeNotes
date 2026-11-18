package com.hasan.videoindirici

import android.content.ClipboardManager
import android.content.ContentValues
import android.content.Intent
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.view.View
import android.view.WindowManager
import android.webkit.MimeTypeMap
import android.widget.*
import androidx.activity.ComponentActivity
import androidx.lifecycle.lifecycleScope
import com.yausername.ffmpeg.FFmpeg
import com.yausername.youtubedl_android.YoutubeDL
import com.yausername.youtubedl_android.YoutubeDLRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

class MainActivity : ComponentActivity() {

    private lateinit var link: EditText
    private lateinit var mp3: RadioButton
    private lateinit var kalite: Spinner
    private lateinit var kaliteBaslik: TextView
    private lateinit var indir: Button
    private lateinit var iptal: Button
    private lateinit var guncelle: Button
    private lateinit var cubuk: ProgressBar
    private lateinit var durum: TextView

    private var hazir = false
    private val islemNo = "indirme"
    private val kaliteler = listOf("En iyi", "1080p", "720p", "480p", "360p")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        link = findViewById(R.id.link)
        mp3 = findViewById(R.id.mp3)
        kalite = findViewById(R.id.kalite)
        kaliteBaslik = findViewById(R.id.kaliteBaslik)
        indir = findViewById(R.id.indir)
        iptal = findViewById(R.id.iptal)
        guncelle = findViewById(R.id.guncelle)
        cubuk = findViewById(R.id.cubuk)
        durum = findViewById(R.id.durum)

        kalite.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, kaliteler)

        findViewById<RadioGroup>(R.id.bicim).setOnCheckedChangeListener { _, _ ->
            val v = if (mp3.isChecked) View.GONE else View.VISIBLE
            kalite.visibility = v
            kaliteBaslik.visibility = v
        }
        findViewById<Button>(R.id.yapistir).setOnClickListener {
            val pano = getSystemService(ClipboardManager::class.java)
            pano.primaryClip?.getItemAt(0)?.coerceToText(this)?.let { link.setText(linkiAyikla(it.toString())) }
        }
        indir.setOnClickListener { baslat() }
        iptal.setOnClickListener {
            YoutubeDL.getInstance().destroyProcessById(islemNo)
            durum.text = "İptal edildi"
        }
        guncelle.setOnClickListener { motoruGuncelle(elle = true) }

        paylasilanLink(intent)
        kur()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        paylasilanLink(intent)
    }

    /** YouTube vb. uygulamadan "Paylaş" ile gelen linki kutuya koy */
    private fun paylasilanLink(i: Intent?) {
        if (i?.action == Intent.ACTION_SEND) {
            i.getStringExtra(Intent.EXTRA_TEXT)?.let { link.setText(linkiAyikla(it)) }
        }
    }

    private fun linkiAyikla(metin: String): String =
        Regex("https?://\\S+").find(metin)?.value ?: metin.trim()

    /** yt-dlp ve ffmpeg'i ilk açılışta hazırla */
    private fun kur() {
        indir.isEnabled = false
        lifecycleScope.launch {
            val hata = withContext(Dispatchers.IO) {
                try {
                    YoutubeDL.getInstance().init(applicationContext)
                    FFmpeg.getInstance().init(applicationContext)
                    null
                } catch (e: Exception) { e.message }
            }
            if (hata != null) {
                durum.text = "Kurulum hatası: $hata"
                return@launch
            }
            hazir = true
            indir.isEnabled = true
            durum.text = "Hazır"
            motoruGuncelle(elle = false)   // YouTube değişikliklerine karşı sessizce güncelle
        }
    }

    private fun motoruGuncelle(elle: Boolean) {
        if (!hazir) return
        if (elle) durum.text = "İndirme motoru güncelleniyor..."
        guncelle.isEnabled = false
        lifecycleScope.launch {
            val sonuc = withContext(Dispatchers.IO) {
                try {
                    val s = YoutubeDL.getInstance().updateYoutubeDL(applicationContext, YoutubeDL.UpdateChannel._STABLE)
                    if (s == YoutubeDL.UpdateStatus.DONE) "Motor güncellendi ✔" else "Motor zaten güncel ✔"
                } catch (e: Exception) { "Güncelleme yapılamadı" }
            }
            guncelle.isEnabled = true
            if (elle) durum.text = sonuc
        }
    }

    private fun baslat() {
        val url = link.text.toString().trim()
        if (url.isEmpty()) {
            Toast.makeText(this, "Lütfen bir link girin", Toast.LENGTH_SHORT).show()
            return
        }
        val sesMi = mp3.isChecked
        val secilen = kaliteler[kalite.selectedItemPosition]

        val gecici = File(cacheDir, "indirme").apply { deleteRecursively(); mkdirs() }
        val istek = YoutubeDLRequest(url).apply {
            addOption("--no-playlist")
            addOption("--no-mtime")
            addOption("-o", "${gecici.absolutePath}/%(title).150B.%(ext)s")
            if (sesMi) {
                addOption("-f", "bestaudio/best")
                addOption("-x")
                addOption("--audio-format", "mp3")
                addOption("--audio-quality", "192K")
            } else {
                val bicim = if (secilen == "En iyi") "bestvideo+bestaudio/best"
                else {
                    val h = secilen.removeSuffix("p")
                    "bestvideo[height<=$h]+bestaudio/best[height<=$h]/best"
                }
                addOption("-f", bicim)
                addOption("--merge-output-format", "mp4")
            }
        }

        calisiyor(true)
        lifecycleScope.launch {
            val mesaj = withContext(Dispatchers.IO) {
                try {
                    YoutubeDL.getInstance().execute(istek, islemNo) { yuzde, _, _ ->
                        runOnUiThread {
                            if (yuzde >= 0) {
                                cubuk.progress = yuzde.toInt()
                                durum.text = "İndiriliyor... %${yuzde.toInt()}"
                            }
                        }
                    }
                    runOnUiThread { durum.text = "Kaydediliyor..." }
                    val dosyalar = gecici.listFiles()?.filter { it.isFile && !it.name.endsWith(".part") }.orEmpty()
                    if (dosyalar.isEmpty()) "Dosya bulunamadı"
                    else {
                        dosyalar.forEach { kaydet(it) }
                        "Tamamlandı ✔  " + dosyalar.first().name
                    }
                } catch (e: YoutubeDL.CanceledException) {
                    "İptal edildi"
                } catch (e: Exception) {
                    "Hata: " + (e.message?.lines()?.lastOrNull { it.isNotBlank() } ?: "bilinmeyen")
                } finally {
                    gecici.deleteRecursively()
                }
            }
            calisiyor(false)
            if (mesaj.startsWith("Tamamlandı")) cubuk.progress = 100
            durum.text = mesaj
        }
    }

    /** Dosyayı telefonun İndirilenler/VideoIndirici klasörüne kopyala */
    private fun kaydet(f: File) {
        val uzanti = f.extension.lowercase()
        val tur = MimeTypeMap.getSingleton().getMimeTypeFromExtension(uzanti)
            ?: if (uzanti == "mp3") "audio/mpeg" else "video/mp4"
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
    }

    private fun calisiyor(evet: Boolean) {
        indir.isEnabled = !evet
        guncelle.isEnabled = !evet
        iptal.visibility = if (evet) View.VISIBLE else View.GONE
        if (evet) {
            cubuk.progress = 0
            durum.text = "Başlıyor..."
            window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        } else {
            window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
    }
}

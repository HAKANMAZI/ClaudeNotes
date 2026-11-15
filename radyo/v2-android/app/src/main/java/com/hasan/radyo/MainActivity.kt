package com.hasan.radyo

import android.Manifest
import android.app.DownloadManager
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.webkit.WebViewAssetLoader

/**
 * Uygulamanın ana ekranı.
 *
 * v2 web uygulaması (assets/www/index.html) bir WebView içinde açılır.
 * Sayfa, telefonun içinden "https://appassets.androidplatform.net" adresiyle
 * sunulur; böylece radyo, podcast ve liste sunucularına bağlanırken
 * tarayıcı engellerine takılmaz.
 *
 * Web sayfası ile telefon arasındaki köprü: JavaScript'te "Android" nesnesi.
 *  - Android.playing(...)  → çalmaya başlayınca/durunca arka plan hizmetini aç/kapat
 *  - Android.download(...) → podcast bölümünü telefona indir
 *  - Android.products() / buy(...) → gönüllü destek (Google Play)
 */
class MainActivity : ComponentActivity() {

    private lateinit var web: WebView
    private lateinit var destek: Destek

    private val bildirimIzni =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Uygulama ekranın tamamını kullanır; üst çubuk ve alt tuşlar için boşluk bırakılır
        WindowCompat.setDecorFitsSystemWindows(window, false)
        val kutu = FrameLayout(this).apply { setBackgroundColor(0xFF0F1115.toInt()) }
        web = WebView(this).apply { setBackgroundColor(0xFF0F1115.toInt()) }
        kutu.addView(web)
        setContentView(kutu)
        ViewCompat.setOnApplyWindowInsetsListener(kutu) { v, insets ->
            val b = insets.getInsets(
                WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout()
            )
            v.setPadding(b.left, b.top, b.right, b.bottom)
            WindowInsetsCompat.CONSUMED
        }

        // Sayfayı uygulamanın içinden sun
        val sunucu = WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this))
            .build()

        with(web.settings) {
            javaScriptEnabled = true
            domStorageEnabled = true                        // Favoriler, abonelikler, kaldığın yer
            mediaPlaybackRequiresUserGesture = false
            mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW // http:// radyo yayınları
        }

        web.webViewClient = object : WebViewClient() {
            override fun shouldInterceptRequest(
                view: WebView, request: WebResourceRequest
            ): WebResourceResponse? = sunucu.shouldInterceptRequest(request.url)

            // Uygulama dışı bağlantılar (yayın akışı, web siteleri) telefonun tarayıcısında açılır
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                if (request.url.host == "appassets.androidplatform.net") return false
                disaridaAc(request.url)
                return true
            }
        }

        web.addJavascriptInterface(Kopru(), "Android")
        web.loadUrl("https://appassets.androidplatform.net/assets/www/index.html")

        // Gönüllü destek (Google Play ödeme sistemi)
        destek = Destek(this) { js -> runOnUiThread { web.evaluateJavascript(js, null) } }
        destek.baglan()

        // Bildirimdeki "Durdur" düğmesi sayfadaki çaları durdurur
        PlaybackService.durdur = {
            runOnUiThread { web.evaluateJavascript("document.getElementById('audio').pause()", null) }
        }

        // Geri tuşu: önce sayfa içinde geri (ör. bölüm listesinden podcast listesine);
        // geri gidecek yer yoksa uygulama kapanmaz, arka plana alınır (yayın sürer)
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                web.evaluateJavascript("window.androidBack ? window.androidBack() : false") { r ->
                    if (r != "true") moveTaskToBack(true)
                }
            }
        })

        // Android 13+: "Çalıyor" bildirimi için izin iste
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            bildirimIzni.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    override fun onDestroy() {
        PlaybackService.durdur = null
        PlaybackService.durdurServis(this)
        destek.kapat()
        web.destroy()
        super.onDestroy()
    }

    private fun disaridaAc(uri: Uri) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, uri))
        } catch (_: Exception) {
            Toast.makeText(this, "Bağlantı açılamadı", Toast.LENGTH_SHORT).show()
        }
    }

    /** Podcast bölümünü telefonun "Podcasts/Radyo" klasörüne indirir (internetsiz dinlemek için). */
    private fun indir(url: String, baslik: String) {
        try {
            val ad = baslik.replace(Regex("[\\\\/:*?\"<>|]"), " ").trim().take(80).ifEmpty { "bolum" }
            val uzanti = (Uri.parse(url).lastPathSegment ?: "")
                .substringAfterLast('.', "mp3").lowercase()
                .takeIf { it in setOf("mp3", "m4a", "aac", "ogg", "opus", "wav") } ?: "mp3"
            val istek = DownloadManager.Request(Uri.parse(url))
                .setTitle(baslik)
                .setDescription("Radyo – podcast bölümü")
                .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                .setDestinationInExternalPublicDir(Environment.DIRECTORY_PODCASTS, "Radyo/$ad.$uzanti")
            (getSystemService(DOWNLOAD_SERVICE) as DownloadManager).enqueue(istek)
            Toast.makeText(this, "İndiriliyor. Podcasts/Radyo klasörüne kaydedilecek.", Toast.LENGTH_LONG).show()
        } catch (_: Exception) {
            disaridaAc(Uri.parse(url)) // İndirilemezse tarayıcıda aç
        }
    }

    /** Web sayfasının çağırabildiği komutlar (JavaScript'te "Android.xxx") */
    inner class Kopru {
        @JavascriptInterface
        fun playing(caliyor: Boolean, baslik: String) = runOnUiThread {
            if (caliyor) PlaybackService.baslat(this@MainActivity, baslik)
            else PlaybackService.durdurServis(this@MainActivity)
        }

        @JavascriptInterface
        fun download(url: String, baslik: String) = runOnUiThread { indir(url, baslik) }

        @JavascriptInterface
        fun products(): String = destek.urunlerJson()

        @JavascriptInterface
        fun buy(id: String) = runOnUiThread { destek.satinAl(id) }

        @JavascriptInterface
        fun refresh() = runOnUiThread { destek.baglan() }
    }
}

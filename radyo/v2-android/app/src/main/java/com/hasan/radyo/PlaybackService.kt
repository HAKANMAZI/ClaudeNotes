package com.hasan.radyo

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.wifi.WifiManager
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.support.v4.media.MediaMetadataCompat
import android.support.v4.media.session.MediaSessionCompat
import android.support.v4.media.session.PlaybackStateCompat
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import java.net.HttpURLConnection
import java.net.URL
import androidx.media.app.NotificationCompat as MedyaBildirim

/**
 * Arka planda çalma hizmeti ve kilit ekranı medya kartı.
 *
 *  - Ekran kapalıyken / başka uygulamaya geçince yayın kesilmez
 *  - Kilit ekranında ve bildirim alanında kapaklı medya kartı:
 *    önceki · çal/duraklat · sonraki · kapat (podcastte sarma çubuğu)
 *  - Kulaklık ve araba düğmeleri de çalışır (Android medya oturumu)
 *  - Duraklatınca kart kalır; on dakika dokunulmazsa kendiliğinden kapanır
 */
class PlaybackService : Service() {

    /** Sayfadan gelen çalma bilgisi */
    data class Bilgi(
        val caliyor: Boolean, val baslik: String, val alt: String,
        val kapak: String, val konum: Long, val sure: Long
    )

    companion object {
        private const val KANAL = "calma"
        private const val BEKLEME_MS = 10 * 60 * 1000L // Duraklatılınca kartın kalma süresi

        /** Karttaki düğmelere basılınca sayfaya gidecek komut (MainActivity ayarlar):
         *  "play", "pause", "next", "prev", "stop", "seek:<ms>" */
        var komut: ((String) -> Unit)? = null

        private var ornek: PlaybackService? = null
        private var bekleyen: Bilgi? = null

        /** Sayfa her çalma/duraklama/sarmada bunu çağırır */
        fun durum(c: Context, b: Bilgi) {
            ornek?.let { it.guncelle(b); return }
            if (!b.caliyor) return // Kart yokken duraklatma için kart açılmaz
            bekleyen = b
            try {
                ContextCompat.startForegroundService(c, Intent(c, PlaybackService::class.java))
            } catch (_: Exception) { }
        }

        /** Kartı tamamen kapat (ör. uyku zamanlayıcısı bitti) */
        fun kapat() { ornek?.kapatHepsi() }

        fun durdurServis(c: Context) {
            c.stopService(Intent(c, PlaybackService::class.java))
        }
    }

    private lateinit var oturum: MediaSessionCompat
    private var bilgi = Bilgi(false, "Kızılelma Radyo", "", "", 0, -1)
    private var kapakAdres = ""
    private var kapakResim: Bitmap? = null
    private val varsayilanKapak: Bitmap? by lazy {
        runCatching { BitmapFactory.decodeResource(resources, R.drawable.kapak_varsayilan) }.getOrNull()
    }
    private val ana = Handler(Looper.getMainLooper())
    private val otoKapat = Runnable { gonder("stop"); kapatHepsi() }
    private var uyanik: PowerManager.WakeLock? = null
    private var wifi: WifiManager.WifiLock? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        ornek = this
        kanalOlustur()
        oturum = MediaSessionCompat(this, "KizilelmaRadyo").apply {
            setCallback(object : MediaSessionCompat.Callback() {
                override fun onPlay() = gonder("play")
                override fun onPause() = gonder("pause")
                override fun onSkipToNext() = gonder("next")
                override fun onSkipToPrevious() = gonder("prev")
                override fun onSeekTo(pos: Long) = gonder("seek:$pos")
                override fun onStop() { gonder("stop"); kapatHepsi() }
                override fun onCustomAction(action: String?, extras: android.os.Bundle?) {
                    if (action == "kapat") { gonder("stop"); kapatHepsi() }
                }
            })
            setSessionActivity(acIntent())
            isActive = true
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            "prev" -> gonder("prev")
            "next" -> gonder("next")
            "toggle" -> gonder(if (bilgi.caliyor) "pause" else "play")
            "kapat" -> { gonder("stop"); kapatHepsi(); return START_NOT_STICKY }
        }
        bekleyen?.let { bilgi = it; bekleyen = null }
        goster()
        return START_NOT_STICKY
    }

    private fun gonder(k: String) { ana.post { komut?.invoke(k) } }

    fun guncelle(b: Bilgi) { bilgi = b; goster() }

    /** Medya oturumunu ve kartı güncelle */
    private fun goster() {
        val b = bilgi
        val resim = kapakResim ?: varsayilanKapak

        oturum.setMetadata(
            MediaMetadataCompat.Builder()
                .putString(MediaMetadataCompat.METADATA_KEY_TITLE, b.baslik)
                .putString(MediaMetadataCompat.METADATA_KEY_ARTIST, b.alt)
                .putLong(MediaMetadataCompat.METADATA_KEY_DURATION, b.sure)
                .apply { if (resim != null) putBitmap(MediaMetadataCompat.METADATA_KEY_ALBUM_ART, resim) }
                .build()
        )
        var eylem = PlaybackStateCompat.ACTION_PLAY or PlaybackStateCompat.ACTION_PAUSE or
            PlaybackStateCompat.ACTION_PLAY_PAUSE or PlaybackStateCompat.ACTION_SKIP_TO_NEXT or
            PlaybackStateCompat.ACTION_SKIP_TO_PREVIOUS or PlaybackStateCompat.ACTION_STOP
        if (b.sure > 0) eylem = eylem or PlaybackStateCompat.ACTION_SEEK_TO // Sadece podcastte sarma
        oturum.setPlaybackState(
            PlaybackStateCompat.Builder()
                .setActions(eylem)
                .addCustomAction("kapat", "Kapat", R.drawable.ic_kapat)
                .setState(
                    if (b.caliyor) PlaybackStateCompat.STATE_PLAYING else PlaybackStateCompat.STATE_PAUSED,
                    if (b.sure > 0) b.konum else PlaybackStateCompat.PLAYBACK_POSITION_UNKNOWN,
                    if (b.caliyor) 1f else 0f
                )
                .build()
        )

        val kart = NotificationCompat.Builder(this, KANAL)
            .setSmallIcon(R.drawable.ic_stat_radyo)
            .setContentTitle(b.baslik)
            .setContentText(b.alt)
            .setLargeIcon(resim)
            .setContentIntent(acIntent())
            .setDeleteIntent(eylemIntent("kapat", 4))
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC) // Kilit ekranında görünsün
            .setOnlyAlertOnce(true)
            .setSilent(true)
            .setOngoing(b.caliyor)
            .setCategory(NotificationCompat.CATEGORY_TRANSPORT)
            .addAction(R.drawable.ic_onceki, "Önceki", eylemIntent("prev", 1))
            .addAction(
                if (b.caliyor) R.drawable.ic_duraklat else R.drawable.ic_cal,
                if (b.caliyor) "Duraklat" else "Çal", eylemIntent("toggle", 2)
            )
            .addAction(R.drawable.ic_sonraki, "Sonraki", eylemIntent("next", 3))
            .addAction(R.drawable.ic_kapat, "Kapat", eylemIntent("kapat", 4))
            .setStyle(
                MedyaBildirim.MediaStyle()
                    .setMediaSession(oturum.sessionToken)
                    .setShowActionsInCompactView(0, 1, 2)
            )
            .build()

        if (Build.VERSION.SDK_INT >= 29) {
            startForeground(1, kart, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK)
        } else {
            startForeground(1, kart)
        }

        ana.removeCallbacks(otoKapat)
        if (b.caliyor) kilitle() else { birak(); ana.postDelayed(otoKapat, BEKLEME_MS) }
        kapakYukle(b.kapak)
    }

    /** Kapak resmini arka planda indir (en fazla 512 piksel) */
    private fun kapakYukle(adres: String) {
        if (adres == kapakAdres) return
        kapakAdres = adres
        kapakResim = null
        if (!adres.startsWith("https://") && !adres.startsWith("http://")) return
        Thread {
            val bmp = runCatching {
                val c = URL(adres).openConnection() as HttpURLConnection
                c.connectTimeout = 8000; c.readTimeout = 8000
                c.setRequestProperty("User-Agent", "KizilelmaRadyo (Android)")
                val r = c.inputStream.use { BitmapFactory.decodeStream(it) }
                c.disconnect()
                if (r != null && (r.width > 512 || r.height > 512)) {
                    val o = 512f / maxOf(r.width, r.height)
                    Bitmap.createScaledBitmap(r, (r.width * o).toInt(), (r.height * o).toInt(), true)
                } else r
            }.getOrNull()
            ana.post { if (kapakAdres == adres && bmp != null && ornek === this) { kapakResim = bmp; goster() } }
        }.start()
    }

    private fun acIntent(): PendingIntent = PendingIntent.getActivity(
        this, 0,
        Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
        PendingIntent.FLAG_IMMUTABLE
    )

    private fun eylemIntent(eylem: String, no: Int): PendingIntent = PendingIntent.getService(
        this, no, Intent(this, PlaybackService::class.java).setAction(eylem), PendingIntent.FLAG_IMMUTABLE
    )

    /** Telefon uyusa da işlemci ve Wi-Fi açık kalsın, yayın kesilmesin (sadece çalarken) */
    private fun kilitle() {
        if (uyanik == null) {
            uyanik = (getSystemService(POWER_SERVICE) as PowerManager)
                .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Radyo:calma")
                .apply { acquire(6 * 60 * 60 * 1000L) } // En fazla altı saat
        }
        if (wifi == null) {
            val mod = if (Build.VERSION.SDK_INT >= 29) WifiManager.WIFI_MODE_FULL_LOW_LATENCY
                      else @Suppress("DEPRECATION") WifiManager.WIFI_MODE_FULL_HIGH_PERF
            wifi = (applicationContext.getSystemService(WIFI_SERVICE) as WifiManager)
                .createWifiLock(mod, "Radyo:wifi")
                .apply { acquire() }
        }
    }

    private fun birak() {
        uyanik?.let { if (it.isHeld) it.release() }
        wifi?.let { if (it.isHeld) it.release() }
        uyanik = null
        wifi = null
    }

    fun kapatHepsi() {
        ana.removeCallbacks(otoKapat)
        birak()
        oturum.isActive = false
        ServiceCompat.stopForeground(this, ServiceCompat.STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun kanalOlustur() {
        val nm = getSystemService(NotificationManager::class.java)
        if (nm.getNotificationChannel(KANAL) == null) {
            nm.createNotificationChannel(
                NotificationChannel(KANAL, "Çalan yayın", NotificationManager.IMPORTANCE_LOW).apply {
                    lockscreenVisibility = android.app.Notification.VISIBILITY_PUBLIC
                }
            )
        }
    }

    override fun onDestroy() {
        ana.removeCallbacksAndMessages(null)
        birak()
        oturum.release()
        if (ornek === this) ornek = null
        super.onDestroy()
    }
}

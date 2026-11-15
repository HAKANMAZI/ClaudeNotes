package com.hasan.radyo

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.net.wifi.WifiManager
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat

/**
 * Arka planda çalma hizmeti.
 *
 * Radyo veya podcast çalarken açılır, durunca kapanır. Görevi:
 *  - Ekran kapalıyken / başka uygulamaya geçince yayının kesilmemesi
 *  - Bildirim alanında "Çalıyor" ve "Durdur" düğmesi göstermek
 */
class PlaybackService : Service() {

    companion object {
        private const val KANAL = "calma"
        private const val DURDUR = "durdur"

        /** Bildirimdeki "Durdur"a basılınca çalışacak komut (MainActivity ayarlar) */
        var durdur: (() -> Unit)? = null

        fun baslat(c: Context, baslik: String) {
            val i = Intent(c, PlaybackService::class.java).putExtra("baslik", baslik)
            try { ContextCompat.startForegroundService(c, i) } catch (_: Exception) { }
        }

        fun durdurServis(c: Context) {
            c.stopService(Intent(c, PlaybackService::class.java))
        }
    }

    private var uyanik: PowerManager.WakeLock? = null
    private var wifi: WifiManager.WifiLock? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == DURDUR) {
            durdur?.invoke()
            stopSelf()
            return START_NOT_STICKY
        }

        kanalOlustur()
        val baslik = intent?.getStringExtra("baslik")?.takeIf { it.isNotBlank() } ?: "Radyo"

        // Bildirime dokununca uygulama açılır
        val ac = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_IMMUTABLE
        )
        // "Durdur" düğmesi
        val dur = PendingIntent.getService(
            this, 1,
            Intent(this, PlaybackService::class.java).setAction(DURDUR),
            PendingIntent.FLAG_IMMUTABLE
        )

        val bildirim = NotificationCompat.Builder(this, KANAL)
            .setSmallIcon(R.drawable.ic_stat_radyo)
            .setContentTitle(baslik)
            .setContentText("Çalıyor")
            .setContentIntent(ac)
            .addAction(0, "Durdur", dur)
            .setOngoing(true)
            .setSilent(true)
            .setCategory(NotificationCompat.CATEGORY_TRANSPORT)
            .build()

        if (Build.VERSION.SDK_INT >= 29) {
            startForeground(1, bildirim, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK)
        } else {
            startForeground(1, bildirim)
        }
        kilitle()
        return START_NOT_STICKY
    }

    /** Telefon uyusa da işlemci ve Wi-Fi açık kalsın, yayın kesilmesin */
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

    private fun kanalOlustur() {
        val nm = getSystemService(NotificationManager::class.java)
        if (nm.getNotificationChannel(KANAL) == null) {
            nm.createNotificationChannel(
                NotificationChannel(KANAL, "Çalan yayın", NotificationManager.IMPORTANCE_LOW)
            )
        }
    }

    override fun onDestroy() {
        uyanik?.let { if (it.isHeld) it.release() }
        wifi?.let { if (it.isHeld) it.release() }
        uyanik = null
        wifi = null
        super.onDestroy()
    }
}

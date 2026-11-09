package com.hasan.ekrantemizle

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Environment
import androidx.work.Worker
import androidx.work.WorkerParameters

class TemizlikWorker(ctx: Context, params: WorkerParameters) : Worker(ctx, params) {

    override fun doWork(): Result {
        val ctx = applicationContext
        if (Ayarlar.otomatik(ctx) && Environment.isExternalStorageManager()) {
            val n = Temizleyici.temizle(ctx)
            if (n > 0) bildir(ctx, n)
        }
        return Result.success()
    }

    private fun bildir(ctx: Context, n: Int) {
        if (Build.VERSION.SDK_INT >= 33 &&
            ctx.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) return

        val nm = ctx.getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(
            NotificationChannel("temizlik", "Temizlik", NotificationManager.IMPORTANCE_DEFAULT)
        )
        val ac = PendingIntent.getActivity(
            ctx, 0, Intent(ctx, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE
        )
        val bildirim = Notification.Builder(ctx, "temizlik")
            .setSmallIcon(android.R.drawable.ic_menu_delete)
            .setContentTitle("Ekran Temizle")
            .setContentText("$n ekran görüntüsü çöpe atıldı. Görmek veya geri almak için dokun.")
            .setContentIntent(ac)
            .setAutoCancel(true)
            .build()
        nm.notify(1, bildirim)
    }
}

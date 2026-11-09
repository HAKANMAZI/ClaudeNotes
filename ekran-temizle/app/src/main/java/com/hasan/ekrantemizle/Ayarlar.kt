package com.hasan.ekrantemizle

import android.content.Context
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

object Ayarlar {
    private const val IS_ADI = "ekran_temizlik"

    private fun prefs(ctx: Context) =
        ctx.getSharedPreferences("ayarlar", Context.MODE_PRIVATE)

    fun otomatik(ctx: Context): Boolean = prefs(ctx).getBoolean("otomatik", true)

    fun otomatikAyarla(ctx: Context, acik: Boolean) {
        prefs(ctx).edit().putBoolean("otomatik", acik).apply()
        if (acik) zamanla(ctx)
        else WorkManager.getInstance(ctx).cancelUniqueWork(IS_ADI)
    }

    /** Altı saatte bir çalışır; telefon yeniden başlasa da devam eder */
    fun zamanla(ctx: Context) {
        val is_ = PeriodicWorkRequestBuilder<TemizlikWorker>(6, TimeUnit.HOURS).build()
        WorkManager.getInstance(ctx).enqueueUniquePeriodicWork(
            IS_ADI, ExistingPeriodicWorkPolicy.KEEP, is_
        )
    }
}

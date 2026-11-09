package com.hasan.ekrantemizle

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.provider.Settings
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

class MainActivity : Activity() {

    private lateinit var durum: TextView
    private lateinit var izinBtn: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        durum = TextView(this).apply { textSize = 18f; gravity = Gravity.CENTER }
        izinBtn = Button(this).apply {
            text = "İzin ver"
            setOnClickListener {
                startActivity(
                    Intent(
                        Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION,
                        Uri.parse("package:$packageName")
                    )
                )
            }
        }
        val simdiBtn = Button(this).apply {
            text = "Şimdi temizle"
            setOnClickListener { simdiTemizle() }
        }

        setContentView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(48, 48, 48, 48)
            addView(durum); addView(izinBtn); addView(simdiBtn)
        })
    }

    override fun onResume() {
        super.onResume()
        val izinVar = Environment.isExternalStorageManager()
        izinBtn.isEnabled = !izinVar
        durum.text = if (izinVar) {
            zamanla()
            "Açık ✅\nİki günden eski ekran görüntüleri\notomatik çöpe atılır."
        } else {
            "İzin gerekli.\n\"İzin ver\"e bas ve aç."
        }
    }

    /** Altı saatte bir arka planda çalışır; telefon yeniden başlasa da devam eder. */
    private fun zamanla() {
        val is_ = PeriodicWorkRequestBuilder<TemizlikWorker>(6, TimeUnit.HOURS).build()
        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "ekran_temizlik", ExistingPeriodicWorkPolicy.KEEP, is_
        )
    }

    private fun simdiTemizle() {
        if (!Environment.isExternalStorageManager()) {
            Toast.makeText(this, "Önce izin ver.", Toast.LENGTH_SHORT).show()
            return
        }
        Thread {
            val n = Temizleyici.temizle(this)
            runOnUiThread {
                Toast.makeText(this, "$n ekran görüntüsü çöpe atıldı.", Toast.LENGTH_SHORT).show()
            }
        }.start()
    }
}

package com.hasan.ekrantemizle

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.GridView
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.Executors

class MainActivity : Activity() {

    private enum class Mod { ADAY, COP }
    private var mod = Mod.ADAY

    private lateinit var durum: TextView
    private lateinit var izinBtn: Button
    private lateinit var otoSwitch: Switch
    private lateinit var adayBtn: Button
    private lateinit var copBtn: Button
    private lateinit var bilgi: TextView
    private lateinit var grid: GridView
    private lateinit var islem1: Button
    private lateinit var islem2: Button
    private lateinit var adapter: FotoAdapter

    private val arka = Executors.newSingleThreadExecutor()
    private val tarih = SimpleDateFormat("d MMMM yyyy, HH:mm", Locale("tr"))

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        adapter = FotoAdapter(this)

        durum = TextView(this).apply { textSize = 16f; gravity = Gravity.CENTER }
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
        otoSwitch = Switch(this).apply {
            text = "Otomatik temizlik (iki günden eskiler)"
            textSize = 16f
            isChecked = Ayarlar.otomatik(this@MainActivity)
            setOnCheckedChangeListener { _, acik ->
                Ayarlar.otomatikAyarla(this@MainActivity, acik)
                durumuGuncelle()
            }
        }

        adayBtn = Button(this).apply { setOnClickListener { mod = Mod.ADAY; yenile() } }
        copBtn = Button(this).apply { setOnClickListener { mod = Mod.COP; yenile() } }
        val sekmeler = LinearLayout(this).apply {
            addView(adayBtn, LinearLayout.LayoutParams(0, -2, 1f))
            addView(copBtn, LinearLayout.LayoutParams(0, -2, 1f))
        }

        bilgi = TextView(this).apply { textSize = 14f; setPadding(0, 12, 0, 12) }

        grid = GridView(this).apply {
            numColumns = 3
            this.adapter = this@MainActivity.adapter
            setOnItemClickListener { _, _, p, _ ->
                val id = this@MainActivity.adapter.fotolar[p].id
                val s = this@MainActivity.adapter.secili
                if (!s.add(id)) s.remove(id)
                this@MainActivity.adapter.notifyDataSetChanged()
                butonlariGuncelle()
            }
            setOnItemLongClickListener { _, _, p, _ ->
                buyukGoster(this@MainActivity.adapter.fotolar[p]); true
            }
        }

        islem1 = Button(this).apply { setOnClickListener { islem1Calistir() } }
        islem2 = Button(this).apply { setOnClickListener { islem2Calistir() } }
        val altSira = LinearLayout(this).apply {
            addView(islem1, LinearLayout.LayoutParams(0, -2, 1f))
            addView(islem2, LinearLayout.LayoutParams(0, -2, 1f))
        }

        setContentView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 24, 24, 24)
            addView(durum)
            addView(izinBtn)
            addView(otoSwitch)
            addView(sekmeler)
            addView(bilgi)
            addView(grid, LinearLayout.LayoutParams(-1, 0, 1f))
            addView(altSira)
        })

        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
        }
    }

    override fun onResume() {
        super.onResume()
        durumuGuncelle()
        if (izinVar() && Ayarlar.otomatik(this)) Ayarlar.zamanla(this)
        yenile()
    }

    private fun izinVar() = Environment.isExternalStorageManager()

    private fun durumuGuncelle() {
        izinBtn.visibility = if (izinVar()) View.GONE else View.VISIBLE
        durum.text = when {
            !izinVar() -> "İzin gerekli. \"İzin ver\"e bas ve aç."
            Ayarlar.otomatik(this) -> "Otomatik temizlik AÇIK ✅"
            else -> "Otomatik temizlik KAPALI ⏸"
        }
    }

    /** Listeleri arka planda yükler */
    private fun yenile() {
        if (!izinVar()) {
            adapter.fotolar = emptyList()
            adayBtn.text = "Silinecekler"
            copBtn.text = "Çöp kutusu"
            bilgi.text = ""
            butonlariGuncelle()
            return
        }
        arka.execute {
            val adaylar = Temizleyici.adaylar(this)
            val cop = Temizleyici.copteki(this)
            runOnUiThread {
                adayBtn.text = "Silinecekler (${adaylar.size})"
                copBtn.text = "Çöp kutusu (${cop.size})"
                adayBtn.isEnabled = mod != Mod.ADAY
                copBtn.isEnabled = mod != Mod.COP
                if (mod == Mod.ADAY) {
                    adapter.fotolar = adaylar
                    bilgi.text = "Sıradaki temizlikte çöpe gidecekler. " +
                            "Korumak istediklerine dokunup seç. Büyük görmek için uzun bas."
                } else {
                    adapter.fotolar = cop
                    bilgi.text = "Çöptekiler otuz gün sonra kalıcı silinir. " +
                            "Geri almak istediklerine dokunup seç. Büyük görmek için uzun bas."
                }
                butonlariGuncelle()
            }
        }
    }

    private fun butonlariGuncelle() {
        val n = adapter.secili.size
        val bos = adapter.fotolar.isEmpty()
        if (mod == Mod.ADAY) {
            islem1.text = "Seçilileri koru ($n)"
            islem2.text = "Hepsini şimdi çöpe at"
        } else {
            islem1.text = "Seçilileri geri al ($n)"
            islem2.text = "Hepsini geri al"
        }
        islem1.isEnabled = n > 0
        islem2.isEnabled = !bos
    }

    private fun islem1Calistir() {
        val secilen = adapter.seciliFotolar()
        arka.execute {
            val n = if (mod == Mod.ADAY) Temizleyici.koru(this, secilen)
                    else Temizleyici.geriAl(this, secilen)
            runOnUiThread {
                val mesaj = if (mod == Mod.ADAY) "$n foto korundu (favorilere eklendi)."
                            else "$n foto geri alındı."
                Toast.makeText(this, mesaj, Toast.LENGTH_SHORT).show()
                yenile()
            }
        }
    }

    private fun islem2Calistir() {
        val hepsi = adapter.fotolar
        val soru = if (mod == Mod.ADAY) "${hepsi.size} foto çöpe atılsın mı?"
                   else "${hepsi.size} foto geri alınsın mı?"
        AlertDialog.Builder(this)
            .setMessage(soru)
            .setPositiveButton("Evet") { _, _ ->
                arka.execute {
                    val n = if (mod == Mod.ADAY) Temizleyici.copeAt(this, hepsi)
                            else Temizleyici.geriAl(this, hepsi)
                    runOnUiThread {
                        val mesaj = if (mod == Mod.ADAY) "$n foto çöpe atıldı." else "$n foto geri alındı."
                        Toast.makeText(this, mesaj, Toast.LENGTH_SHORT).show()
                        yenile()
                    }
                }
            }
            .setNegativeButton("Vazgeç", null)
            .show()
    }

    private fun buyukGoster(foto: Foto) {
        arka.execute {
            val bm = try { Temizleyici.resim(this, foto, 1080) } catch (e: Exception) { null }
            runOnUiThread {
                val img = ImageView(this).apply {
                    adjustViewBounds = true
                    setImageBitmap(bm)
                }
                var baslik = "Çekilme: " + tarih.format(Date(foto.eklenme * 1000))
                if (foto.silinme > 0) {
                    val kalan = ((foto.silinme * 1000 - System.currentTimeMillis()) / 86_400_000L).coerceAtLeast(0)
                    baslik += "\nKalıcı silinmeye $kalan gün"
                }
                AlertDialog.Builder(this)
                    .setTitle(baslik)
                    .setView(img)
                    .setPositiveButton("Kapat", null)
                    .show()
            }
        }
    }
}

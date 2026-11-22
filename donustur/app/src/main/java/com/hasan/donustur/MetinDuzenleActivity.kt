package com.hasan.donustur

import android.app.AlertDialog
import android.graphics.Color
import android.graphics.Typeface
import android.text.Editable
import android.text.InputType
import android.text.TextWatcher
import android.view.Gravity
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import java.io.File

/** Düz metin düzenleyici: TXT, Markdown, JSON, CSV (metin olarak), HTML, XML, altyazı… */
class MetinDuzenleActivity : DuzenleyiciActivity() {

    private var ext = "txt"
    override val uzanti: String get() = ext
    private lateinit var alan: EditText
    private var yukleniyor = false
    private var boy = 15f

    override fun ekAraclar(cubuk: LinearLayout) {
        cubuk.ekle(buton("🔍 Bul/Değiştir", 0xFF37474F.toInt()) { bulDegistir() })
        cubuk.ekle(buton("A± Boyut", 0xFF37474F.toInt()) { boy = if (boy >= 21f) 13f else boy + 2f; alan.textSize = boy })
    }

    override fun yukle() {
        uri?.let { ext = Dosya.girdi(this, it).uzanti.ifEmpty { "txt" } }
        baslikYaz()
        alan = EditText(this).apply {
            gravity = Gravity.TOP or Gravity.START
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE or InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
            setHorizontallyScrolling(false)
            textSize = 15f
            if (ext in setOf("json", "xml", "html", "htm", "csv", "yaml", "yml", "ini", "log")) typeface = Typeface.MONOSPACE
            setTextColor(Color.rgb(20, 20, 20)); setBackgroundColor(Color.WHITE)
            setPadding(dp(12), dp(10), dp(12), dp(10))
            hint = "Yazmaya başlayın…"
            addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
                override fun onTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
                override fun afterTextChanged(s: Editable?) { if (!yukleniyor && !degisti) degisti = true }
            })
        }
        kok.addView(ScrollView(this).apply { isFillViewport = true; addView(alan) }, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(kok)
        val u = uri
        if (u == null) { degisti = true; return }
        isle("Açılıyor…") {
            val m = Dosya.metinOku(this, Dosya.girdi(this, u))
            runOnUiThread { yukleniyor = true; alan.setText(m); yukleniyor = false }
        }
    }

    private fun bulDegistir() {
        val bul = EditText(this).apply { hint = "Bul" }
        val yeni = EditText(this).apply { hint = "Yerine (boş = sil)" }
        val kap = dikey(this).apply { setPadding(dp(16), 0, dp(16), 0); ekle(bul); ekle(yeni) }
        AlertDialog.Builder(this).setTitle("Bul ve değiştir").setView(kap)
            .setPositiveButton("Tümünü değiştir") { _, _ ->
                val a = bul.text.toString()
                if (a.isEmpty()) return@setPositiveButton
                val m = alan.text.toString()
                val n = m.split(a).size - 1
                if (n > 0) alan.setText(m.replace(a, yeni.text.toString()))
                mesaj("$n yer değiştirildi")
            }.setNegativeButton("Vazgeç", null).show()
    }

    @Volatile private var anlik = ""
    override fun onceKaydet() { anlik = alan.text.toString() }
    override fun dosyayaYaz(f: File) = f.writeText(anlik)

    override fun duzMetin(): String = alan.text.toString()
}

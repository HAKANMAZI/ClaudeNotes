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

/** Word (.docx) düzenleyici: paragrafları doğrudan yazarak düzenle; stil, resim ve tablolar korunur. */
class WordActivity : DuzenleyiciActivity() {

    override val uzanti = "docx"
    private var belge: WordBelge? = null
    private lateinit var liste: LinearLayout
    private lateinit var kaydirma: ScrollView
    private var odak = 0
    private var yukleniyor = false

    override fun ekAraclar(cubuk: LinearLayout) {
        cubuk.ekle(buton("➕ Paragraf", 0xFF37474F.toInt()) { paragrafEkle() })
        cubuk.ekle(buton("🗑 Sil", 0xFF37474F.toInt()) { paragrafSil() })
        cubuk.ekle(buton("B Kalın", 0xFF37474F.toInt()) { kalin() })
        cubuk.ekle(buton("🔍 Bul/Değiştir", 0xFF37474F.toInt()) { bulDegistir() })
    }

    override fun yukle() {
        liste = dikey(this).apply { setPadding(dp(14), dp(10), dp(14), dp(80)); setBackgroundColor(Color.WHITE) }
        kaydirma = ScrollView(this).apply { addView(liste) }
        kok.addView(kaydirma, LinearLayout.LayoutParams(-1, 0, 1f))
        kok.ekle(yazi("Paragrafa dokunup yazın. Enter yeni paragraf açar. Biçim, resim ve tablolar korunur.", 11f).apply { setTextColor(Color.GRAY) }, kenar = 2)
        setContentView(kok)
        val yeni = intent.getStringExtra("yeni") != null
        isle("Açılıyor…") {
            val b = WordBelge(if (yeni) WordBelge.yeni() else Paket.oku(this, uri!!))
            runOnUiThread { belge = b; ciz(); if (yeni) degisti = true }
        }
    }

    private fun ciz(odakla: Int = -1) {
        val b = belge ?: return
        yukleniyor = true
        liste.removeAllViews()
        b.paragraflar.forEachIndexed { i, p ->
            val e = EditText(this).apply {
                setText(p.metin)
                textSize = if (p.baslik) 20f else 16f
                setTypeface(Typeface.SERIF, if (p.kalin || p.baslik) Typeface.BOLD else Typeface.NORMAL)
                setTextColor(Color.rgb(20, 20, 20))
                background = null
                gravity = Gravity.TOP or Gravity.START
                inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE or InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
                setPadding(dp(4), dp(3), dp(4), dp(3))
                hint = if (b.paragraflar.size == 1) "Yazmaya başlayın…" else null
                if (p.tabloda) setBackgroundColor(Color.rgb(238, 242, 250))
                setOnFocusChangeListener { _, var1 -> if (var1) odak = liste.indexOfChild(this) }
                addTextChangedListener(object : TextWatcher {
                    override fun beforeTextChanged(s: CharSequence?, a: Int, c: Int, d: Int) {}
                    override fun onTextChanged(s: CharSequence?, a: Int, c: Int, d: Int) {}
                    override fun afterTextChanged(s: Editable?) {
                        if (yukleniyor) return
                        val k = liste.indexOfChild(this@apply)
                        if (k in b.paragraflar.indices) { b.paragraflar[k].metin = s.toString(); if (!degisti) degisti = true }
                    }
                })
            }
            liste.addView(e, LinearLayout.LayoutParams(-1, -2))
        }
        yukleniyor = false
        if (odakla in 0 until liste.childCount) {
            val v = liste.getChildAt(odakla) as EditText
            v.requestFocus(); v.setSelection(v.text.length)
            odak = odakla
            kaydirma.post { kaydirma.smoothScrollTo(0, v.top - dp(80)) }
        }
    }

    private fun paragrafEkle() {
        val b = belge ?: return
        val i = b.ekle(odak.coerceIn(-1, b.paragraflar.size - 1))
        degisti = true
        ciz(i)
    }

    private fun paragrafSil() {
        val b = belge ?: return
        if (odak !in b.paragraflar.indices) return
        val tabloda = b.paragraflar[odak].tabloda
        b.sil(odak)
        degisti = true
        ciz((if (tabloda) odak else odak - 1).coerceAtLeast(0))
        if (tabloda) mesaj("Tablo hücresi silinemez; içi boşaltıldı")
    }

    private fun kalin() {
        val b = belge ?: return
        if (odak !in b.paragraflar.indices) return
        val p = b.paragraflar[odak]
        p.kalin = !p.kalin
        degisti = true
        (liste.getChildAt(odak) as? EditText)?.setTypeface(Typeface.SERIF, if (p.kalin || p.baslik) Typeface.BOLD else Typeface.NORMAL)
    }

    private fun bulDegistir() {
        val b = belge ?: return
        val bul = EditText(this).apply { hint = "Bul" }
        val yeni = EditText(this).apply { hint = "Yerine (boş = sil)" }
        val kap = dikey(this).apply { setPadding(dp(16), 0, dp(16), 0); ekle(bul); ekle(yeni) }
        AlertDialog.Builder(this).setTitle("Bul ve değiştir").setView(kap)
            .setPositiveButton("Tümünü değiştir") { _, _ ->
                val a = bul.text.toString()
                if (a.isEmpty()) return@setPositiveButton
                var adet = 0
                for (p in b.paragraflar) {
                    val n = p.metin.split(a).size - 1
                    if (n > 0) { adet += n; p.metin = p.metin.replace(a, yeni.text.toString()) }
                }
                if (adet > 0) { degisti = true; ciz() }
                mesaj("$adet yer değiştirildi")
            }.setNegativeButton("Vazgeç", null).show()
    }

    override fun dosyayaYaz(f: File) { belge!!.kaydet(f); runOnUiThread { ciz(odak) } }

    override fun duzMetin(): String = belge?.duzMetin() ?: ""
}

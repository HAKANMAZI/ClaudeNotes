package com.hasan.donustur

import android.app.AlertDialog
import android.graphics.Color
import android.graphics.Typeface
import android.text.TextUtils
import android.view.Gravity
import android.widget.EditText
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TableLayout
import android.widget.TableRow
import android.widget.TextView
import java.io.File

/** Excel (.xlsx) ve CSV düzenleyici: hücreye dokun, değer ya da =FORMÜL yaz. Biçimler korunur. */
class TabloActivity : DuzenleyiciActivity() {

    private var csvMi = false
    override val uzanti: String get() = if (csvMi) "csv" else "xlsx"

    private var excel: ExcelBelge? = null
    private var sayfa: Sayfa? = null
    private var hucre = HashMap<Pair<Int, Int>, String>()
    private var csvAyirici = ','
    private var satirSay = 30
    private var sutunSay = 8

    private lateinit var tablo: TableLayout
    private lateinit var sekmeler: LinearLayout
    private lateinit var formulCubugu: TextView

    override fun ekAraclar(cubuk: LinearLayout) {
        cubuk.ekle(buton("➕ Satır", 0xFF37474F.toInt()) { satirSay += 50; ciz() })
        cubuk.ekle(buton("➕ Sütun", 0xFF37474F.toInt()) { sutunSay += 2; ciz() })
        cubuk.ekle(buton("Σ Topla", 0xFF37474F.toInt()) { toplaBilgi() })
    }

    override fun yukle() {
        val g = uri?.let { Dosya.girdi(this, it) }
        csvMi = g?.uzanti == "csv"
        baslikYaz()
        sekmeler = yatay(this)
        kok.ekle(HorizontalScrollView(this).apply { addView(sekmeler) }, kenar = 0)
        formulCubugu = yazi("Hücreye dokunup yazın. Formül = ile başlar, İngilizce yazılır: =SUM(A1:A5), =AVERAGE(B2:B9)", 12f).apply {
            setTextColor(Color.DKGRAY); setPadding(dp(8), dp(2), dp(8), dp(2))
        }
        kok.ekle(formulCubugu, kenar = 0)
        tablo = TableLayout(this).apply { setBackgroundColor(Color.rgb(200, 205, 215)) }
        val dikeyK = ScrollView(this).apply { addView(HorizontalScrollView(this@TabloActivity).apply { addView(tablo) }) }
        kok.addView(dikeyK, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(kok)

        val yeni = intent.getStringExtra("yeni") != null
        isle("Açılıyor…") {
            if (csvMi) {
                val metin = Dosya.metinOku(this, g!!)
                val ilk = metin.lineSequence().firstOrNull() ?: ""
                csvAyirici = if (ilk.count { it == ';' } > ilk.count { it == ',' }) ';' else ','
                val m = HashMap<Pair<Int, Int>, String>()
                Metin.csvOku(metin).forEachIndexed { r, satir -> satir.forEachIndexed { c, v -> if (v.isNotEmpty()) m[r to c] = v } }
                runOnUiThread { hucre = m; boyutAyarla(); ciz() }
            } else {
                val e = ExcelBelge(if (yeni) ExcelBelge.yeni() else Paket.oku(this, uri!!))
                val s = e.sayfalar.first()
                val m = e.hucreler(s)
                runOnUiThread { excel = e; sayfa = s; hucre = m; sekmeCiz(); boyutAyarla(); ciz(); if (yeni) degisti = true }
            }
        }
    }

    private fun boyutAyarla() {
        satirSay = maxOf(30, (hucre.keys.maxOfOrNull { it.first } ?: 0) + 6).coerceAtMost(maxOf(300, satirSay))
        sutunSay = maxOf(8, (hucre.keys.maxOfOrNull { it.second } ?: 0) + 3).coerceAtMost(40)
    }

    private fun sekmeCiz() {
        sekmeler.removeAllViews()
        val e = excel ?: return
        if (e.sayfalar.size < 2) return
        for (s in e.sayfalar) {
            sekmeler.ekle(buton(s.ad, if (s === sayfa) MAVI else Color.GRAY) {
                isle("Açılıyor…") {
                    val m = e.hucreler(s)
                    runOnUiThread { sayfa = s; hucre = m; sekmeCiz(); boyutAyarla(); ciz() }
                }
            })
        }
    }

    private fun kutu(s: String, baslik: Boolean, genislik: Int): TextView = TextView(this).apply {
        text = s; textSize = 14f; maxLines = 1; ellipsize = TextUtils.TruncateAt.END
        setPadding(dp(6), dp(6), dp(6), dp(6))
        setBackgroundColor(if (baslik) Color.rgb(230, 234, 242) else Color.WHITE)
        setTextColor(if (baslik) Color.DKGRAY else Color.rgb(20, 20, 20))
        if (baslik) { gravity = Gravity.CENTER; setTypeface(typeface, Typeface.BOLD) }
        layoutParams = TableRow.LayoutParams(genislik, -2).apply { setMargins(1, 1, 0, 0) }
    }

    private fun ciz() {
        tablo.removeAllViews()
        val gen = dp(96)
        val ust = TableRow(this)
        ust.addView(kutu("", true, dp(44)))
        for (c in 0 until sutunSay) ust.addView(kutu(ExcelBelge.sutunHarf(c), true, gen))
        tablo.addView(ust)
        for (r in 0 until satirSay) {
            val satir = TableRow(this)
            satir.addView(kutu("${r + 1}", true, dp(44)))
            for (c in 0 until sutunSay) {
                val v = hucre[r to c] ?: ""
                satir.addView(kutu(v, false, gen).apply {
                    if (v.toDoubleOrNull() != null) gravity = Gravity.END
                    setOnClickListener { hucreDuzenle(r, c, this) }
                })
            }
            tablo.addView(satir)
        }
    }

    private fun hucreDuzenle(r: Int, c: Int, gorunum: TextView) {
        val ref = ExcelBelge.sutunHarf(c) + (r + 1)
        val mevcut = excel?.let { e -> sayfa?.let { e.formulVeyaDeger(it, r, c) } } ?: (hucre[r to c] ?: "")
        formulCubugu.text = "$ref: $mevcut"
        val e = EditText(this).apply { setText(mevcut); setSelection(text.length); setSingleLine(false); maxLines = 6 }
        val kap = dikey(this).apply { setPadding(dp(16), 0, dp(16), 0); ekle(e) }
        val d = AlertDialog.Builder(this).setTitle(ref).setView(kap)
            .setPositiveButton("Tamam") { _, _ -> yaz(r, c, e.text.toString(), gorunum) }
            .setNeutralButton("Sil") { _, _ -> yaz(r, c, "", gorunum) }
            .setNegativeButton("Vazgeç", null).create()
        d.window?.setSoftInputMode(android.view.WindowManager.LayoutParams.SOFT_INPUT_STATE_VISIBLE)
        d.show()
        e.requestFocus()
    }

    private fun yaz(r: Int, c: Int, deger: String, gorunum: TextView) {
        val eski = hucre[r to c] ?: ""
        if (deger == eski && excel == null) return
        if (deger.isEmpty()) hucre.remove(r to c) else hucre[r to c] = deger
        excel?.let { e -> sayfa?.let { e.degistir(it, r, c, deger) } }
        gorunum.text = deger
        gorunum.gravity = if (deger.toDoubleOrNull() != null) Gravity.END else Gravity.START
        degisti = true
        formulCubugu.text = ExcelBelge.sutunHarf(c) + (r + 1) + ": " + deger
    }

    /** Sayısal hücrelerin toplamı / ortalaması (her sütun). */
    private fun toplaBilgi() {
        val sb = StringBuilder()
        for (c in 0 until sutunSay) {
            val sayilar = hucre.filterKeys { it.second == c }.values.mapNotNull { it.replace(',', '.').toDoubleOrNull() }
            if (sayilar.isNotEmpty())
                sb.append("${ExcelBelge.sutunHarf(c)}: toplam ${ExcelBelge.sayiGoster(sayilar.sum().toString())}, ortalama ${ExcelBelge.sayiGoster(sayilar.average().toString())} (${sayilar.size} sayı)\n")
        }
        AlertDialog.Builder(this).setTitle("Sütun toplamları").setMessage(sb.ifEmpty { "Sayı yok" }).setPositiveButton("Tamam", null).show()
    }

    private fun satirlar(): List<List<String>> {
        val enR = hucre.keys.maxOfOrNull { it.first } ?: -1
        val enC = hucre.keys.maxOfOrNull { it.second } ?: -1
        return (0..enR).map { r -> (0..enC).map { c -> hucre[r to c] ?: "" } }
    }

    override fun dosyayaYaz(f: File) {
        val e = excel
        if (e != null) e.kaydet(f)
        else f.writeText(satirlar().joinToString("\n") { s ->
            s.joinToString(csvAyirici.toString()) { v -> if (v.any { it == csvAyirici || it == '"' || it == '\n' }) "\"" + v.replace("\"", "\"\"") + "\"" else v }
        } + "\n")
    }

    override fun duzMetin(): String = Metin.tabloMetin(satirlar())
}

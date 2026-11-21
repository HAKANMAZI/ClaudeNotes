package com.hasan.donustur

import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast

const val MAVI = 0xFF1E5BD8.toInt()

fun Context.dp(v: Int): Int = (v * resources.displayMetrics.density).toInt()

fun Context.buton(yazi: String, renk: Int = MAVI, tikla: () -> Unit): Button = Button(this).apply {
    text = yazi
    isAllCaps = false
    setTextColor(Color.WHITE)
    textSize = 14f
    background = GradientDrawable().apply { cornerRadius = dp(10).toFloat(); setColor(renk) }
    setPadding(dp(10), dp(6), dp(10), dp(6))
    setOnClickListener { tikla() }
}

fun Context.yazi(s: String, boy: Float = 15f, kalin: Boolean = false): TextView = TextView(this).apply {
    text = s; textSize = boy
    setTextColor(Color.rgb(30, 30, 30))
    if (kalin) setTypeface(typeface, android.graphics.Typeface.BOLD)
}

fun dikey(ctx: Context) = LinearLayout(ctx).apply { orientation = LinearLayout.VERTICAL }
fun yatay(ctx: Context) = LinearLayout(ctx).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }

fun LinearLayout.ekle(v: View, agirlik: Float = 0f, kenar: Int = 4): View {
    val lp = if (orientation == LinearLayout.HORIZONTAL)
        LinearLayout.LayoutParams(if (agirlik > 0) 0 else LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT, agirlik)
    else LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
    val k = context.dp(kenar)
    lp.setMargins(k, k, k, k)
    addView(v, lp)
    return v
}

/** Butonları satır başına n tane olacak şekilde dizer. */
fun Context.izgara(butonlar: List<View>, sutun: Int = 3): LinearLayout {
    val kap = dikey(this)
    butonlar.chunked(sutun).forEach { grup ->
        val s = yatay(this)
        grup.forEach { s.ekle(it, 1f, 3) }
        repeat(sutun - grup.size) { s.ekle(View(this), 1f, 3) }
        kap.ekle(s, kenar = 0)
    }
    return kap
}

fun Activity.mesaj(s: String) = Toast.makeText(this, s, Toast.LENGTH_LONG).show()

fun Activity.sor(baslik: String, ipucu: String, varsayilan: String = "", sifre: Boolean = false, tamam: (String) -> Unit) {
    val e = EditText(this).apply {
        hint = ipucu; setText(varsayilan)
        if (sifre) inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
    }
    val kap = dikey(this).apply { setPadding(dp(16), dp(8), dp(16), 0); ekle(e) }
    AlertDialog.Builder(this).setTitle(baslik).setView(kap)
        .setPositiveButton("Tamam") { _, _ -> tamam(e.text.toString()) }
        .setNegativeButton("Vazgeç", null).show()
}

fun Activity.disaridaAc(uri: Uri, mime: String) {
    val i = Intent(Intent.ACTION_VIEW).setDataAndType(uri, mime).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    try { startActivity(Intent.createChooser(i, "Şununla aç")) } catch (e: Exception) { mesaj("Açacak uygulama yok") }
}

fun Activity.paylas(uriler: List<Uri>, mime: String = "*/*") {
    val i = if (uriler.size == 1) Intent(Intent.ACTION_SEND).putExtra(Intent.EXTRA_STREAM, uriler[0])
    else Intent(Intent.ACTION_SEND_MULTIPLE).putParcelableArrayListExtra(Intent.EXTRA_STREAM, ArrayList(uriler))
    i.type = mime
    i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    startActivity(Intent.createChooser(i, "Paylaş"))
}

package com.hasan.ekrantemizle

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Color
import android.os.Handler
import android.os.Looper
import android.util.LruCache
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.AbsListView
import android.widget.BaseAdapter
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.TextView
import java.util.concurrent.Executors

/** Küçük resim ızgarası; dokununca seçilir */
class FotoAdapter(private val ctx: Context) : BaseAdapter() {

    var fotolar: List<Foto> = emptyList()
        set(v) { field = v; secili.clear(); notifyDataSetChanged() }

    val secili = mutableSetOf<Long>()

    fun seciliFotolar() = fotolar.filter { it.id in secili }

    private val onbellek = LruCache<Long, Bitmap>(150)
    private val havuz = Executors.newFixedThreadPool(3)
    private val ana = Handler(Looper.getMainLooper())
    private val hucre = ctx.resources.displayMetrics.widthPixels / 3

    override fun getCount() = fotolar.size
    override fun getItem(p: Int) = fotolar[p]
    override fun getItemId(p: Int) = fotolar[p].id

    override fun getView(p: Int, eski: View?, parent: ViewGroup): View {
        val kutu = (eski as? FrameLayout) ?: yeniHucre()
        val img = kutu.getChildAt(0) as ImageView
        val isaret = kutu.getChildAt(1) as TextView
        val foto = fotolar[p]

        val sec = foto.id in secili
        img.alpha = if (sec) 0.45f else 1f
        isaret.visibility = if (sec) View.VISIBLE else View.GONE

        img.tag = foto.id
        val hazir = onbellek.get(foto.id)
        if (hazir != null) {
            img.setImageBitmap(hazir)
        } else {
            img.setImageDrawable(null)
            havuz.execute {
                val bm = try { Temizleyici.resim(ctx, foto, 300) } catch (e: Exception) { null }
                if (bm != null) onbellek.put(foto.id, bm)
                ana.post { if (img.tag == foto.id) img.setImageBitmap(bm) }
            }
        }
        return kutu
    }

    private fun yeniHucre(): FrameLayout {
        val kutu = FrameLayout(ctx).apply {
            layoutParams = AbsListView.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, hucre)
            setPadding(3, 3, 3, 3)
        }
        val img = ImageView(ctx).apply {
            scaleType = ImageView.ScaleType.CENTER_CROP
            setBackgroundColor(Color.LTGRAY)
        }
        val isaret = TextView(ctx).apply {
            text = "✓"
            textSize = 28f
            setTextColor(Color.WHITE)
            setBackgroundColor(Color.argb(200, 0, 120, 215))
            gravity = Gravity.CENTER
        }
        kutu.addView(img, FrameLayout.LayoutParams(-1, -1))
        kutu.addView(isaret, FrameLayout.LayoutParams(90, 90, Gravity.TOP or Gravity.END))
        return kutu
    }
}

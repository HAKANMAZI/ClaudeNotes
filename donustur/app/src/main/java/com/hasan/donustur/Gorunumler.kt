package com.hasan.donustur

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.view.MotionEvent
import android.view.View

/** Sayfa önizlemesi: parmakla dokun (nokta) ya da sürükle (kutu). Sonuç sayfaya oranla 0..1. */
class KutuSecView(ctx: Context, private val sayfa: Bitmap, private val ipucu: String) : View(ctx) {
    private val hedef = RectF()
    private var x0 = -1f; private var y0 = -1f; private var x1 = -1f; private var y1 = -1f
    private val kalem = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.RED; style = Paint.Style.STROKE; strokeWidth = 5f }
    private val dolgu = Paint().apply { color = Color.argb(60, 255, 0, 0) }
    private val yazi = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.DKGRAY; textSize = 34f }

    /** (x, y, w, h) oranları; seçim yoksa null. */
    val secim: FloatArray?
        get() {
            if (x0 < 0 || hedef.width() <= 0) return null
            val l = minOf(x0, x1); val t = minOf(y0, y1)
            val r = maxOf(x0, x1); val b = maxOf(y0, y1)
            fun ox(v: Float) = ((v - hedef.left) / hedef.width()).coerceIn(0f, 1f)
            fun oy(v: Float) = ((v - hedef.top) / hedef.height()).coerceIn(0f, 1f)
            return floatArrayOf(ox(l), oy(t), ox(r) - ox(l), oy(b) - oy(t))
        }

    override fun onMeasure(w: Int, h: Int) {
        val gen = MeasureSpec.getSize(w)
        val enFazla = (resources.displayMetrics.heightPixels * 0.6f).toInt()
        setMeasuredDimension(gen, minOf((gen * sayfa.height / sayfa.width.toFloat()).toInt() + 50, enFazla))
    }

    override fun onDraw(c: Canvas) {
        val o = minOf(width.toFloat() / sayfa.width, (height - 50f) / sayfa.height)
        val w = sayfa.width * o; val h = sayfa.height * o
        hedef.set((width - w) / 2, 50f, (width + w) / 2, 50f + h)
        c.drawText(ipucu, 10f, 36f, yazi)
        c.drawBitmap(sayfa, null, hedef, null)
        c.drawRect(hedef, Paint().apply { style = Paint.Style.STROKE; color = Color.GRAY })
        if (x0 >= 0) {
            val r = RectF(minOf(x0, x1), minOf(y0, y1), maxOf(x0, x1), maxOf(y0, y1))
            if (r.width() < 8 && r.height() < 8) { c.drawCircle(x0, y0, 12f, kalem) } else { c.drawRect(r, dolgu); c.drawRect(r, kalem) }
        }
    }

    @SuppressLint("ClickableViewAccessibility")
    override fun onTouchEvent(e: MotionEvent): Boolean {
        parent?.requestDisallowInterceptTouchEvent(true)
        when (e.action) {
            MotionEvent.ACTION_DOWN -> { x0 = e.x; y0 = e.y; x1 = e.x; y1 = e.y }
            MotionEvent.ACTION_MOVE, MotionEvent.ACTION_UP -> { x1 = e.x; y1 = e.y }
        }
        invalidate()
        return true
    }
}

/** Parmakla imza atma alanı; saydam zeminli bitmap verir. */
class ImzaView(ctx: Context) : View(ctx) {
    private val yol = Path()
    private val kalem = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(10, 30, 120); style = Paint.Style.STROKE; strokeWidth = 7f
        strokeCap = Paint.Cap.ROUND; strokeJoin = Paint.Join.ROUND
    }
    var bos = true; private set

    override fun onMeasure(w: Int, h: Int) {
        val gen = MeasureSpec.getSize(w)
        setMeasuredDimension(gen, gen / 2)
    }

    override fun onDraw(c: Canvas) {
        c.drawColor(Color.rgb(250, 250, 240))
        c.drawLine(20f, height * 0.8f, width - 20f, height * 0.8f, Paint().apply { color = Color.LTGRAY })
        c.drawPath(yol, kalem)
    }

    @SuppressLint("ClickableViewAccessibility")
    override fun onTouchEvent(e: MotionEvent): Boolean {
        parent?.requestDisallowInterceptTouchEvent(true)
        when (e.action) {
            MotionEvent.ACTION_DOWN -> yol.moveTo(e.x, e.y)
            MotionEvent.ACTION_MOVE -> { for (i in 0 until e.historySize) yol.lineTo(e.getHistoricalX(i), e.getHistoricalY(i)); yol.lineTo(e.x, e.y); bos = false }
        }
        invalidate()
        return true
    }

    fun temizle() { yol.reset(); bos = true; invalidate() }

    fun bitmap(): Bitmap {
        val b = RectF(); yol.computeBounds(b, true)
        b.inset(-10f, -10f)
        val l = b.left.coerceAtLeast(0f); val t = b.top.coerceAtLeast(0f)
        val w = (b.right.coerceAtMost(width.toFloat()) - l).toInt().coerceAtLeast(1)
        val h = (b.bottom.coerceAtMost(height.toFloat()) - t).toInt().coerceAtLeast(1)
        val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        val c = Canvas(bmp); c.translate(-l, -t); c.drawPath(yol, kalem)
        return bmp
    }
}

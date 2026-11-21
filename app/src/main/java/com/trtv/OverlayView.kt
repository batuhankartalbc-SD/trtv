package com.trtv

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.view.View
import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.max
import kotlin.math.min

/** Çeviri kutularını çizer. Koordinatlar oyun görüntüsüne göre 0–1 (HDMI tam ekran = 16:9). */
class OverlayView(ctx: Context) : View(ctx) {

    data class Item(val b: FloatArray, val lh: Float, val speaker: String, val tr: String, val kind: String)

    companion object {
        fun parseItems(a: JSONArray?): List<Item> {
            if (a == null) return emptyList()
            val out = ArrayList<Item>(a.length())
            for (i in 0 until a.length()) {
                val o = a.getJSONObject(i)
                val b = o.getJSONArray("b")
                out.add(Item(
                    floatArrayOf(b.getDouble(0).toFloat(), b.getDouble(1).toFloat(), b.getDouble(2).toFloat(), b.getDouble(3).toFloat()),
                    o.optDouble("lh", 0.03).toFloat(), o.optString("s", ""), o.optString("tr", ""), o.optString("k", "text")))
            }
            return out
        }
    }

    private val zones = LinkedHashMap<String, List<Item>>()
    private var boxColor = Color.argb(250, 16, 16, 16)
    private var textColor = Color.WHITE
    private var speakerColor = Color.rgb(255, 213, 74)
    private var fontScale = 1f
    private var shown = true
    private var bannerText: String? = null
    private val typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
    private val fill = Paint(Paint.ANTI_ALIAS_FLAG).apply { typeface = this@OverlayView.typeface }
    private val stroke = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        typeface = this@OverlayView.typeface; style = Paint.Style.STROKE; color = Color.argb(230, 0, 0, 0)
        strokeJoin = Paint.Join.ROUND
    }
    private val bg = Paint(Paint.ANTI_ALIAS_FLAG)

    init { setWillNotDraw(false); setLayerType(LAYER_TYPE_HARDWARE, null) }

    fun setItems(zone: String, items: List<Item>) {
        if (items.isEmpty()) zones.remove(zone) else zones[zone] = items
        invalidate()
    }

    fun clearAll() { zones.clear(); invalidate() }

    fun setShown(v: Boolean) { shown = v; invalidate() }

    fun setStyle(o: JSONObject) {
        fun col(k: String, d: Int) = try { Color.parseColor(o.optString(k)) } catch (_: Exception) { d }
        val base = col("box", Color.rgb(16, 16, 16))
        val a = o.optInt("opacity", 250).coerceIn(0, 255)
        boxColor = Color.argb(a, Color.red(base), Color.green(base), Color.blue(base))
        textColor = col("text", Color.WHITE)
        speakerColor = col("speaker", Color.rgb(255, 213, 74))
        fontScale = o.optDouble("scale", 1.0).toFloat()
        invalidate()
    }

    fun banner(text: String) {
        bannerText = text
        invalidate()
        postDelayed({ bannerText = null; invalidate() }, 3500)
    }

    private fun wrap(text: String, p: Paint, width: Float): List<String> {
        val out = ArrayList<String>()
        var cur = ""
        for (w in text.split(' ').filter { it.isNotEmpty() }) {
            val t = if (cur.isEmpty()) w else "$cur $w"
            if (p.measureText(t) <= width || cur.isEmpty()) cur = t else { out.add(cur); cur = w }
        }
        if (cur.isNotEmpty()) out.add(cur)
        return if (out.isEmpty()) listOf("") else out
    }

    override fun onDraw(c: Canvas) {
        val W = width.toFloat(); val H = height.toFloat()
        bannerText?.let { drawBanner(c, it, W, H) }
        if (!shown) return
        for (items in zones.values) for (it in items) drawItem(c, it, W, H)
    }

    private fun drawBanner(c: Canvas, t: String, W: Float, H: Float) {
        fill.textSize = H * 0.028f
        val tw = fill.measureText(t)
        val r = RectF(W * 0.5f - tw / 2 - 30, H * 0.04f, W * 0.5f + tw / 2 + 30, H * 0.04f + fill.textSize * 2f)
        bg.color = Color.argb(230, 15, 40, 33)
        c.drawRoundRect(r, 18f, 18f, bg)
        fill.color = Color.rgb(61, 220, 151)
        c.drawText(t, r.left + 30, r.centerY() + fill.textSize * 0.35f, fill)
    }

    private fun drawItem(c: Canvas, it: Item, W: Float, H: Float) {
        if (it.tr.isEmpty()) return
        var x0 = it.b[0] * W; var y0 = it.b[1] * H; var x1 = it.b[2] * W; var y1 = it.b[3] * H
        val pad = max(6f, it.lh * H * 0.3f)
        val cover = RectF(x0 - pad, y0 - pad, x1 + pad, y1 + pad)
        val isSub = it.kind == "subtitle" || it.kind == "objective"
        if (isSub) {
            val lo = W * 0.06f; val hi = W * 0.94f
            val aw = max(cover.width(), min(hi - lo, cover.width() * 1.35f))
            val left = max(lo, min(cover.centerX() - aw / 2, hi - aw))
            cover.left = left; cover.right = left + aw
        } else {
            cover.right = min(W, cover.left + cover.width() * 1.25f)
        }
        val text = if (it.speaker.isNotEmpty()) "${it.speaker}: ${it.tr}" else it.tr
        var size = max(16f, it.lh * H * 0.92f * fontScale)
        val innerW = cover.width() - 2 * pad
        var lines: List<String>
        var lineH: Float
        while (true) {
            fill.textSize = size
            lines = wrap(text, fill, innerW)
            lineH = fill.fontSpacing
            if (lines.size * lineH <= (cover.height() - 2 * pad) * 1.15f || size <= 16f) break
            size -= 1f
        }
        val need = lines.size * lineH + 2 * pad
        if (need > cover.height()) {
            if (it.kind == "subtitle") cover.top = cover.bottom - need else cover.bottom = cover.top + need
        }
        bg.color = boxColor
        c.drawRoundRect(cover, 8f, 8f, bg)
        stroke.textSize = size
        stroke.strokeWidth = max(2f, size / 12f)
        val fm = fill.fontMetrics
        var y = cover.top + (cover.height() - lines.size * lineH) / 2 - fm.ascent
        val prefix = if (it.speaker.isNotEmpty()) "${it.speaker}:" else ""
        for ((i, line) in lines.withIndex()) {
            val lw = fill.measureText(line)
            val x = cover.left + (cover.width() - lw) / 2
            if (i == 0 && prefix.isNotEmpty() && line.startsWith(prefix)) {
                drawText(c, prefix, x, y, speakerColor)
                drawText(c, line.substring(prefix.length), x + fill.measureText(prefix), y, textColor)
            } else {
                drawText(c, line, x, y, textColor)
            }
            y += lineH
        }
    }

    private fun drawText(c: Canvas, t: String, x: Float, y: Float, color: Int) {
        c.drawText(t, x, y, stroke)
        fill.color = color
        c.drawText(t, x, y, fill)
    }
}

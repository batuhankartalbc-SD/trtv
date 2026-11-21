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

/**
 * Çeviri kutularını çizer. Koordinatlar oyun görüntüsüne göre 0–1 (HDMI tam ekran = 16:9).
 * "match" (oyun stili): Türkçe, İngilizcenin tam yerine, oyunun yazı rengi ve konturuyla çizilir;
 * İngilizceyi örten zemin oyundan ölçülen renkte ve yumuşak kenarlıdır.
 */
class OverlayView(ctx: Context) : View(ctx) {

    data class Item(
        val b: FloatArray, val lh: Float, val speaker: String, val tr: String, val kind: String,
        val lines: Int, val fg: Int?, val bg: Int?, val sc: Int?, val align: String
    )

    companion object {
        private fun color(o: JSONObject, k: String): Int? {
            val s = o.optString(k, "")
            if (s.isEmpty()) return null
            return try { Color.parseColor(s) } catch (_: Exception) { null }
        }

        fun parseItems(a: JSONArray?): List<Item> {
            if (a == null) return emptyList()
            val out = ArrayList<Item>(a.length())
            for (i in 0 until a.length()) {
                val o = a.getJSONObject(i)
                val b = o.getJSONArray("b")
                out.add(Item(
                    floatArrayOf(b.getDouble(0).toFloat(), b.getDouble(1).toFloat(), b.getDouble(2).toFloat(), b.getDouble(3).toFloat()),
                    o.optDouble("lh", 0.03).toFloat(), o.optString("s", ""), o.optString("tr", ""), o.optString("k", "text"),
                    o.optInt("n", 1), color(o, "fg"), color(o, "bg"), color(o, "sc"), o.optString("a", "c")))
            }
            return out
        }
    }

    private val zones = LinkedHashMap<String, List<Item>>()
    private var boxColor = Color.rgb(16, 16, 16)
    private var boxAlpha = 250
    private var textColor = Color.WHITE
    private var speakerColor = Color.rgb(255, 213, 74)
    private var fontScale = 1.1f
    private var mode = "match"
    private var matchColors = true
    private var dx = 0f; private var dy = 0f; private var sx = 1f; private var sy = 1f
    private var shown = true
    private var calib = false
    private var bannerText: String? = null
    private val typeface = Typeface.create("sans-serif-medium", Typeface.BOLD)
    private val fill = Paint(Paint.ANTI_ALIAS_FLAG).apply { typeface = this@OverlayView.typeface }
    private val stroke = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        typeface = this@OverlayView.typeface; style = Paint.Style.STROKE; color = Color.argb(220, 0, 0, 0)
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
        boxColor = col("box", Color.rgb(16, 16, 16))
        mode = o.optString("mode", "match")
        boxAlpha = when (mode) { "semi" -> 160; "text" -> 0; else -> o.optInt("opacity", 250).coerceIn(0, 255) }
        textColor = col("text", Color.WHITE)
        speakerColor = col("speaker", Color.rgb(255, 213, 74))
        fontScale = o.optDouble("scale", 1.1).toFloat()
        matchColors = o.optBoolean("match", true)
        dx = o.optDouble("dx", 0.0).toFloat(); dy = o.optDouble("dy", 0.0).toFloat()
        sx = o.optDouble("sx", 1.0).toFloat(); sy = o.optDouble("sy", 1.0).toFloat()
        calib = o.optBoolean("calib", false)
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

    // kalibrasyon: oyun koordinatı (0–1) → ekran pikseli
    private fun mx(v: Float, W: Float) = ((v - 0.5f) * sx + 0.5f + dx) * W
    private fun my(v: Float, H: Float) = ((v - 0.5f) * sy + 0.5f + dy) * H

    override fun onDraw(c: Canvas) {
        val W = width.toFloat(); val H = height.toFloat()
        bannerText?.let { drawBanner(c, it, W, H) }
        if (calib) { drawCalib(c, W, H); return }
        if (!shown) return
        for (items in zones.values) for (it in items) {
            if (mode == "match") drawMatch(c, it, W, H) else drawBox(c, it, W, H)
        }
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

    /** Hizalama modu: algılanan İngilizce yazıların çevresine çerçeve; Türkçe çizilmez, İngilizce görünür. */
    private fun drawCalib(c: Canvas, W: Float, H: Float) {
        val line = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; strokeWidth = 4f; color = Color.rgb(0, 229, 255) }
        val thin = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; strokeWidth = 2f; color = Color.argb(160, 61, 220, 151) }
        c.drawLine(W / 2, 0f, W / 2, H, thin); c.drawLine(0f, H / 2, W, H / 2, thin)
        c.drawRect(mx(0f, W), my(0f, H), mx(1f, W), my(1f, H), thin)   // oyun görüntüsünün sınırı (kalibre)
        for (items in zones.values) for (it in items) {
            c.drawRect(mx(it.b[0], W) - 3, my(it.b[1], H) - 3, mx(it.b[2], W) + 3, my(it.b[3], H) + 3, line)
        }
        val t = String.format("HİZALAMA  kaydırma X %.1f%%  Y %.1f%%   ölçek %.1f%% × %.1f%%   (Ctrl+Alt+oklar / PgUp-PgDn / Home-End)",
            dx * 100, dy * 100, sx * 100, sy * 100)
        fill.textSize = H * 0.022f
        val tw = fill.measureText(t)
        val r = RectF(W / 2 - tw / 2 - 24, H * 0.12f, W / 2 + tw / 2 + 24, H * 0.12f + fill.textSize * 1.9f)
        bg.color = Color.argb(225, 10, 20, 30); c.drawRoundRect(r, 14f, 14f, bg)
        fill.color = Color.rgb(0, 229, 255); c.drawText(t, r.left + 24, r.centerY() + fill.textSize * 0.35f, fill)
    }

    private fun drawMatch(c: Canvas, it: Item, W: Float, H: Float) {
        if (it.tr.isEmpty()) return
        val x0 = mx(it.b[0], W); val y0 = my(it.b[1], H); val x1 = mx(it.b[2], W); val y1 = my(it.b[3], H)
        val lh = max(8f, it.lh * H * sy)
        var size = max(12f, lh * 0.70f * fontScale)
        val text = if (it.speaker.isNotEmpty()) "${it.speaker}: ${it.tr}" else it.tr
        val isSub = it.kind == "subtitle" || it.kind == "objective"
        val maxW = when {
            isSub -> W * 0.86f
            it.align == "l" -> max(x1 - x0, min(W - x0 - 8, (x1 - x0) * 1.9f))
            else -> max(x1 - x0, (x1 - x0) * 1.7f)
        }
        var lines: List<String>
        var n = 0
        while (true) {
            fill.textSize = size
            lines = wrap(text, fill, maxW)
            if (lines.size <= max(1, it.lines) + (if (it.kind == "subtitle") 1 else 0) || size <= lh * 0.7f || n++ > 12) break
            size *= 0.94f
        }
        val lineH = fill.fontSpacing
        val lw = lines.maxOf { fill.measureText(it) }
        val th = lines.size * lineH
        var tx0 = if (it.align == "l") x0 else (x0 + x1) / 2 - lw / 2
        tx0 = max(4f, min(tx0, W - lw - 4))
        val ty0 = when {
            it.kind == "subtitle" -> min(y1 - th, (y0 + y1) / 2 - th / 2)
            lines.size <= it.lines -> (y0 + y1) / 2 - th / 2
            else -> y0
        }
        val pad = max(3f, lh * 0.22f)
        val cover = RectF(min(x0, tx0) - pad, min(y0, ty0) - pad, max(x1, tx0 + lw) + pad, max(y1, ty0 + th) + pad)
        val base = if (matchColors && it.bg != null) it.bg else boxColor
        for ((grow, alpha) in listOf(pad * 1.6f to 50, pad * 0.9f to 120, 0f to 255)) {
            bg.color = Color.argb(alpha, Color.red(base), Color.green(base), Color.blue(base))
            val r = RectF(cover.left - grow, cover.top - grow, cover.right + grow, cover.bottom + grow)
            c.drawRoundRect(r, pad + grow, pad + grow, bg)
        }
        val fg = if (matchColors && it.fg != null) it.fg else textColor
        val spk = if (matchColors && it.sc != null) it.sc else speakerColor
        stroke.textSize = size
        stroke.strokeWidth = max(2f, size / 11f)
        val fm = fill.fontMetrics
        var y = ty0 - fm.ascent
        val prefix = if (it.speaker.isNotEmpty()) "${it.speaker}:" else ""
        for ((i, line) in lines.withIndex()) {
            val w = fill.measureText(line)
            val x = if (it.align == "l") tx0 else tx0 + (lw - w) / 2
            if (i == 0 && prefix.isNotEmpty() && line.startsWith(prefix)) {
                drawText(c, prefix, x, y, spk)
                drawText(c, line.substring(prefix.length), x + fill.measureText(prefix), y, fg)
            } else {
                drawText(c, line, x, y, fg)
            }
            y += lineH
        }
    }

    private fun drawBox(c: Canvas, it: Item, W: Float, H: Float) {
        if (it.tr.isEmpty()) return
        val x0 = mx(it.b[0], W); val y0 = my(it.b[1], H); val x1 = mx(it.b[2], W); val y1 = my(it.b[3], H)
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
        bg.color = Color.argb(boxAlpha, Color.red(boxColor), Color.green(boxColor), Color.blue(boxColor))
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

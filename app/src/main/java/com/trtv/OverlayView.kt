package com.trtv

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.os.SystemClock
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
typealias ViewItem = OverlayItem

class OverlayView(ctx: Context) : View(ctx) {

    companion object {
        private fun color(o: JSONObject, k: String): Int? {
            val s = o.optString(k, "")
            if (s.isEmpty()) return null
            return try { Color.parseColor(s) } catch (_: Exception) { null }
        }

        fun parseItems(a: JSONArray?): List<ViewItem> = parseItemsJson(a?.toString())
    }

    private data class AnimatedItem(
        var item: ViewItem,
        val id: String,
        val startedAt: Long,
        var removedAt: Long? = null
    )
    private data class MatchLayout(
        val lines: List<String>, val widths: List<Float>, val size: Float, val lineHeight: Float,
        val lineWidth: Float, val totalHeight: Float, val textX: Float, val textY: Float,
        val pad: Float, val cover: RectF, val prefixWidth: Float
    )
    private data class BoxLayout(
        val cover: RectF, val lines: List<String>, val widths: List<Float>, val size: Float,
        val lineHeight: Float, val pad: Float, val prefixWidth: Float
    )
    private val zones = LinkedHashMap<String, MutableList<AnimatedItem>>()
    private val layoutCache = HashMap<String, MatchLayout>()
    private val boxLayoutCache = HashMap<String, BoxLayout>()
    private var animationScheduled = false
    private val animationTick = object : Runnable {
        override fun run() {
            animationScheduled = false
            val now = SystemClock.uptimeMillis()
            zones.values.forEach { entries -> entries.removeAll { it.removedAt?.let { t -> now - t >= 120L } == true } }
            if (zones.values.flatten().any { it.removedAt != null || now - it.startedAt < 120L }) {
                animationScheduled = true
                postDelayed(this, 16L)
            } else invalidate()
        }
    }
    private var boxColor = Color.BLACK
    private var boxAlpha = 255
    private var backgroundAlpha = 255
    private var textColor = Color.WHITE
    private var speakerColor = Color.rgb(255, 213, 74)
    private var fontScale = 1.0f
    private var mode = "match"
    private var matchColors = true
    private var dx = 0f; private var dy = 0f; private var sx = 1f; private var sy = 1f
    private var shown = true
    private var calib = false
    private var bgMode = "black"
    private var bannerText: String? = null
    private var bannerGeneration = 0
    private var connectionWarning = false
    private var uiSuppressed = false
    private val typeface = Typeface.create("sans-serif-medium", Typeface.BOLD)
    private val fill = Paint(Paint.ANTI_ALIAS_FLAG).apply { typeface = this@OverlayView.typeface }
    private val stroke = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        typeface = this@OverlayView.typeface; style = Paint.Style.STROKE; color = Color.argb(220, 0, 0, 0)
        strokeJoin = Paint.Join.ROUND
    }
    private val bg = Paint(Paint.ANTI_ALIAS_FLAG)

    init { setWillNotDraw(false); setLayerType(LAYER_TYPE_HARDWARE, null) }

    fun setItems(zone: String, items: List<ViewItem>) {
        val now = SystemClock.uptimeMillis()
        val entries = zones.getOrPut(zone) { ArrayList() }
        val current = entries.filter { it.removedAt == null }.associateBy { it.id }
        val incomingIds = HashSet<String>()
        var geometryChanged = false
        for (item in items) {
            val id = itemIdentity(item)
            incomingIds.add(id)
            val old = current[id]
            if (old != null) {
                if (old.item != item) geometryChanged = true
                old.item = item // Aynı kutudaki iyileştirilmiş metin anında değişir.
            } else { entries.add(AnimatedItem(item, id, now)); geometryChanged = true }
        }
        current.filterKeys { it !in incomingIds }.values.forEach { it.removedAt = now; geometryChanged = true }
        if (geometryChanged && layoutCache.size > 300) { layoutCache.clear(); boxLayoutCache.clear() }
        animateUntilSettled()
    }

    fun clearAll() {
        val now = SystemClock.uptimeMillis()
        zones.values.flatten().filter { it.removedAt == null }.forEach { it.removedAt = now }
        animateUntilSettled()
    }

    private fun itemIdentity(item: ViewItem) = "${item.kind}|${item.speaker}|${item.b.joinToString(",") { "%.4f".format(java.util.Locale.US, it) }}"

    private fun animateUntilSettled() {
        postInvalidateOnAnimation()
        if (!animationScheduled) {
            animationScheduled = true
            postDelayed(animationTick, 16L)
        }
    }

    fun setShown(v: Boolean) { shown = v; invalidate() }
    fun setConnectionWarning(v: Boolean) { connectionWarning = v; invalidate() }
    fun setUiSuppressed(v: Boolean) { uiSuppressed = v; invalidate() }
    fun setOverlayOpacity(alpha: Int) {
        backgroundAlpha = alpha.coerceIn(0, 255)
        if (mode != "text") boxAlpha = backgroundAlpha
        invalidate()
    }

    fun setStyle(o: JSONObject) {
        fun col(k: String, d: Int) = try { Color.parseColor(o.optString(k)) } catch (_: Exception) { d }
        boxColor = col("box", Color.BLACK)
        mode = o.optString("mode", "match")
        backgroundAlpha = if (o.has("opacity")) o.optInt("opacity", 255).coerceIn(0, 255) else if (mode == "semi") 160 else backgroundAlpha
        boxAlpha = if (mode == "text") 0 else backgroundAlpha
        textColor = col("text", Color.WHITE)
        speakerColor = col("speaker", Color.rgb(255, 213, 74))
        fontScale = o.optDouble("scale", 1.1).toFloat()
        matchColors = o.optBoolean("match", true)
        dx = o.optDouble("dx", 0.0).toFloat(); dy = o.optDouble("dy", 0.0).toFloat()
        sx = o.optDouble("sx", 1.0).toFloat(); sy = o.optDouble("sy", 1.0).toFloat()
        calib = o.optBoolean("calib", false)
        bgMode = o.optString("bgm", "black")
        layoutCache.clear()
        boxLayoutCache.clear()
        invalidate()
    }

    fun banner(text: String, durationMs: Long = 3500L) {
        val generation = ++bannerGeneration
        bannerText = text
        invalidate()
        postDelayed({ if (generation == bannerGeneration) { bannerText = null; invalidate() } }, durationMs)
    }

    // kalibrasyon: oyun koordinatı (0–1) → ekran pikseli
    private fun mx(v: Float, W: Float) = mapX(v, sx, dx, W)
    private fun my(v: Float, H: Float) = mapY(v, sy, dy, H)

    override fun onDraw(c: Canvas) {
        if (uiSuppressed) return
        val W = width.toFloat(); val H = height.toFloat()
        bannerText?.let { drawBanner(c, it, W, H) }
        if (connectionWarning) drawConnectionWarning(c, W, H)
        if (calib) { drawCalib(c, W, H); return }
        if (!shown) return
        val now = SystemClock.uptimeMillis()
        for (items in zones.values) for (animated in items) {
            val alpha = animated.removedAt?.let { (255f * (1f - (now - it) / 120f)).toInt() }
                ?: (255f * ((now - animated.startedAt) / 120f).coerceIn(0f, 1f)).toInt()
            if (alpha <= 0) continue
            val layer = c.saveLayerAlpha(null, alpha.coerceIn(0, 255))
            if (mode == "match") drawMatch(c, animated.item, W, H) else drawBox(c, animated.item, W, H)
            c.restoreToCount(layer)
        }
    }

    private fun drawConnectionWarning(c: Canvas, W: Float, H: Float) {
        fill.textSize = H * 0.02f
        val label = "Brolis: bilgisayar bağlı değil"
        val dot = H * 0.008f
        val pad = H * 0.012f
        val width = fill.measureText(label) + dot * 2 + pad * 3
        val height = fill.textSize * 1.8f
        val r = RectF(W - width - H * 0.025f, H * 0.035f, W - H * 0.025f, H * 0.035f + height)
        bg.color = Color.argb(175, 20, 20, 20)
        c.drawRoundRect(r, height / 2, height / 2, bg)
        bg.color = Color.rgb(244, 65, 65)
        c.drawCircle(r.left + pad + dot, r.centerY(), dot, bg)
        fill.color = Color.argb(220, 255, 255, 255)
        c.drawText(label, r.left + pad * 2 + dot * 2, r.centerY() + fill.textSize * 0.34f, fill)
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
            c.drawRect(mx(it.item.b[0], W) - 3, my(it.item.b[1], H) - 3, mx(it.item.b[2], W) + 3, my(it.item.b[3], H) + 3, line)
        }
        val t = String.format("HİZALAMA  kaydırma X %.1f%%  Y %.1f%%   ölçek %.1f%% × %.1f%%   (Ctrl+Alt+oklar / PgUp-PgDn / Home-End)",
            dx * 100, dy * 100, sx * 100, sy * 100)
        fill.textSize = H * 0.022f
        val tw = fill.measureText(t)
        val r = RectF(W / 2 - tw / 2 - 24, H * 0.12f, W / 2 + tw / 2 + 24, H * 0.12f + fill.textSize * 1.9f)
        bg.color = Color.argb(225, 10, 20, 30); c.drawRoundRect(r, 14f, 14f, bg)
        fill.color = Color.rgb(0, 229, 255); c.drawText(t, r.left + 24, r.centerY() + fill.textSize * 0.35f, fill)
    }

    /** Birebir stil: İngilizceyle aynı boyut (her yazı kendi boyutunda), aynı yer; zemin varsayılan simsiyah. */
    private fun drawMatch(c: Canvas, it: ViewItem, W: Float, H: Float) {
        if (it.tr.isEmpty()) return
        val layout = matchLayout(it, W, H)
        val lines = layout.lines
        val size = layout.size
        fill.textSize = size
        val lineH = layout.lineHeight
        val cover = layout.cover
        val pad = layout.pad
        if (bgMode == "game" && it.bg != null) {
            val b = it.bg
            for ((grow, alpha) in listOf(pad * 1.6f to 50, pad * 0.9f to 120, 0f to 255)) {
                bg.color = Color.argb(alpha * backgroundAlpha / 255, Color.red(b), Color.green(b), Color.blue(b))
                c.drawRoundRect(RectF(cover.left - grow, cover.top - grow, cover.right + grow, cover.bottom + grow), pad + grow, pad + grow, bg)
            }
        } else if (bgMode != "none") {
            bg.color = Color.argb(backgroundAlpha, 0, 0, 0)
            c.drawRoundRect(cover, pad * 0.8f, pad * 0.8f, bg)
        }
        var fg = if (matchColors && it.fg != null) it.fg else textColor
        var spk = it.sc ?: speakerColor   // PC konuşmacı rengini (ya da oyundan ölçüleni) gönderir
        if (bgMode != "game" && bgMode != "none") {     // koyu zeminde koyu yazı okunmaz → beyaz
            if (lum(fg) < 110) fg = textColor
            if (lum(spk) < 110) spk = speakerColor
        }
        stroke.textSize = size
        stroke.strokeWidth = max(1.5f, size / 14f)
        val fm = fill.fontMetrics
        var y = layout.textY - fm.ascent
        val prefix = if (it.speaker.isNotEmpty()) "${it.speaker}:" else ""
        for ((i, line) in lines.withIndex()) {
            val w = layout.widths[i]
            val x = if (it.align == "l") layout.textX else layout.textX + (layout.lineWidth - w) / 2
            if (i == 0 && prefix.isNotEmpty() && line.startsWith(prefix)) {
                drawText(c, prefix, x, y, spk)
                drawText(c, line.substring(prefix.length), x + layout.prefixWidth, y, fg)
            } else {
                drawText(c, line, x, y, fg)
            }
            y += lineH
        }
    }

    private fun matchLayout(it: ViewItem, W: Float, H: Float): MatchLayout {
        val key = listOf(it.b.joinToString(","), it.lh, it.speaker, it.tr, it.kind, it.lines, it.align,
            W, H, fontScale, dx, dy, sx, sy).joinToString("|")
        layoutCache[key]?.let { return it }
        val x0 = mx(it.b[0], W); val y0 = my(it.b[1], H); val x1 = mx(it.b[2], W); val y1 = my(it.b[3], H)
        val ow = max(8f, x1 - x0)
        val lh = max(8f, it.lh * H * sy)
        val base = max(10f, lh * 0.78f * fontScale)
        val text = if (it.speaker.isNotEmpty()) "${it.speaker}: ${it.tr}" else it.tr
        val nl = max(1, it.lines)
        val isSub = it.kind == "subtitle" || it.kind == "objective"
        var size = base
        var lines: List<String>
        while (true) {
            fill.textSize = size
            lines = wrapText(text, fill::measureText, ow * 1.06f)
            if (lines.size <= nl || size <= base * 0.82f) break
            size *= 0.96f
        }
        if (lines.size > nl) {
            fill.textSize = size
            lines = when {
                isSub -> wrapText(text, fill::measureText, max(ow, W * 0.82f))
                it.align == "l" -> wrapText(text, fill::measureText, max(ow, min(W - x0 - 8, ow * 1.6f)))
                else -> wrapText(text, fill::measureText, max(ow, ow * 1.5f))
            }
        }
        fill.textSize = size
        val widths = lines.map(fill::measureText)
        val lineH = fill.fontSpacing
        val lw = widths.maxOrNull() ?: 0f
        val th = lines.size * lineH
        var tx0 = if (it.align == "l") x0 else (x0 + x1) / 2 - lw / 2
        tx0 = max(4f, min(tx0, W - lw - 4))
        val ty0 = if (isSub && lines.size > nl) y1 - th else (y0 + y1) / 2 - th / 2
        val pad = max(2f, lh * 0.16f)
        val cover = RectF(min(x0, tx0) - pad, min(y0, ty0) - pad, max(x1, tx0 + lw) + pad, max(y1, ty0 + th) + pad)
        val prefix = if (it.speaker.isNotEmpty()) "${it.speaker}:" else ""
        val cached = MatchLayout(lines, widths, size, lineH, lw, th, tx0, ty0, pad, cover, fill.measureText(prefix))
        layoutCache[key] = cached
        return cached
    }

    private fun lum(c: Int) = (0.299 * Color.red(c) + 0.587 * Color.green(c) + 0.114 * Color.blue(c)).toInt()
    private fun drawBox(c: Canvas, it: ViewItem, W: Float, H: Float) {
        if (it.tr.isEmpty()) return
        val layout = boxLayout(it, W, H)
        val cover = layout.cover
        val pad = layout.pad
        val lines = layout.lines
        val lineH = layout.lineHeight
        val size = layout.size
        fill.textSize = size
        val backgroundColor = if (bgMode == "black" || bgMode == "semi") Color.BLACK else boxColor
        bg.color = Color.argb(if (bgMode == "none") 0 else boxAlpha, Color.red(backgroundColor), Color.green(backgroundColor), Color.blue(backgroundColor))
        c.drawRoundRect(cover, 8f, 8f, bg)
        stroke.textSize = size
        stroke.strokeWidth = max(2f, size / 12f)
        val fm = fill.fontMetrics
        var y = cover.top + (cover.height() - lines.size * lineH) / 2 - fm.ascent
        val prefix = if (it.speaker.isNotEmpty()) "${it.speaker}:" else ""
        for ((i, line) in lines.withIndex()) {
            val lw = layout.widths[i]
            val x = cover.left + (cover.width() - lw) / 2
            if (i == 0 && prefix.isNotEmpty() && line.startsWith(prefix)) {
                drawText(c, prefix, x, y, speakerColor)
                drawText(c, line.substring(prefix.length), x + layout.prefixWidth, y, textColor)
            } else {
                drawText(c, line, x, y, textColor)
            }
            y += lineH
        }
    }

    private fun boxLayout(it: ViewItem, W: Float, H: Float): BoxLayout {
        val key = listOf(it.b.joinToString(","), it.lh, it.speaker, it.tr, it.kind, it.lines, it.align,
            W, H, fontScale, dx, dy, sx, sy).joinToString("|")
        boxLayoutCache[key]?.let { return it }
        val x0 = mx(it.b[0], W); val y0 = my(it.b[1], H); val x1 = mx(it.b[2], W); val y1 = my(it.b[3], H)
        val pad = max(6f, it.lh * H * 0.3f)
        val cover = RectF(x0 - pad, y0 - pad, x1 + pad, y1 + pad)
        if (it.kind == "subtitle" || it.kind == "objective") {
            val lo = W * 0.06f; val hi = W * 0.94f
            val aw = max(cover.width(), min(hi - lo, cover.width() * 1.35f))
            val left = max(lo, min(cover.centerX() - aw / 2, hi - aw))
            cover.left = left; cover.right = left + aw
        } else cover.right = min(W, cover.left + cover.width() * 1.25f)
        val text = if (it.speaker.isNotEmpty()) "${it.speaker}: ${it.tr}" else it.tr
        var size = max(16f, it.lh * H * 0.92f * fontScale)
        val innerW = cover.width() - 2 * pad
        var lines: List<String>
        var lineH: Float
        while (true) {
            fill.textSize = size
            lines = wrapText(text, fill::measureText, innerW)
            lineH = fill.fontSpacing
            if (lines.size * lineH <= (cover.height() - 2 * pad) * 1.15f || size <= 16f) break
            size -= 1f
        }
        val need = lines.size * lineH + 2 * pad
        if (need > cover.height()) {
            if (it.kind == "subtitle") cover.top = cover.bottom - need else cover.bottom = cover.top + need
        }
        fill.textSize = size
        val prefix = if (it.speaker.isNotEmpty()) "${it.speaker}:" else ""
        val result = BoxLayout(cover, lines, lines.map(fill::measureText), size, lineH, pad, fill.measureText(prefix))
        boxLayoutCache[key] = result
        return result
    }

    private fun drawText(c: Canvas, t: String, x: Float, y: Float, color: Int) {
        c.drawText(t, x, y, stroke)
        fill.color = color
        c.drawText(t, x, y, fill)
    }
}

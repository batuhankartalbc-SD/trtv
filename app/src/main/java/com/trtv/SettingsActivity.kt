package com.trtv

import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.Color
import android.graphics.Typeface
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.view.KeyEvent
import android.view.View
import android.widget.Button
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/** Oyun görüntüsünün üstünde açılan, kumandayla kullanılan ayarlar paneli. */
class SettingsActivity : Activity() {
    private data class Row(val key: String, val title: String)
    private val rows = listOf(
        Row("profile", "Oyun profili"),
        Row("engine", "Çeviri motoru"),
        Row("font", "Yazı tipi"),
        Row("visible", "Türkçe yazılar"),
        Row("font_scale", "Yazı boyutu"),
        Row("bg_mode", "Yazı arkası"),
        Row("bg_opacity", "Yazı arkası opaklığı"),
        Row("speaker_colors_on", "Konuşmacı renkleri"),
        Row("tts_enabled", "Türkçe seslendirme"),
        Row("cat_dialogue", "Konuşmalar"),
        Row("cat_menu", "Menüler"),
        Row("cat_controls", "Kontroller"),
        Row("cat_other", "Diğer yazılar"),
        Row("cat_nav", "GPS / yön"),
        Row("disconnect_warning", "Bağlantı uyarısı"),
        Row("replay", "Son konuşmayı tekrar göster")
    )
    private val values = mutableMapOf<String, Any>()
    private val rowViews = mutableMapOf<String, Button>()
    private lateinit var connectionLabel: TextView
    private lateinit var pcStatusLabel: TextView
    private lateinit var preview: TextView
    private lateinit var fontPreview: TextView
    private var receiverRegistered = false
    private val stateReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) { loadState(); renderRows(); renderConnection() }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.setBackgroundDrawableResource(android.R.color.transparent)
        loadState()

        val frame = FrameLayout(this)
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 20, 24, 20)
            setBackgroundColor(Color.argb(235, 17, 23, 30))
        }
        val title = TextView(this).apply {
            text = "Brolis Game Translate · Ayarlar"; textSize = 25f; typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.rgb(61, 220, 151)); setPadding(10, 4, 10, 18)
        }
        panel.addView(title)
        connectionLabel = TextView(this).apply {
            textSize = 16f; setTextColor(Color.rgb(255, 190, 100)); setPadding(10, 0, 10, 14)
        }
        panel.addView(connectionLabel)
        preview = TextView(this).apply {
            text = "Örnek Türkçe yazı"
            textSize = 19f; setTextColor(Color.WHITE); setPadding(18, 14, 18, 14)
        }
        val previewSurface = FrameLayout(this).apply { setBackgroundColor(Color.rgb(91, 108, 124)) }
        previewSurface.addView(preview, FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.WRAP_CONTENT))
        panel.addView(previewSurface, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply { bottomMargin = 12 })
        val scroll = ScrollView(this).apply { isFillViewport = false; overScrollMode = View.OVER_SCROLL_IF_CONTENT_SCROLLS }
        val list = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        rows.forEachIndexed { index, row ->
            val button = Button(this).apply {
                tag = index
                textSize = 16f
                gravity = Gravity.CENTER_VERTICAL or Gravity.START
                isAllCaps = false
                setOnClickListener { activate(row.key) }
            }
            rowViews[row.key] = button
            list.addView(button, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 74))
            if (row.key == "engine") {
                list.addView(TextView(this).apply {
                    text = "Değişince çeviri 1–2 sn durur"
                    textSize = 13f
                    setTextColor(Color.rgb(174, 183, 194))
                    setPadding(18, 0, 18, 8)
                    isFocusable = false
                })
            }
            if (row.key == "font") {
                fontPreview = TextView(this).apply {
                    text = "Polisler sahil yolunu kapatmış."
                    textSize = 18f
                    setTextColor(Color.WHITE)
                    setPadding(20, 10, 20, 14)
                    isFocusable = false
                }
                list.addView(fontPreview)
            }
        }
        scroll.addView(list)
        panel.addView(scroll, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f))
        pcStatusLabel = TextView(this).apply {
            textSize = 13f
            setTextColor(Color.rgb(165, 174, 186))
            setPadding(10, 10, 10, 0)
            isFocusable = false
        }
        panel.addView(pcStatusLabel)
        frame.addView(panel, FrameLayout.LayoutParams((resources.displayMetrics.widthPixels * 0.58f).toInt(), FrameLayout.LayoutParams.MATCH_PARENT, Gravity.RIGHT))
        setContentView(frame)
        renderRows(); renderConnection()
        rowViews["visible"]?.requestFocus()
    }

    override fun onStart() {
        super.onStart()
        if (!receiverRegistered) {
            val filter = IntentFilter(OverlayService.SETTINGS_ACTION)
            if (Build.VERSION.SDK_INT >= 33) registerReceiver(stateReceiver, filter, Context.RECEIVER_NOT_EXPORTED) else registerReceiver(stateReceiver, filter)
            receiverRegistered = true
        }
        loadState(); renderRows(); renderConnection()
    }

    override fun onResume() {
        super.onResume()
        OverlayService.suppressOverlayUi(true)
    }

    override fun onPause() {
        OverlayService.suppressOverlayUi(false)
        super.onPause()
    }

    override fun onStop() {
        if (receiverRegistered) { unregisterReceiver(stateReceiver); receiverRegistered = false }
        super.onStop()
    }

    private fun loadState() {
        val state = OverlayService.currentSettings()
        values["visible"] = state.visible
        values["font_scale"] = (state.scale * 100).toInt().coerceIn(60, 250)
        values["bg_mode"] = state.bgm
        values["bg_opacity"] = state.opacity
        values["speaker_colors_on"] = state.speakerColors
        values["tts_enabled"] = state.tts
        values["cat_dialogue"] = state.dialogue
        values["cat_menu"] = state.menu
        values["cat_controls"] = state.controls
        values["cat_other"] = state.other
        values["cat_nav"] = state.nav
        values["disconnect_warning"] = getSharedPreferences("settings", MODE_PRIVATE).getBoolean("disconnect_warning", true)
        values["profiles"] = state.profiles
        values["profile"] = state.profile
        values["engines"] = state.engines
        values["engine"] = state.engine
        values["font"] = state.font
    }

    private fun displayValue(key: String): String = when (key) {
        "font_scale" -> "%${values[key] ?: 110}"
        "bg_opacity" -> "%${values[key] ?: 100}"
        "bg_mode" -> when (values[key]) { "black" -> "Simsiyah"; "semi" -> "Yarı saydam"; "none" -> "Kutu yok"; "game" -> "Oyun rengi"; else -> "Simsiyah" }
        "profile" -> (values["profile"] as? String)?.takeIf { it.isNotBlank() } ?: "Seçilemez"
        "engine" -> when (values["engine"]) {
            "local" -> "Yerel (anlık)"
            "gemini" -> "Gemini (en doğal)"
            "free" -> "Ücretsiz (internet)"
            else -> "Seçilemez"
        }
        "font" -> when (values["font"]) {
            "condensed" -> "Oyun stili (dar)"
            "rounded" -> "Yuvarlak"
            "clean" -> "Sade"
            else -> "Varsayılan"
        }
        "replay" -> "Göster"
        else -> if (values[key] == true) "Açık" else "Kapalı"
    }

    private fun renderRows() {
        rows.forEach { row ->
            val button = rowViews[row.key] ?: return@forEach
            button.text = "${row.title}     ‹  ${displayValue(row.key)}  ›"
            if (row.key == "profile" || row.key == "engine") {
                val available = OverlayService.isComputerConnected() &&
                    ((if (row.key == "profile") values["profiles"] else values["engines"]) as? List<*>)?.isNotEmpty() == true
                button.isEnabled = available
                button.alpha = if (available) 1f else 0.48f
            }
        }
        if (::preview.isInitialized) {
            val mode = values["bg_mode"] as? String ?: "black"
            val percent = values["bg_opacity"] as? Int ?: 100
            val opacity = if (mode == "none") 0 else percent * 255 / 100
            preview.setBackgroundColor(Color.argb(opacity, 0, 0, 0))
            preview.text = when (mode) {
                "none" -> "Örnek Türkçe yazı · Kutu yok"
                "semi" -> "Örnek Türkçe yazı · Yarı saydam %$percent"
                "game" -> "Örnek Türkçe yazı · Oyun rengi"
                else -> "Örnek Türkçe yazı · Simsiyah %$percent"
            }
        }
        if (::fontPreview.isInitialized) fontPreview.typeface = selectedTypeface(values["font"] as? String ?: "default")
        if (::pcStatusLabel.isInitialized) renderPcStatus()
    }

    private fun selectedTypeface(font: String): Typeface {
        if (font == "default") return Typeface.create("sans-serif-medium", Typeface.BOLD)
        return try {
            if (font == "condensed") return Typeface.create(Typeface.createFromAsset(assets, "fonts/condensed.ttf"), Typeface.BOLD)
            val variation = when (font) {
                "rounded" -> "'wght' 700"
                "clean" -> "'opsz' 18, 'wght' 600"
                else -> "'wght' 600"
            }
            Typeface.Builder(assets, "fonts/$font.ttf").setFontVariationSettings(variation).build().let { Typeface.create(it, Typeface.BOLD) }
        } catch (_: Exception) { Typeface.create("sans-serif-medium", Typeface.BOLD) }
    }

    private fun renderConnection() {
        connectionLabel.text = if (OverlayService.isComputerConnected()) "Bilgisayar bağlı" else "Bilgisayar bağlı değil — ayarlar uygulanamaz"
        connectionLabel.setTextColor(if (OverlayService.isComputerConnected()) Color.rgb(110, 235, 175) else Color.rgb(255, 170, 110))
    }

    private fun renderPcStatus() {
        val state = OverlayService.currentSettings()
        val pcVersion = state.pcVersion
        val updateNeeded = isOlderThanPcMinimum(pcVersion)
        val tvVersion = try { packageManager.getPackageInfo(packageName, 0).versionName ?: "—" } catch (_: Exception) { "—" }
        val gemini = if (state.geminiStatus.equals("Kapalı", true)) "kapalı" else state.geminiStatus
        val text = buildString {
            append("PC $pcVersion · TV $tvVersion · Gemini: $gemini")
            if (updateNeeded) append("\nBilgisayardaki uygulamayı güncelleyin")
        }
        pcStatusLabel.text = text
        val warning = updateNeeded || state.geminiStatus.contains("kota", true) || state.geminiStatus.contains("geçersiz", true)
        pcStatusLabel.setTextColor(if (warning) Color.rgb(255, 205, 92) else Color.rgb(165, 174, 186))
    }

    private fun isOlderThanPcMinimum(version: String): Boolean {
        val match = Regex("^(\\d+)\\.(\\d+)\\.(\\d+)").find(version) ?: return true
        val parts = match.groupValues.drop(1).map { it.toIntOrNull() ?: 0 }
        val minimum = listOf(2, 3, 0)
        for (index in minimum.indices) {
            if (parts[index] != minimum[index]) return parts[index] < minimum[index]
        }
        return false
    }

    override fun dispatchKeyEvent(event: KeyEvent): Boolean {
        if (event.action == KeyEvent.ACTION_DOWN && (event.keyCode == KeyEvent.KEYCODE_DPAD_LEFT || event.keyCode == KeyEvent.KEYCODE_DPAD_RIGHT)) {
            val key = (currentFocus?.tag as? Int)?.let { rows.getOrNull(it)?.key }
            if (key != null && key != "disconnect_warning" && key != "replay") {
                change(key, event.keyCode == KeyEvent.KEYCODE_DPAD_RIGHT)
                return true
            }
        }
        return super.dispatchKeyEvent(event)
    }

    private fun activate(key: String) {
        if (key == "replay") {
            OverlayService.changeSetting("replay", true)
            finish()
            return
        }
        when (key) {
            "disconnect_warning" -> {
                val enabled = values[key] != true
                values[key] = enabled
                getSharedPreferences("settings", MODE_PRIVATE).edit().putBoolean("disconnect_warning", enabled).apply()
                OverlayService.setDisconnectWarning(enabled)
                renderRows()
            }
            "font_scale", "bg_mode", "bg_opacity", "font" -> change(key, true)
            "profile", "engine" -> change(key, true)
            else -> change(key, null)
        }
    }

    /** Sağ + / sol −; OK boolean ayarları açıp kapatır. */
    private fun change(key: String, increase: Boolean?) {
        val value: Any = when (key) {
            "font_scale" -> ((values[key] as? Int ?: 110) + if (increase == false) -5 else 5).coerceIn(60, 250).also { values[key] = it }.let { it / 100.0 }
            "bg_opacity" -> ((values[key] as? Int ?: 100) + if (increase == false) -5 else 5).coerceIn(0, 100).also { values[key] = it }
            "bg_mode" -> {
                val modes = listOf("black", "semi", "none", "game")
                val current = modes.indexOf(values[key] as? String ?: "black").coerceAtLeast(0)
                modes[(current + if (increase == false) modes.size - 1 else 1) % modes.size].also { values[key] = it }
            }
            "font" -> {
                val fonts = listOf("default", "condensed", "rounded", "clean")
                val current = fonts.indexOf(values[key] as? String ?: "default").coerceAtLeast(0)
                fonts[(current + if (increase == false) fonts.size - 1 else 1) % fonts.size].also { values[key] = it }
            }
            "profile", "engine" -> {
                val options = (values[if (key == "profile") "profiles" else "engines"] as? List<*>)
                    ?.filterIsInstance<String>().orEmpty()
                if (!OverlayService.isComputerConnected() || options.isEmpty()) return
                val selected = values[key] as? String
                val current = options.indexOfFirst { it == selected }.coerceAtLeast(0)
                options[(current + if (increase == false) options.size - 1 else 1) % options.size]
                    .also { values[key] = it }
            }
            else -> (values[key] != true).also { values[key] = it }
        }
        if (key != "font_scale") values[key] = value
        OverlayService.changeSetting(key, value)
        renderRows(); renderConnection()
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        if (keyCode == KeyEvent.KEYCODE_BACK) { finish(); return true }
        return super.onKeyDown(keyCode, event)
    }
}

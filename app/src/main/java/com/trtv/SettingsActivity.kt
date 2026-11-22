package com.trtv

import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
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
        Row("auto_mode", "Çevrilecek yer"),
        Row("film_mode", "Bağımsız mod (film/dizi)"),
        Row("film_band", "Altyazı bandı"),
        Row("fps", "Yakalama hızı"),
        Row("instant", "Anlık mod"),
        Row("output", "Çeviri çıkışı"),
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
        Row("replay", "Son konuşmayı tekrar göster"),
        Row("remote_help", "Kumanda tuşları")
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
            setPadding(34, 28, 34, 28)
            setBackgroundColor(Color.rgb(11, 15, 20))
        }
        val title = TextView(this).apply {
            text = "Ayarlar"; textSize = 32f; typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.rgb(61, 220, 151)); setPadding(10, 4, 10, 18)
        }
        panel.addView(title)
        connectionLabel = TextView(this).apply {
            textSize = 20f; setTextColor(Color.rgb(255, 190, 100)); setPadding(10, 0, 10, 14)
        }
        panel.addView(connectionLabel)
        preview = TextView(this).apply {
            text = "Örnek Türkçe yazı"
            textSize = 22f; setTextColor(Color.WHITE); setPadding(18, 14, 18, 14)
        }
        val previewSurface = FrameLayout(this).apply { setBackgroundColor(Color.rgb(91, 108, 124)) }
        previewSurface.addView(preview, FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.WRAP_CONTENT))
        panel.addView(previewSurface, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply { bottomMargin = 12 })
        val scroll = ScrollView(this).apply { isFillViewport = false; overScrollMode = View.OVER_SCROLL_IF_CONTENT_SCROLLS }
        val list = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        rows.forEachIndexed { index, row ->
            val button = Button(this).apply {
                tag = index
                textSize = 20f
                gravity = Gravity.CENTER_VERTICAL or Gravity.START
                isAllCaps = false
                setTextColor(Color.WHITE)
                background = rowBackground()
                setOnFocusChangeListener { view, focused ->
                    view.background = rowBackground(focused)
                    view.scaleX = if (focused) 1.03f else 1f
                    view.scaleY = if (focused) 1.03f else 1f
                }
                setOnClickListener { activate(row.key) }
            }
            rowViews[row.key] = button
            list.addView(button, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 82).apply { bottomMargin = 6 })
            if (row.key == "engine") {
                list.addView(TextView(this).apply {
                    text = "Değişince çeviri 1–2 sn durur"
                    textSize = 18f
                    setTextColor(Color.rgb(174, 183, 194))
                    setPadding(18, 0, 18, 8)
                    isFocusable = false
                })
            }
            if (row.key == "font") {
                fontPreview = TextView(this).apply {
                    text = "Polisler sahil yolunu kapatmış."
                    textSize = 22f
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
            textSize = 18f
            setTextColor(Color.rgb(165, 174, 186))
            setPadding(10, 10, 10, 0)
            isFocusable = false
        }
        panel.addView(pcStatusLabel)
        frame.addView(panel, FrameLayout.LayoutParams((resources.displayMetrics.widthPixels * 0.68f).toInt(), FrameLayout.LayoutParams.MATCH_PARENT, Gravity.RIGHT))
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
        values["fps"] = state.fps
        values["instant"] = state.instant
        values["auto_mode"] = state.autoMode
        values["output"] = state.output
        values["film_mode"] = getSharedPreferences(IndependentModeService.PREFS, MODE_PRIVATE)
            .getBoolean(IndependentModeService.KEY_ENABLED, false)
        values["film_band"] = getSharedPreferences(IndependentModeService.PREFS, MODE_PRIVATE)
            .getInt(IndependentModeService.KEY_BAND, 35)
    }

    private fun rowBackground(focused: Boolean = false) = GradientDrawable().apply {
        cornerRadius = 14f
        setColor(if (focused) Color.rgb(24, 54, 45) else Color.rgb(18, 24, 33))
        setStroke(if (focused) 3 else 1, if (focused) Color.rgb(62, 230, 160) else Color.rgb(30, 40, 51))
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
        "remote_help" -> "Aç"
        "film_mode" -> if (values[key] == true) "TV'de (açık)" else "PC'den (PS5)"
        "film_band" -> "%${values[key] ?: 35} alt"
        "fps" -> "${values[key] ?: 20} FPS"
        "instant" -> if (values[key] == true) "Açık" else "Kapalı"
        "auto_mode" -> if (values[key] == false) "Sadece bölgelerim" else "Tüm ekran"
        "output" -> when (values[key]) { "pc" -> "Bilgisayar"; "both" -> "Bilgisayar + TV"; else -> "TV" }
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
            if (key != null && key != "disconnect_warning" && key != "replay" && key != "remote_help" && key != "film_mode") {
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
        if (key == "remote_help") {
            startActivity(Intent(this, RemoteKeysActivity::class.java))
            return
        }
        if (key == "film_band") {
            change(key, true)
            return
        }
        when (key) {
            "film_mode" -> {
                if (IndependentModeService.active || values[key] == true) {
                    startService(Intent(this, IndependentModeService::class.java).setAction(IndependentModeService.ACTION_STOP))
                    values[key] = false
                    renderRows()
                } else {
                    val manager = getSystemService(android.media.projection.MediaProjectionManager::class.java)
                    @Suppress("DEPRECATION")
                    startActivityForResult(manager.createScreenCaptureIntent(), REQUEST_FILM_MODE)
                }
            }
            "disconnect_warning" -> {
                val enabled = values[key] != true
                values[key] = enabled
                getSharedPreferences("settings", MODE_PRIVATE).edit().putBoolean("disconnect_warning", enabled).apply()
                OverlayService.setDisconnectWarning(enabled)
                renderRows()
            }
            "font_scale", "bg_mode", "bg_opacity", "font", "film_band", "fps", "output" -> change(key, true)
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
            "film_band" -> {
                val choices = listOf(35, 50, 75, 100)
                val current = choices.indexOf(values[key] as? Int ?: 35).coerceAtLeast(0)
                choices[(current + if (increase == false) choices.size - 1 else 1) % choices.size]
                    .also { values[key] = it }
            }
            "fps" -> {
                val rates = listOf(10, 20, 30, 45, 60)
                val current = rates.indexOf(values[key] as? Int ?: 20).coerceAtLeast(0)
                rates[(current + if (increase == false) rates.size - 1 else 1) % rates.size].also { values[key] = it }
            }
            "output" -> {
                val outputs = listOf("tv", "pc", "both")
                val current = outputs.indexOf(values[key] as? String ?: "tv").coerceAtLeast(0)
                outputs[(current + if (increase == false) outputs.size - 1 else 1) % outputs.size].also { values[key] = it }
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
        if (key == "film_band") {
            getSharedPreferences(IndependentModeService.PREFS, MODE_PRIVATE).edit()
                .putInt(IndependentModeService.KEY_BAND, value as Int).apply()
        }
        renderRows(); renderConnection()
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        if (keyCode == KeyEvent.KEYCODE_BACK) { finish(); return true }
        return super.onKeyDown(keyCode, event)
    }

    @Deprecated("MediaProjection consent callback")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != REQUEST_FILM_MODE) return
        if (resultCode == RESULT_OK && data != null) {
            val service = Intent(this, IndependentModeService::class.java)
                .putExtra(IndependentModeService.EXTRA_RESULT_CODE, resultCode)
                .putExtra(IndependentModeService.EXTRA_RESULT_DATA, data)
            if (Build.VERSION.SDK_INT >= 26) startForegroundService(service) else startService(service)
            values["film_mode"] = true
            // İzin sonrası video uygulamasını öne çıkar; OCR, Brolis ayar metnini okumamalı.
            finishAffinity()
        } else values["film_mode"] = false
        getSharedPreferences(IndependentModeService.PREFS, MODE_PRIVATE).edit()
            .putBoolean(IndependentModeService.KEY_ENABLED, values["film_mode"] == true).apply()
        renderRows()
    }

    companion object { private const val REQUEST_FILM_MODE = 813 }
}

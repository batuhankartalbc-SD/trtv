package com.trtv

import android.app.Activity
import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.KeyEvent
import android.widget.LinearLayout
import android.widget.TextView
import org.json.JSONObject

/** Kumandayla hizalama; saydam pencere HDMI görüntüsünü arkada bırakır. */
class CalibrateActivity : Activity() {
    private val handler = Handler(Looper.getMainLooper())
    private lateinit var hint: TextView
    private var scaleMode = false
    private var connected = false
    private var lastSentAt = 0L

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.setBackgroundDrawableResource(android.R.color.transparent)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.TOP or Gravity.CENTER_HORIZONTAL
            setPadding(24, 18, 24, 0)
            isFocusable = true
            isFocusableInTouchMode = true
        }
        hint = TextView(this).apply {
            textSize = 16f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            setPadding(22, 14, 22, 14)
            setBackgroundColor(Color.argb(210, 10, 16, 24))
            gravity = Gravity.CENTER
        }
        root.addView(hint, LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT))
        setContentView(root)
        root.requestFocus()
        connected = OverlayService.sendToPc(message("CAL_MODE_ON"))
        val prefs = getSharedPreferences("settings", MODE_PRIVATE)
        if (!prefs.getBoolean("alignment_hint_seen", false)) {
            prefs.edit().putBoolean("alignment_hint_seen", true).apply()
            hint.text = "İpucu · Oklarla hizala · OK: kaydırma/ölçek · MENU veya uzun OK: sıfırla · Geri: bitir"
            handler.postDelayed({ if (!isFinishing) updateHint() }, 5000L)
        } else updateHint()
    }

    private fun message(action: String) = JSONObject().put("t", "cal").put("a", action)

    private fun send(action: String) {
        connected = OverlayService.sendToPc(message(action))
        updateHint()
    }

    private fun updateHint() {
        val mode = if (scaleMode) "Ölçek modu" else "Kaydırma modu"
        hint.text = if (connected) "Hizalama · Oklar: ${if (scaleMode) "ölçek" else "kaydır"} · OK: mod değiştir · Geri: bitir\n$mode · Uzun OK/MENU: sıfırla"
        else "Bilgisayar bağlı değil · TV bağlantısını kontrol edin\nHizalama · Oklar: kaydır · OK: ölçek modu · Geri: bitir"
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        if (keyCode == KeyEvent.KEYCODE_BACK) { finishCalibration(); return true }
        if (keyCode == KeyEvent.KEYCODE_MENU) {
            if (event.repeatCount == 1) send("CAL_RESET")
            return true
        }
        if (keyCode == KeyEvent.KEYCODE_DPAD_CENTER || keyCode == KeyEvent.KEYCODE_ENTER) {
            if (event.repeatCount == 0) super.onKeyDown(keyCode, event)
            return true
        }
        if (event.repeatCount > 0) {
            val now = android.os.SystemClock.uptimeMillis()
            if (now - lastSentAt < 120) return true
            lastSentAt = now
        }
        when (keyCode) {
            KeyEvent.KEYCODE_DPAD_LEFT -> send("CAL_LEFT")
            KeyEvent.KEYCODE_DPAD_RIGHT -> send("CAL_RIGHT")
            KeyEvent.KEYCODE_DPAD_UP -> send(if (scaleMode) "CAL_BIGGER" else "CAL_UP")
            KeyEvent.KEYCODE_DPAD_DOWN -> send(if (scaleMode) "CAL_SMALLER" else "CAL_DOWN")
            else -> return super.onKeyDown(keyCode, event)
        }
        return true
    }

    override fun onKeyLongPress(keyCode: Int, event: KeyEvent): Boolean {
        if (keyCode == KeyEvent.KEYCODE_DPAD_CENTER || keyCode == KeyEvent.KEYCODE_ENTER) {
            send("CAL_RESET")
            return true
        }
        return super.onKeyLongPress(keyCode, event)
    }

    override fun onKeyUp(keyCode: Int, event: KeyEvent): Boolean {
        if (keyCode == KeyEvent.KEYCODE_DPAD_CENTER || keyCode == KeyEvent.KEYCODE_ENTER) {
            if (event.isLongPress) return true
            scaleMode = !scaleMode
            updateHint()
            return true
        }
        return super.onKeyUp(keyCode, event)
    }

    private fun finishCalibration() {
        send("CAL_MODE_OFF")
        finish()
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        if (isFinishing) OverlayService.sendToPc(message("CAL_MODE_OFF"))
        super.onDestroy()
    }
}

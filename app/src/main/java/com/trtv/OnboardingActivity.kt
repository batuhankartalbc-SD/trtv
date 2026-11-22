package com.trtv

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.net.ConnectivityManager
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.view.Gravity
import android.view.KeyEvent
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import java.net.Inet4Address

/** İlk açılış ve tekrar gösterim için kumanda odaklı kurulum rehberi. */
class OnboardingActivity : Activity() {
    private val handler = Handler(Looper.getMainLooper())
    private var step = 0
    private lateinit var page: LinearLayout
    private lateinit var status: TextView
    private lateinit var primary: Button
    private lateinit var permission: Button
    private val refreshTask = object : Runnable {
        override fun run() {
            if (step == 1 || step == 2) renderStatus()
            handler.postDelayed(this, 1000L)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN)
        window.setBackgroundDrawableResource(android.R.color.transparent)
        step = savedInstanceState?.getInt("step") ?: 0
        page = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(72, 36, 72, 36)
            setBackgroundColor(Color.rgb(10, 14, 19))
        }
        setContentView(page)
        renderPage()
    }

    override fun onSaveInstanceState(outState: Bundle) {
        outState.putInt("step", step)
        super.onSaveInstanceState(outState)
    }

    override fun onResume() {
        super.onResume()
        OverlayService.suppressOverlayUi(true)
        if (Settings.canDrawOverlays(this)) OverlayService.start(this)
        renderPage()
        handler.removeCallbacks(refreshTask)
        refreshTask.run()
    }

    override fun onPause() {
        handler.removeCallbacks(refreshTask)
        OverlayService.suppressOverlayUi(false)
        super.onPause()
    }

    override fun dispatchKeyEvent(event: KeyEvent): Boolean {
        if (event.action == KeyEvent.ACTION_DOWN && event.repeatCount == 0) {
            when (event.keyCode) {
                KeyEvent.KEYCODE_DPAD_RIGHT -> { nextStep(); return true }
                KeyEvent.KEYCODE_DPAD_LEFT -> { previousStep(); return true }
                KeyEvent.KEYCODE_DPAD_CENTER, KeyEvent.KEYCODE_ENTER -> {
                    if (step == 1 && !Settings.canDrawOverlays(this) && permission.hasFocus()) requestOverlayPermission()
                    else nextStep()
                    return true
                }
            }
        }
        return super.dispatchKeyEvent(event)
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        if (keyCode == KeyEvent.KEYCODE_BACK) {
            if (step > 0) previousStep() else { setResult(RESULT_CANCELED); finish() }
            return true
        }
        return super.onKeyDown(keyCode, event)
    }

    private fun renderPage() {
        if (!::page.isInitialized) return
        page.removeAllViews()
        page.addView(TextView(this).apply {
            text = "BAŞLANGIÇ  ${step + 1} / 4"
            textSize = 16f; typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.rgb(62, 230, 160)); gravity = Gravity.CENTER
            setPadding(12, 0, 12, 20)
        })
        if (step == 0) {
            page.addView(ImageView(this).apply {
                setImageResource(R.drawable.logo)
                contentDescription = "Brolis Game Translate logosu"
                scaleType = ImageView.ScaleType.FIT_CENTER
            }, LinearLayout.LayoutParams(170, 170).apply { bottomMargin = 18 })
        }
        val titleText = when (step) {
            0 -> "Brolis Game Translate'e hoş geldin"
            1 -> "Ekran üstü izni"
            2 -> "Bilgisayara bağlan"
            else -> "Hazırsın"
        }
        page.addView(TextView(this).apply {
            text = titleText; textSize = 34f; typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE); gravity = Gravity.CENTER
            setPadding(10, 8, 10, 18)
        })
        val body = when (step) {
            0 -> "Bilgisayardaki uygulamanın çevirilerini oyunun üstünde gösterir."
            1 -> "Çevirilerin oyun görüntüsünde görünmesi için Brolis Game Translate'in ekranın üstünde gösterme iznine ihtiyacı var."
            2 -> "Bilgisayarda Brolis Game Translate'i aç; TV'yi kendisi bulur. Bilgisayar ve TV aynı ağa bağlı olmalı."
            else -> "Kurulum tamamlandı. Kumandayla Oyuna dön'e basıp PS5 girişine geçebilirsin."
        }
        page.addView(TextView(this).apply {
            text = body; textSize = 23f; setTextColor(Color.rgb(220, 228, 235))
            gravity = Gravity.CENTER; setLineSpacing(8f, 1f); setPadding(24, 8, 24, 20)
        })
        status = TextView(this).apply {
            textSize = 20f; setTextColor(Color.rgb(62, 230, 160)); gravity = Gravity.CENTER
            setLineSpacing(6f, 1f); setPadding(20, 8, 20, 24)
        }
        page.addView(status)
        permission = Button(this).apply {
            text = "İzin ver"; textSize = 21f; isAllCaps = false
            visibility = if (step == 1 && !Settings.canDrawOverlays(this@OnboardingActivity)) View.VISIBLE else View.GONE
            setOnClickListener { requestOverlayPermission() }
        }
        page.addView(permission)
        primary = Button(this).apply {
            text = if (step == 3) "Oyuna dön" else "Devam"
            textSize = 23f; isAllCaps = false
            setOnClickListener { if (step == 3) complete() else nextStep() }
        }
        page.addView(primary, LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply { topMargin = 12 })
        renderStatus()
        if (step == 1 && !Settings.canDrawOverlays(this)) permission.requestFocus() else primary.requestFocus()
    }

    private fun renderStatus() {
        if (!::status.isInitialized) return
        status.text = when (step) {
            1 -> if (Settings.canDrawOverlays(this)) "✓ Ekran üstü izni verildi" else "İzin henüz verilmedi"
            2 -> {
                val d = OverlayService.diagnosticsSnapshot()
                val connection = if (d.connected) "✓ Bağlandı: ${d.computerName}" else "Bilgisayar bekleniyor…"
                "$connection\nTV adresi: ${localIp()} · bağlantı noktası ${OverlayService.PORT}"
            }
            else -> ""
        }
        if (::permission.isInitialized && step == 1) permission.visibility = if (Settings.canDrawOverlays(this)) View.GONE else View.VISIBLE
    }

    private fun requestOverlayPermission() {
        try {
            startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")))
        } catch (_: Exception) {
            status.text = "İzin ayarları açılamadı. TV ayarlarından uygulama izinlerini aç."
        }
    }

    private fun nextStep() {
        if (step == 1 && !Settings.canDrawOverlays(this)) {
            status.text = "Devam etmek için önce ekran üstü iznini ver."
            permission.requestFocus()
            return
        }
        if (step < 3) { step++; renderPage() }
    }

    private fun previousStep() {
        if (step > 0) { step--; renderPage() }
        else { setResult(RESULT_CANCELED); finish() }
    }

    private fun complete() {
        getSharedPreferences("settings", MODE_PRIVATE).edit().putBoolean("onboarding_done", true).apply()
        setResult(RESULT_OK)
        finish()
    }

    private fun localIp(): String {
        return try {
            val cm = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
            cm.getLinkProperties(cm.activeNetwork)?.linkAddresses?.map { it.address }
                ?.firstOrNull { it is Inet4Address }?.hostAddress ?: "?"
        } catch (_: Exception) { "?" }
    }
}

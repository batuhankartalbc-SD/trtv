package com.trtv

import android.app.Activity
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
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import java.net.Inet4Address

/** Durum ekranı. Servisi başlatır; "Oyuna dön" ile kapanır, katman arka planda çalışmaya devam eder. */
class MainActivity : Activity() {
    private lateinit var info: TextView
    private val h = Handler(Looper.getMainLooper())
    private val tick = object : Runnable {
        override fun run() { refresh(); h.postDelayed(this, 1000) }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setBackgroundColor(Color.rgb(13, 17, 16))
            setPadding(80, 60, 80, 60)
        }
        root.addView(TextView(this).apply {
            text = "TRÇeviri TV"
            textSize = 40f
            setTextColor(Color.rgb(61, 220, 151))
            typeface = Typeface.DEFAULT_BOLD
        })
        root.addView(TextView(this).apply {
            text = "Bilgisayardaki TRÇeviri'nin çevirilerini oyun görüntüsünün üstünde gösterir."
            textSize = 18f
            setTextColor(Color.rgb(190, 200, 196))
            setPadding(0, 10, 0, 30)
        })
        info = TextView(this).apply { textSize = 22f; setTextColor(Color.WHITE); setLineSpacing(8f, 1f) }
        root.addView(info)
        val back = Button(this).apply {
            text = "Oyuna dön"
            textSize = 20f
            setOnClickListener { finish() }
        }
        root.addView(back, LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply { topMargin = 40 })
        setContentView(root)
        back.requestFocus()
    }

    override fun onResume() {
        super.onResume()
        if (Settings.canDrawOverlays(this)) {
            OverlayService.start(this)
        } else {
            try {
                startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")))
            } catch (_: Exception) { }
        }
        h.post(tick)
    }

    override fun onPause() {
        h.removeCallbacks(tick)
        super.onPause()
    }

    private fun ip(): String {
        val cm = getSystemService(ConnectivityManager::class.java)
        val lp = cm.getLinkProperties(cm.activeNetwork) ?: return "?"
        return lp.linkAddresses.map { it.address }.firstOrNull { it is Inet4Address }?.hostAddress ?: "?"
    }

    private fun refresh() {
        val perm = Settings.canDrawOverlays(this)
        info.text = buildString {
            append(if (perm) "✔ Ekran üstü izni var\n" else "✘ Ekran üstü izni YOK — ayarlardan TRÇeviri TV'ye izin verin\n")
            append("• Durum: ${OverlayService.status}\n")
            append("• Bu TV'nin adresi: ${ip()}  (port ${OverlayService.PORT})\n\n")
            append("Bilgisayarda TRÇeviri'yi açın; TV'yi kendisi bulup bağlanır.\n")
            append("Bağlandıktan sonra 'Oyuna dön'e basıp PS5 girişine geçin.")
        }
    }
}

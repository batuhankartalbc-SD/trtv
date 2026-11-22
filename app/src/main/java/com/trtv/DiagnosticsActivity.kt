package com.trtv

import android.app.Activity
import android.content.Context
import android.net.ConnectivityManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.graphics.Color
import android.graphics.Typeface
import android.content.pm.PackageInfo
import java.net.Inet4Address

/** TV'de bilgisayar bağlantısı ve katman durumu için canlı tanılama ekranı. */
class DiagnosticsActivity : Activity() {
    private lateinit var details: TextView
    private val handler = Handler(Looper.getMainLooper())
    private val refreshTask = object : Runnable {
        override fun run() {
            if (::details.isInitialized) details.text = diagnosticText()
            handler.postDelayed(this, 1000L)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(48, 28, 48, 28)
            setBackgroundColor(Color.argb(238, 10, 14, 19))
        }
        root.addView(TextView(this).apply {
            text = "Brolis — Tanılama"
            textSize = 32f
            setTextColor(Color.rgb(62, 230, 160))
            typeface = Typeface.DEFAULT_BOLD
            setPadding(12, 8, 12, 18)
        })
        val scroll = ScrollView(this)
        details = TextView(this).apply {
            textSize = 21f
            setTextColor(Color.WHITE)
            setLineSpacing(7f, 1f)
            setPadding(22, 20, 22, 20)
            setBackgroundColor(Color.rgb(22, 29, 38))
            isFocusable = false
        }
        scroll.addView(details, ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        root.addView(scroll, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
        root.addView(Button(this).apply {
            text = "Geri dön"
            textSize = 20f
            setOnClickListener { finish() }
        })
        setContentView(root)
    }

    override fun onResume() {
        super.onResume()
        OverlayService.suppressOverlayUi(true)
        handler.removeCallbacks(refreshTask)
        refreshTask.run()
    }

    override fun onPause() {
        handler.removeCallbacks(refreshTask)
        OverlayService.suppressOverlayUi(false)
        super.onPause()
    }

    private fun diagnosticText(): String {
        val d = OverlayService.diagnosticsSnapshot()
        val pc = OverlayService.currentSettings()
        val display = resources.displayMetrics
        val version = try {
            val p = packageManager.getPackageInfo(packageName, 0)
            val code = if (android.os.Build.VERSION.SDK_INT >= 28) p.longVersionCode else legacyVersionCode(p)
            "${p.versionName} (build $code)"
        } catch (_: Exception) { "Bilinmiyor" }
        val age = d.lastMessageSeconds?.let { "%.1f saniye önce".format(java.util.Locale.US, it) } ?: "Henüz mesaj alınmadı"
        val cm = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val ip = cm.getLinkProperties(cm.activeNetwork)?.linkAddresses
            ?.map { it.address }?.firstOrNull { it is Inet4Address } ?: "?"
        val overlayPermission = Settings.canDrawOverlays(this)
        return buildString {
            appendLine("Bilgisayar bağlantısı: ${if (d.connected) "Bağlı" else "Bağlı değil"}")
            appendLine("Bilgisayar adı: ${d.computerName}")
            appendLine("Bilgisayar sürümü: ${pc.pcVersion}")
            appendLine("Gemini durumu: ${pc.geminiStatus}")
            appendLine("Çeviri motoru: ${pc.pcEngine}")
            appendLine("Oyun profili: ${pc.pcProfile}")
            appendLine("Son mesaj: $age")
            appendLine("Son 10 saniyedeki items mesajı: ${d.itemsLast10Seconds}")
            appendLine("Ekrandaki çeviri kutusu: ${d.visibleBoxes}")
            appendLine("Ekran: ${d.width} × ${d.height} px · yoğunluk ${"%.2f".format(java.util.Locale.US, d.density)}")
            appendLine("Ekran üstü izni: ${if (overlayPermission) "Var" else "Yok"}")
            appendLine("Uygulama sürümü: $version")
            appendLine("TV adresi: $ip · port ${OverlayService.PORT}")
            append("Hizalama: dx ${"%.4f".format(java.util.Locale.US, d.dx)}, dy ${"%.4f".format(java.util.Locale.US, d.dy)}, sx ${"%.4f".format(java.util.Locale.US, d.sx)}, sy ${"%.4f".format(java.util.Locale.US, d.sy)}")
        }
    }

    @Suppress("DEPRECATION")
    private fun legacyVersionCode(info: PackageInfo): Long = info.versionCode.toLong()
}

package com.trtv

import android.app.Activity
import android.content.Context
import android.content.pm.PackageInfo
import android.graphics.Color
import android.graphics.Typeface
import android.net.ConnectivityManager
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.net.Inet4Address

/** Kurulum ve temel sorun giderme adımları; TV kumandasıyla gezilir. */
class HelpActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(54, 28, 54, 24)
            setBackgroundColor(Color.rgb(10, 14, 19))
        }
        root.addView(TextView(this).apply {
            text = "Brolis Game Translate · Yardım"
            textSize = 32f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.rgb(62, 230, 160))
            setPadding(12, 4, 12, 16)
        })
        val scroll = ScrollView(this).apply {
            isFillViewport = false
            isFocusable = true
            isFocusableInTouchMode = true
        }
        val steps = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        val helpLines = listOf(
            "1. Bilgisayara Brolis Game Translate'i kurun: github.com/batuhankartalbc-SD/trtv → Releases → TRCeviri-Kurulum.exe.",
            "2. PS Remote Play'i açıp PS5'e bağlanın. Oyunda altyazıları açın.",
            "3. Bilgisayar ve TV aynı modemde olsun. Bilgisayardaki uygulama TV'yi kendisi bulur.",
            "4. Türkçe kayıyorsa: Ana ekran → Kumandayla hizala.",
            "5. Bir şey çalışmıyorsa: Ana ekran → Tanılama.",
            "Film izlerken: Mod'u TV'nin kendisi olarak seçin ve ekran yakalama izni verin. Netflix/Disney+ gibi DRM'li uygulamalar görüntüyü siyah gösterebilir; bu içerikler çevrilemez. YouTube'da varsa Altyazılar → Otomatik çeviri → Türkçe seçeneğini kullanın."
        )
        helpLines.forEachIndexed { index, line ->
            val normalColor = if (index % 2 == 0) Color.rgb(22, 29, 38) else Color.rgb(17, 23, 30)
            steps.addView(TextView(this).apply {
                text = line
                textSize = 23f
                setTextColor(Color.WHITE)
                setPadding(22, 18, 22, 18)
                setBackgroundColor(normalColor)
                isFocusable = true
                isFocusableInTouchMode = true
                setOnFocusChangeListener { view, focused ->
                    view.setBackgroundColor(if (focused) Color.rgb(31, 60, 53) else normalColor)
                }
            }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                bottomMargin = 8
            })
        }
        steps.addView(TextView(this).apply {
            text = "TV bilgisi: ${tvIp()} · Uygulama ${version()}"
            textSize = 19f
            setTextColor(Color.rgb(190, 202, 214))
            setPadding(20, 16, 20, 20)
            isFocusable = false
        })
        scroll.addView(steps)
        root.addView(scroll, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
        root.addView(Button(this).apply {
            text = "Kapat"
            textSize = 20f
            setOnClickListener { finish() }
        }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
            gravity = Gravity.CENTER_HORIZONTAL
            topMargin = 12
        })
        setContentView(root)
        scroll.requestFocus()
    }

    override fun onResume() {
        super.onResume()
        OverlayService.suppressOverlayUi(true)
    }

    override fun onPause() {
        OverlayService.suppressOverlayUi(false)
        super.onPause()
    }

    override fun onKeyDown(keyCode: Int, event: android.view.KeyEvent): Boolean {
        if (keyCode == android.view.KeyEvent.KEYCODE_BACK) { finish(); return true }
        return super.onKeyDown(keyCode, event)
    }

    private fun tvIp(): String {
        val cm = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        return cm.getLinkProperties(cm.activeNetwork)?.linkAddresses?.map { it.address }
            ?.firstOrNull { it is Inet4Address }?.hostAddress ?: "?"
    }

    private fun version(): String = try {
        val info = packageManager.getPackageInfo(packageName, 0)
        val code = if (Build.VERSION.SDK_INT >= 28) info.longVersionCode else legacyVersionCode(info)
        "${info.versionName} ($code)"
    } catch (_: Exception) { "bilinmiyor" }

    @Suppress("DEPRECATION")
    private fun legacyVersionCode(info: PackageInfo): Long = info.versionCode.toLong()
}

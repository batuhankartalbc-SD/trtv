package com.trtv

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import rikka.shizuku.Shizuku

class MainActivity : Activity() {
    private lateinit var status: TextView

    override fun onCreate(b: Bundle?) {
        super.onCreate(b)
        val col = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(48, 32, 48, 32) }
        status = TextView(this).apply { textSize = 16f; text = CaptureService.last.ifEmpty { "Hazır. Testi başlatıp HDMI girişine geçin." } }
        fun btn(t: String, f: () -> Unit) = col.addView(Button(this).apply { text = t; setOnClickListener { f() } })
        btn("Test: screencap PNG (1 sn)") { start("png") }
        btn("Test: screencap RAW (1 sn)") { start("raw") }
        btn("Test: screenrecord H264") { start("h264") }
        btn("Durdur") { stopService(Intent(this, CaptureService::class.java)); status.text = "Durduruldu" }
        btn("Ekran üstünde gösterme izni") {
            runCatching { startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName"))) }
                .onFailure { status.text = "İzin ekranı yok; ADB bağlanınca otomatik verilecek." }
        }
        btn("Shizuku izni iste (yedek)") {
            runCatching { if (Shizuku.pingBinder()) Shizuku.requestPermission(1) else status.text = "Shizuku çalışmıyor" }
        }
        col.addView(status)
        setContentView(ScrollView(this).apply { addView(col) })
        col.getChildAt(0).requestFocus()
    }

    private fun start(mode: String) {
        startForegroundService(Intent(this, CaptureService::class.java).putExtra("mode", mode))
        status.text = "Başlatıldı ($mode). Şimdi HDMI girişine geçin; sağ üstte sonuçlar görünecek."
    }

    override fun onResume() { super.onResume(); CaptureService.listener = { status.text = it } }
    override fun onPause() { CaptureService.listener = null; super.onPause() }
}

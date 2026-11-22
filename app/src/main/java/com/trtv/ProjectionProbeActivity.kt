package com.trtv

import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.Color
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import java.io.File

/** Zguh = MediaProjection ile tek karelik, DRM davranışını teşhis eden test ekranı. */
class ProjectionProbeActivity : Activity() {
    private lateinit var resultText: TextView
    private lateinit var preview: ImageView
    private var receiverRegistered = false
    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            val file = intent.getStringExtra(ProjectionProbeService.EXTRA_FILE)?.let(::File)
            val black = intent.getBooleanExtra(ProjectionProbeService.EXTRA_BLACK, true)
            if (file != null && file.exists()) {
                preview.setImageURI(Uri.fromFile(file))
                preview.visibility = ImageView.VISIBLE
                resultText.text = if (black) "Kare geldi · siyah içerik" else "Kare geldi · görüntü var"
                resultText.setTextColor(if (black) Color.rgb(255, 205, 92) else Color.rgb(62, 230, 160))
                setResult(RESULT_OK, Intent().putExtra(ProjectionProbeService.EXTRA_FILE, file.absolutePath).putExtra(ProjectionProbeService.EXTRA_BLACK, black))
            } else {
                resultText.text = "Kare alınamadı. Tekrar deneyin."
                setResult(RESULT_CANCELED)
            }
            finish()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.setBackgroundDrawableResource(android.R.color.transparent)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER
            setPadding(48, 32, 48, 32); setBackgroundColor(Color.rgb(11, 15, 20))
        }
        root.addView(TextView(this).apply {
            text = "Ekran yakalama testi"; textSize = 30f; typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.rgb(61, 220, 151)); gravity = Gravity.CENTER
        })
        root.addView(TextView(this).apply {
            text = "İzin verildikten sonra tek kare alınır. DRM korumalı ya da HDMI görüntüsü siyah gelebilir; bu normaldir."
            textSize = 20f; setTextColor(Color.WHITE); gravity = Gravity.CENTER
            setPadding(10, 14, 10, 14)
        })
        resultText = TextView(this).apply {
            text = "Önce TV'deki YouTube, film uygulaması veya HDMI kaynağına geçin."
            textSize = 20f; setTextColor(Color.rgb(138, 151, 166)); gravity = Gravity.CENTER
            setPadding(10, 12, 10, 12)
        }
        root.addView(resultText)
        preview = ImageView(this).apply {
            visibility = ImageView.GONE; scaleType = ImageView.ScaleType.FIT_CENTER
            setBackgroundColor(Color.BLACK); contentDescription = "MediaProjection test karesi"
        }
        root.addView(preview, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
        root.addView(Button(this).apply {
            text = "Tek kare yakala"; textSize = 21f; isAllCaps = false
            setOnClickListener { startConsent() }
        })
        root.addView(Button(this).apply {
            text = "Geri"; textSize = 20f; isAllCaps = false; setOnClickListener { finish() }
        })
        setContentView(root)
    }

    override fun onStart() {
        super.onStart()
        if (!receiverRegistered) {
            val filter = IntentFilter(ProjectionProbeService.ACTION_RESULT)
            if (Build.VERSION.SDK_INT >= 33) registerReceiver(receiver, filter, Context.RECEIVER_NOT_EXPORTED) else registerReceiver(receiver, filter)
            receiverRegistered = true
        }
    }

    override fun onStop() {
        if (receiverRegistered) { unregisterReceiver(receiver); receiverRegistered = false }
        super.onStop()
    }

    @Suppress("DEPRECATION")
    private fun startConsent() {
        val manager = getSystemService(android.media.projection.MediaProjectionManager::class.java)
        startActivityForResult(manager.createScreenCaptureIntent(), REQUEST_CAPTURE)
    }

    @Deprecated("Android TV screen capture result callback")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != REQUEST_CAPTURE) return
        if (resultCode != RESULT_OK || data == null) {
            resultText.text = "Ekran yakalama izni verilmedi."
            return
        }
        val service = Intent(this, ProjectionProbeService::class.java)
            .putExtra(ProjectionProbeService.EXTRA_RESULT_CODE, resultCode)
            .putExtra(ProjectionProbeService.EXTRA_RESULT_DATA, data)
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(service) else startService(service)
        resultText.text = "Kare bekleniyor…"
        preview.visibility = ImageView.GONE
    }

    companion object { private const val REQUEST_CAPTURE = 811 }
}

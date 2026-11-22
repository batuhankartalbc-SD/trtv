package com.trtv

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.os.Build
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

/** Zguh = MediaProjection ile tek karelik, DRM davranışını teşhis eden test ekranı. */
class ProjectionProbeActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.setBackgroundDrawableResource(android.R.color.transparent)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER
            setPadding(48, 32, 48, 32); setBackgroundColor(Color.argb(170, 11, 15, 20))
        }
        root.addView(TextView(this).apply {
            text = "Tek kare ekran yakalama testi"; textSize = 26f; typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.rgb(61, 220, 151)); gravity = Gravity.CENTER
        })
        root.addView(TextView(this).apply {
            text = "İzin verdikten sonra Brolis kapanır ve önceki TV uygulamasına dönersiniz. Yaklaşık bir saniye sonra kare alınır. Sonucu görmek için Tanılama'yı yeniden açın."
            textSize = 20f; setTextColor(Color.WHITE); gravity = Gravity.CENTER
            setPadding(10, 14, 10, 14)
        })
        root.addView(Button(this).apply {
            text = "Tek kare yakala"; textSize = 21f; isAllCaps = false
            setOnClickListener { startConsent() }
        })
        root.addView(Button(this).apply {
            text = "Geri"; textSize = 20f; isAllCaps = false; setOnClickListener { finish() }
        })
        setContentView(root)
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
            setContentView(TextView(this).apply {
                text = "Ekran yakalama izni verilmedi. Geri ile tanılamaya dönün."
                textSize = 22f; setTextColor(Color.WHITE); gravity = Gravity.CENTER
                setPadding(48, 32, 48, 32)
                setBackgroundColor(Color.argb(170, 11, 15, 20))
            })
            return
        }
        val service = Intent(this, ProjectionProbeService::class.java)
            .putExtra(ProjectionProbeService.EXTRA_RESULT_CODE, resultCode)
            .putExtra(ProjectionProbeService.EXTRA_RESULT_DATA, data)
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(service) else startService(service)
        finishAffinity()
    }

    companion object { private const val REQUEST_CAPTURE = 811 }
}

package com.trtv

import android.app.Activity
import android.app.PendingIntent
import android.content.Intent
import android.content.IntentFilter
import android.content.BroadcastReceiver
import android.content.Context
import android.content.pm.PackageInstaller
import android.graphics.Color
import android.graphics.Typeface
import android.net.ConnectivityManager
import android.net.Uri
import android.os.Build
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
import java.io.File
import java.net.HttpURLConnection
import java.net.Inet4Address
import java.net.URL

/** Durum ekranı. Servisi başlatır; "Oyuna dön" ile kapanır. */
class MainActivity : Activity() {
    private lateinit var rootView: LinearLayout
    private lateinit var info: TextView
    private lateinit var updateButton: Button
    private lateinit var calibrateButton: Button
    private val h = Handler(Looper.getMainLooper())
    private var downloading = false
    private var awaitingSourcePermission = false
    private var receiverRegistered = false
    private var onboardingLaunchedThisSession = false
    private val updateReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) { refreshUpdateButton() }
    }
    private val tick = object : Runnable {
        override fun run() { refresh(); refreshUpdateButton(); h.postDelayed(this, 1000) }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        rootView = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setBackgroundColor(Color.TRANSPARENT)
            setPadding(80, 44, 80, 44)
        }
        rootView.addView(TextView(this).apply {
            text = "Brolis Game Translate"; textSize = 40f; setTextColor(Color.rgb(61, 220, 151)); typeface = Typeface.DEFAULT_BOLD
        })
        rootView.addView(TextView(this).apply {
            text = "Bilgisayardaki TRÇeviri'nin çevirilerini oyun görüntüsünün üstünde gösterir."
            textSize = 18f; setTextColor(Color.rgb(225, 232, 230)); setPadding(18, 12, 18, 20)
            setBackgroundColor(Color.argb(170, 13, 17, 16))
        })
        info = TextView(this).apply { textSize = 21f; setTextColor(Color.WHITE); setLineSpacing(8f, 1f) }
        info.setPadding(18, 14, 18, 14)
        info.setBackgroundColor(Color.argb(185, 13, 17, 16))
        rootView.addView(info)
        calibrateButton = Button(this).apply {
            text = "Kumandayla hizala"; textSize = 20f
            setOnClickListener { rootView.visibility = android.view.View.INVISIBLE; startActivity(Intent(this@MainActivity, CalibrateActivity::class.java)) }
        }
        rootView.addView(calibrateButton, buttonParams())
        rootView.addView(Button(this).apply {
            text = "Ayarlar"; textSize = 20f
            setOnClickListener { rootView.visibility = android.view.View.INVISIBLE; startActivity(Intent(this@MainActivity, SettingsActivity::class.java)) }
        }, buttonParams())
        rootView.addView(Button(this).apply {
            text = "Konuşma geçmişi"; textSize = 20f
            setOnClickListener { rootView.visibility = android.view.View.INVISIBLE; startActivity(Intent(this@MainActivity, HistoryActivity::class.java)) }
        }, buttonParams())
        rootView.addView(Button(this).apply {
            text = "Tanılama"; textSize = 20f
            setOnClickListener { rootView.visibility = android.view.View.INVISIBLE; startActivity(Intent(this@MainActivity, DiagnosticsActivity::class.java)) }
        }, buttonParams())
        rootView.addView(Button(this).apply {
            text = "Yardım"; textSize = 20f
            setOnClickListener { rootView.visibility = android.view.View.INVISIBLE; startActivity(Intent(this@MainActivity, HelpActivity::class.java)) }
        }, buttonParams())
        rootView.addView(Button(this).apply {
            text = "Rehberi tekrar göster"; textSize = 20f
            setOnClickListener { openOnboarding() }
        }, buttonParams())
        updateButton = Button(this).apply {
            textSize = 20f; visibility = android.view.View.GONE
            setOnClickListener { updateApp() }
        }
        rootView.addView(updateButton, buttonParams())
        val back = Button(this).apply { text = "Oyuna dön"; textSize = 20f; setOnClickListener { finish() } }
        rootView.addView(back, buttonParams())
        val screen = ScrollView(this).apply { isFillViewport = true; isFocusable = false }
        screen.addView(rootView, ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        setContentView(screen)
        back.requestFocus()
        handleInstallResult(intent)
    }

    private fun buttonParams() = LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply { topMargin = 14 }

    override fun onResume() {
        super.onResume()
        OverlayService.suppressOverlayUi(true)
        if (::rootView.isInitialized) rootView.visibility = android.view.View.VISIBLE
        val onboardingPending = !getSharedPreferences("settings", MODE_PRIVATE).getBoolean("onboarding_done", false)
        if (onboardingPending) {
            if (!onboardingLaunchedThisSession) openOnboarding()
            if (Settings.canDrawOverlays(this)) OverlayService.start(this)
            h.removeCallbacks(tick)
            return
        }
        if (Settings.canDrawOverlays(this)) OverlayService.start(this) else try {
            startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")))
        } catch (_: Exception) { }
        if (!receiverRegistered) {
            val filter = IntentFilter(OverlayService.UPDATE_ACTION)
            if (Build.VERSION.SDK_INT >= 33) registerReceiver(updateReceiver, filter, Context.RECEIVER_NOT_EXPORTED) else registerReceiver(updateReceiver, filter)
            receiverRegistered = true
        }
        refreshUpdateButton()
        if (awaitingSourcePermission && (Build.VERSION.SDK_INT < 26 || packageManager.canRequestPackageInstalls())) {
            awaitingSourcePermission = false
            updateApp()
        }
        h.post(tick)
    }

    private fun openOnboarding() {
        onboardingLaunchedThisSession = true
        rootView.visibility = android.view.View.INVISIBLE
        startActivityForResult(Intent(this, OnboardingActivity::class.java), REQUEST_ONBOARDING)
    }

    @Deprecated("Deprecated in Android, kept for API 28 compatibility")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQUEST_ONBOARDING && resultCode == RESULT_OK) finish()
    }

    override fun onPause() {
        h.removeCallbacks(tick)
        OverlayService.suppressOverlayUi(false)
        super.onPause()
    }

    override fun onDestroy() {
        if (receiverRegistered) { unregisterReceiver(updateReceiver); receiverRegistered = false }
        super.onDestroy()
    }

    private fun refreshUpdateButton() {
        val prefs = getSharedPreferences("updates", MODE_PRIVATE)
        val build = prefs.getInt("build", 0)
        updateButton.visibility = if (build > 0) android.view.View.VISIBLE else android.view.View.GONE
        if (build > 0 && !downloading) updateButton.text = "Güncelle (Build $build)"
    }

    private fun updateApp() {
        if (downloading) return
        if (Build.VERSION.SDK_INT >= 26 && !packageManager.canRequestPackageInstalls()) {
            awaitingSourcePermission = true
            try { startActivity(Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:$packageName"))) } catch (_: Exception) { }
            return
        }
        val url = getSharedPreferences("updates", MODE_PRIVATE).getString("url", null)
            ?: "https://github.com/batuhankartalbc-SD/trtv/releases/download/latest/a.apk"
        downloading = true
        updateButton.isEnabled = false
        updateButton.text = "İndiriliyor: %0"
        Thread({
            var conn: HttpURLConnection? = null
            try {
                conn = (URL(url).openConnection() as HttpURLConnection).apply { connectTimeout = 15000; readTimeout = 20000; instanceFollowRedirects = true }
                if (conn.responseCode !in 200..299) throw IllegalStateException("İndirme başarısız")
                val total = conn.contentLengthLong
                val apk = File(cacheDir, "trceviri-update.apk")
                conn.inputStream.use { input -> apk.outputStream().use { output ->
                    val buf = ByteArray(64 * 1024); var done = 0L; var lastPercent = -1
                    while (true) {
                        val n = input.read(buf); if (n < 0) break
                        output.write(buf, 0, n); done += n
                        if (total > 0) {
                            val percent = (done * 100 / total).toInt()
                            if (percent != lastPercent) { lastPercent = percent; runOnUiThread { updateButton.text = "İndiriliyor: %$percent" } }
                        }
                    }
                } }
                installApk(apk)
            } catch (_: Exception) {
                runOnUiThread { downloading = false; updateButton.isEnabled = true; refreshUpdateButton() }
            } finally { conn?.disconnect() }
        }, "trtv-apk-download").start()
    }

    private fun installApk(apk: File) {
        val installer = packageManager.packageInstaller
        val params = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL)
        val sessionId = installer.createSession(params)
        installer.openSession(sessionId).use { session ->
            apk.inputStream().use { input -> session.openWrite("trceviri.apk", 0, apk.length()).use { output ->
                val buf = ByteArray(64 * 1024); while (true) { val n = input.read(buf); if (n < 0) break; output.write(buf, 0, n) }; session.fsync(output)
            } }
            val callback = Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP).putExtra("install_session", sessionId)
            val flags = PendingIntent.FLAG_UPDATE_CURRENT or (if (Build.VERSION.SDK_INT >= 31) PendingIntent.FLAG_MUTABLE else 0)
            session.commit(PendingIntent.getActivity(this, sessionId, callback, flags).intentSender)
        }
        runOnUiThread { updateButton.text = "Kurulum başlatıldı"; updateButton.isEnabled = false }
    }

    /** PackageInstaller sonucu: sistem kullanıcıdan "Yükle" onayı isterse onay ekranını aç. */
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleInstallResult(intent)
    }

    private fun handleInstallResult(intent: Intent?) {
        if (intent == null || !intent.hasExtra(PackageInstaller.EXTRA_STATUS)) return
        when (intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE)) {
            PackageInstaller.STATUS_PENDING_USER_ACTION -> {
                @Suppress("DEPRECATION")
                val confirm = if (Build.VERSION.SDK_INT >= 33) intent.getParcelableExtra(Intent.EXTRA_INTENT, Intent::class.java)
                              else intent.getParcelableExtra<Intent>(Intent.EXTRA_INTENT)
                if (confirm != null) try { startActivity(confirm.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) } catch (_: Exception) { }
            }
            PackageInstaller.STATUS_SUCCESS -> {
                getSharedPreferences("updates", MODE_PRIVATE).edit().putInt("build", 0).apply()
                downloading = false; updateButton.text = "Güncellendi ✓"
            }
            else -> {
                downloading = false; updateButton.isEnabled = true
                updateButton.text = "Kurulum başarısız — tekrar dene"
            }
        }
    }

    private fun ip(): String {
        val cm = getSystemService(ConnectivityManager::class.java)
        val lp = cm.getLinkProperties(cm.activeNetwork) ?: return "?"
        return lp.linkAddresses.map { it.address }.firstOrNull { it is Inet4Address }?.hostAddress ?: "?"
    }

    companion object { private const val REQUEST_ONBOARDING = 804 }

    private fun refresh() {
        val perm = Settings.canDrawOverlays(this)
        val tvAddress = ip()
        val pcConnected = OverlayService.isComputerConnected()
        info.text = buildString {
            append(if (perm) "✔ Ekran üstü izni var\n" else "✘ Ekran üstü izni YOK — ayarlardan TRÇeviri TV'ye izin verin\n")
            append("• Durum: ${OverlayService.status}\n")
            if (pcConnected) append("• TV IP: $tvAddress · port ${OverlayService.PORT}\n\n")
            else append("• PC bekleniyor… IP: $tvAddress port ${OverlayService.PORT}\n\n")
            append("Bilgisayarda TRÇeviri'yi açın; TV'yi kendisi bulup bağlanır.\n")
            append("Bağlandıktan sonra 'Oyuna dön'e basıp PS5 girişine geçin.")
        }
    }
}

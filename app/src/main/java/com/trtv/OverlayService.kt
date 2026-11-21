package com.trtv

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.PixelFormat
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.provider.Settings
import android.util.Log
import android.view.WindowManager
import org.json.JSONObject
import java.io.BufferedWriter
import java.net.HttpURLConnection
import java.net.InetSocketAddress
import java.net.URL
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import kotlin.concurrent.thread

/**
 * Bilgisayardaki TRÇeviri buraya bağlanır (TCP 47800, satır başına bir JSON) ve
 * çevirileri gönderir; bu servis onları HDMI görüntüsünün üstündeki katmana çizer.
 * Katman odak almaz ve dokunulmaz: kumanda tuşları oyuna / TV'ye gitmeye devam eder.
 */
class OverlayService : Service() {
    companion object {
        const val PORT = 47800
        const val TAG = "TRCeviriTV"
        @Volatile var status: String = "Başlatılmadı"
        @Volatile var running = false
        @Volatile private var activeService: OverlayService? = null
        const val UPDATE_ACTION = "com.trtv.UPDATE_AVAILABLE"

        /** Hizalama kumandası ve diğer uygulama mesajları için güvenli TCP gönderimi. */
        fun sendToPc(o: JSONObject): Boolean = activeService?.sendToClient(o) ?: false

        fun start(ctx: Context) {
            val i = Intent(ctx, OverlayService::class.java)
            if (Build.VERSION.SDK_INT >= 26) ctx.startForegroundService(i) else ctx.startService(i)
        }
    }

    private val main = Handler(Looper.getMainLooper())
    private var view: OverlayView? = null
    private var server: ServerSocket? = null
    @Volatile private var client: Socket? = null
    private val writerLock = Any()
    @Volatile private var clientWriter: BufferedWriter? = null
    private val updates = Executors.newSingleThreadScheduledExecutor { r -> Thread(r, "trtv-updates").apply { isDaemon = true } }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        activeService = this
        goForeground()
        running = true
        addOverlay()
        thread(name = "trceviri-server", isDaemon = true) { serve() }
        updates.scheduleAtFixedRate({ checkForUpdate() }, 0, 6, TimeUnit.HOURS)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (view == null) addOverlay()
        return START_STICKY
    }

    override fun onDestroy() {
        running = false
        updates.shutdownNow()
        if (activeService === this) activeService = null
        try { server?.close() } catch (_: Exception) {}
        try { client?.close() } catch (_: Exception) {}
        view?.let { try { (getSystemService(WINDOW_SERVICE) as WindowManager).removeView(it) } catch (_: Exception) {} }
        view = null
        status = "Durduruldu"
        super.onDestroy()
    }

    private fun goForeground() {
        val nm = getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= 26) {
            nm.createNotificationChannel(NotificationChannel("ceviri", "TRÇeviri", NotificationManager.IMPORTANCE_MIN))
        }
        val n: Notification = (if (Build.VERSION.SDK_INT >= 26) Notification.Builder(this, "ceviri") else Notification.Builder(this))
            .setContentTitle("TRÇeviri TV")
            .setContentText("Çeviri katmanı çalışıyor")
            .setSmallIcon(android.R.drawable.ic_menu_info_details)
            .setOngoing(true)
            .build()
        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(1, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
        } else {
            startForeground(1, n)
        }
    }

    private fun addOverlay() {
        if (!Settings.canDrawOverlays(this)) {
            status = "Ekran üstü izni yok"
            return
        }
        val wm = getSystemService(WINDOW_SERVICE) as WindowManager
        val lp = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
                WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS or
                WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED,
            PixelFormat.TRANSLUCENT
        )
        val v = OverlayView(this)
        try {
            wm.addView(v, lp)
            view = v
            if (status == "Başlatılmadı" || status == "Ekran üstü izni yok") status = "Bilgisayar bekleniyor"
        } catch (e: Exception) {
            Log.e(TAG, "katman eklenemedi", e)
            status = "Katman eklenemedi: ${e.message}"
        }
    }

    private fun serve() {
        while (running) {
            try {
                val ss = ServerSocket()
                ss.reuseAddress = true
                ss.bind(InetSocketAddress(PORT))
                server = ss
                while (running) {
                    val s = ss.accept()
                    thread(name = "trceviri-client", isDaemon = true) { handle(s) }
                }
            } catch (e: Exception) {
                if (!running) return
                Log.w(TAG, "sunucu hatası, yeniden deneniyor", e)
                Thread.sleep(1500)
            }
        }
    }

    private fun send(w: BufferedWriter, o: JSONObject) {
        synchronized(w) { w.write(o.toString()); w.write("\n"); w.flush() }
    }

    private fun sendToClient(o: JSONObject): Boolean = synchronized(writerLock) {
        val w = clientWriter ?: return@synchronized false
        try { send(w, o); true } catch (_: Exception) { false }
    }

    private fun checkForUpdate() {
        var c: HttpURLConnection? = null
        try {
            c = (URL("https://api.github.com/repos/batuhankartalbc-SD/trtv/releases/tags/latest").openConnection() as HttpURLConnection).apply {
                connectTimeout = 8000; readTimeout = 8000; requestMethod = "GET"
                setRequestProperty("Accept", "application/vnd.github+json")
                setRequestProperty("User-Agent", "TRCeviri-TV")
            }
            if (c.responseCode !in 200..299) return
            val json = JSONObject(c.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() })
            val build = Regex("Build\\s+(\\d+)", RegexOption.IGNORE_CASE).find(json.optString("name"))?.groupValues?.get(1)?.toIntOrNull() ?: return
            val installed = if (Build.VERSION.SDK_INT >= 28) packageManager.getPackageInfo(packageName, 0).longVersionCode.toInt() else packageManager.getPackageInfo(packageName, 0).versionCode
            if (build <= installed) return
            val assets = json.optJSONArray("assets")
            val apkUrl = (0 until (assets?.length() ?: 0)).mapNotNull { assets?.optJSONObject(it) }
                .firstOrNull { it.optString("name") == "a.apk" }?.optString("browser_download_url")
                ?.takeIf { it.startsWith("https://") }
                ?: "https://github.com/batuhankartalbc-SD/trtv/releases/download/latest/a.apk"
            getSharedPreferences("updates", MODE_PRIVATE).edit().putInt("build", build).putString("url", apkUrl).apply()
            main.post { view?.banner("Güncelleme var — TRÇeviri TV'yi açıp Güncelle'ye basın", 6000L) }
            sendBroadcast(Intent(UPDATE_ACTION).setPackage(packageName).putExtra("build", build))
        } catch (e: Exception) { Log.i(TAG, "güncelleme denetimi atlandı: ${e.message}") }
        finally { c?.disconnect() }
    }

    private fun handle(s: Socket) {
        var isMain = false
        try {
            s.tcpNoDelay = true
            s.soTimeout = 10000
            val r = s.getInputStream().bufferedReader(Charsets.UTF_8)
            val w = s.getOutputStream().bufferedWriter(Charsets.UTF_8)
            while (running) {
                val line = r.readLine() ?: break
                if (line.isBlank()) continue
                val o = JSONObject(line)
                when (o.optString("t")) {
                    "hello" -> {
                        val dm = resources.displayMetrics
                        send(w, JSONObject().put("t", "hello").put("app", "trceviri-tv").put("v", 1)
                            .put("w", dm.widthPixels).put("h", dm.heightPixels).put("overlay", view != null))
                        if (o.optBoolean("probe")) break   // sadece tarama
                        val old = client
                        synchronized(writerLock) { client = s; clientWriter = w }
                        isMain = true
                        if (old != null && old !== s) try { old.close() } catch (_: Exception) {}
                        val name = o.optString("name", "Bilgisayar")
                        status = "Bağlı: $name"
                        main.post { if (view == null) addOverlay(); view?.banner("TRÇeviri bağlandı ($name)") }
                    }
                    "style" -> main.post { view?.setStyle(o) }
                    "items" -> {
                        val z = o.optString("z", "auto")
                        val items = OverlayView.parseItems(o.optJSONArray("items"))
                        main.post { view?.setItems(z, items) }
                    }
                    "clear" -> main.post { view?.clearAll() }
                    "visible" -> { val vis = o.optBoolean("v", true); main.post { view?.setShown(vis) } }
                    "ping" -> send(w, JSONObject().put("t", "pong"))
                }
            }
        } catch (e: Exception) {
            Log.i(TAG, "bağlantı kapandı: ${e.message}")
        } finally {
            try { s.close() } catch (_: Exception) {}
            if (isMain && client === s) {
                synchronized(writerLock) { if (client === s) { client = null; clientWriter = null } }
                status = "Bilgisayar bekleniyor"
                main.post { view?.clearAll() }
            }
        }
    }
}

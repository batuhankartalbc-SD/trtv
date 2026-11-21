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
import java.net.InetSocketAddress
import java.net.ServerSocket
import java.net.Socket
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

        fun start(ctx: Context) {
            val i = Intent(ctx, OverlayService::class.java)
            if (Build.VERSION.SDK_INT >= 26) ctx.startForegroundService(i) else ctx.startService(i)
        }
    }

    private val main = Handler(Looper.getMainLooper())
    private var view: OverlayView? = null
    private var server: ServerSocket? = null
    @Volatile private var client: Socket? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        goForeground()
        running = true
        addOverlay()
        thread(name = "trceviri-server", isDaemon = true) { serve() }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (view == null) addOverlay()
        return START_STICKY
    }

    override fun onDestroy() {
        running = false
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
                        client = s
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
                client = null
                status = "Bilgisayar bekleniyor"
                main.post { view?.clearAll() }
            }
        }
    }
}

package com.trtv

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.BroadcastReceiver
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.ServiceInfo
import android.graphics.PixelFormat
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.SystemClock
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

data class TvSettings(
    val visible: Boolean = true,
    val scale: Double = 1.1,
    val bgm: String = "black",
    val opacity: Int = 100,
    val speakerColors: Boolean = true,
    val tts: Boolean = false,
    val dialogue: Boolean = true,
    val menu: Boolean = true,
    val controls: Boolean = true,
    val other: Boolean = true,
    val nav: Boolean = false,
    val output: String = "tv",
    val profiles: List<String> = emptyList(),
    val profile: String = "",
    val engine: String = "local",
    val engines: List<String> = emptyList(),
    val font: String = "default",
    val fonts: List<String> = emptyList(),
    val pcVersion: String = "—",
    val geminiStatus: String = "—",
    val pcEngine: String = "—",
    val pcProfile: String = "—",
    val fps: Int = 20,
    val instant: Boolean = false,
    /** true: PC tüm ekranı tarar; false: yalnızca profilde çizilen bölgeler. */
    val autoMode: Boolean = true
)

data class DiagnosticsSnapshot(
    val connected: Boolean,
    val computerName: String,
    val lastMessageSeconds: Double?,
    val itemsLast10Seconds: Int,
    val visibleBoxes: Int,
    val width: Int,
    val height: Int,
    val density: Float,
    val dx: Float,
    val dy: Float,
    val sx: Float,
    val sy: Float,
    val lastDrawMs: Float
)

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
        const val SETTINGS_ACTION = "com.trtv.SETTINGS_CHANGED"
        private const val HISTORY_LIMIT = 50
        fun toggleFilmShown(): Boolean = activeService?.toggleFilmShownInternal() ?: false

        /** Hizalama kumandası ve diğer uygulama mesajları için güvenli TCP gönderimi. */
        fun sendToPc(o: JSONObject): Boolean = activeService?.sendToClient(o) ?: false
        fun currentSettings(): TvSettings = activeService?.settingsSnapshot() ?: TvSettings()
        fun historySnapshot(): List<HistoryEntry> = activeService?.historySnapshotInternal() ?: emptyList()
        fun isComputerConnected(): Boolean = activeService?.isPcConnected() ?: false
        fun diagnosticsSnapshot(): DiagnosticsSnapshot = activeService?.diagnosticsSnapshotInternal()
            ?: DiagnosticsSnapshot(false, "—", null, 0, 0, 0, 0, 1f, 0f, 0f, 1f, 1f, 0f)
        fun changeSetting(key: String, value: Any): Boolean = activeService?.sendSettingToPc(key, value) ?: false
        fun setDisconnectWarning(enabled: Boolean) { activeService?.setConnectionWarningEnabled(enabled) }
        fun suppressOverlayUi(suppressed: Boolean) {
            activeService?.let { service -> service.main.post { service.view?.setUiSuppressed(suppressed) } }
        }

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
    private val historyLock = Any()
    private val diagnosticsLock = Any()
    private val itemMessageTimes = ArrayDeque<Long>()
    private val history = ArrayList<HistoryEntry>()
    private val historyKeys = ArrayList<String>()
    @Volatile private var clientWriter: BufferedWriter? = null
    private val updates = Executors.newSingleThreadScheduledExecutor { r -> Thread(r, "trtv-updates").apply { isDaemon = true } }
    @Volatile private var settings = TvSettings()
    @Volatile private var connected = false
    @Volatile private var computerName = "—"
    @Volatile private var lastMessageAt = 0L
    @Volatile private var alignDx = 0f
    @Volatile private var alignDy = 0f
    @Volatile private var alignSx = 1f
    @Volatile private var alignSy = 1f
    private var lastWarningAt = 0L
    private val warningShow = Runnable { showDisconnectWarning() }
    private val warningHide = Runnable { view?.setConnectionWarning(false) }
    private val warningRepeat = Runnable { showDisconnectWarning() }
    private var localFilmTranslator: LocalFilmTranslator? = null
    @Volatile private var filmShown = true
    private var latestFilmId = 0
    private val filmLinesById = LinkedHashMap<Int, List<FilmLine>>()
    private val filmReplies = TranslationRevisionCache(2000)
    private val filmFallbacks = HashMap<Int, Runnable>()
    private val filmPcTranslations = LinkedHashSet<Int>()
    private val filmReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            when (intent.action) {
                IndependentModeService.ACTION_STABLE_LINES -> handleFilmLines(intent.getStringExtra(IndependentModeService.EXTRA_LINES))
                IndependentModeService.ACTION_CLEAR_FILM -> main.post { view?.clearZoneImmediately("film") }
            }
        }
    }

    fun settingsSnapshot(): TvSettings = settings
    fun isPcConnected(): Boolean = connected

    private fun toggleFilmShownInternal(): Boolean {
        filmShown = !filmShown
        if (!filmShown) main.post { view?.clearZoneImmediately("film") }
        else {
            val id = latestFilmId
            filmReplies[id]?.let { translations ->
                showFilmTranslations(id, translations, if (filmPcTranslations.contains(id)) "PC" else "cihazda")
            }
        }
        return filmShown
    }

    private fun diagnosticsSnapshotInternal(): DiagnosticsSnapshot {
        val now = SystemClock.elapsedRealtime()
        val recentItems = synchronized(diagnosticsLock) {
            while (itemMessageTimes.isNotEmpty() && now - itemMessageTimes.first() > 10_000L) itemMessageTimes.removeFirst()
            itemMessageTimes.size
        }
        val display = resources.displayMetrics
        return DiagnosticsSnapshot(
            connected, computerName,
            if (lastMessageAt == 0L) null else ((now - lastMessageAt).coerceAtLeast(0L) / 1000.0),
            recentItems, view?.visibleItemCount() ?: 0, display.widthPixels, display.heightPixels,
            display.density, alignDx, alignDy, alignSx, alignSy, view?.lastDrawDurationMs() ?: 0f
        )
    }

    private fun historySnapshotInternal(): List<HistoryEntry> = synchronized(historyLock) { history.toList() }

    private fun stringList(o: JSONObject, key: String, fallback: List<String>): List<String> {
        val array = o.optJSONArray(key) ?: return fallback
        return (0 until array.length()).mapNotNull { index -> array.optString(index).trim().takeIf { it.isNotEmpty() } }.distinct()
    }

    private fun recordHistory(zone: String, items: List<OverlayItem>) = synchronized(historyLock) {
        items.filter { it.kind == "subtitle" && it.tr.isNotBlank() }.forEach { item ->
            val incoming = HistoryEntry(item.speaker, item.tr, item.sc)
            val key = "$zone|${item.kind}|${item.speaker.trim().lowercase()}|${item.b.joinToString(",") { (it * 100).toInt().toString() }}"
            val keyedIndex = historyKeys.indexOfLast { it == key }
            if (keyedIndex >= 0 && isSameHistoryLine(history[keyedIndex], incoming)) {
                history[keyedIndex] = incoming
                return@forEach
            }
            val recentSimilar = if (keyedIndex >= 0) null else history.indices.reversed().take(6)
                .firstOrNull { isSameHistoryLine(history[it], incoming) }
            if (recentSimilar != null) {
                history[recentSimilar] = incoming
                historyKeys[recentSimilar] = key
                return@forEach
            }
            history.add(incoming)
            historyKeys.add(key)
            if (history.size > HISTORY_LIMIT) {
                history.removeAt(0)
                historyKeys.removeAt(0)
            }
        }
    }

    fun sendSettingToPc(key: String, value: Any): Boolean {
        settings = applySetting(settings, key, value)
        val message = if (key == "visible") JSONObject().put("t", "visible").put("v", value as Boolean)
            else JSONObject().put("t", "set").put("k", key).put("v", value)
        val ok = clientWriter != null
        if (key == "bg_opacity") main.post { view?.setOverlayOpacity(((value as Number).toInt() * 255 / 100).coerceIn(0, 255)) }
        thread(name = "trtv-setting-send", isDaemon = true) { sendToPc(message) }
        sendBroadcast(Intent(SETTINGS_ACTION).setPackage(packageName))
        return ok
    }

    fun setConnectionWarningEnabled(enabled: Boolean) {
        getSharedPreferences("settings", MODE_PRIVATE).edit().putBoolean("disconnect_warning", enabled).apply()
        main.post {
            if (!enabled) {
                main.removeCallbacks(warningShow); main.removeCallbacks(warningRepeat); main.removeCallbacks(warningHide)
                view?.setConnectionWarning(false)
            } else if (!connected) {
                main.removeCallbacks(warningShow); main.postDelayed(warningShow, 10_000L)
            }
        }
    }

    private fun applySetting(s: TvSettings, key: String, value: Any): TvSettings = when (key) {
        "visible" -> s.copy(visible = value as Boolean)
        "font_scale" -> s.copy(scale = (value as Number).toDouble())
        "bg_mode" -> s.copy(bgm = value as String)
        "bg_opacity" -> s.copy(opacity = (value as Number).toInt().coerceIn(0, 100))
        "speaker_colors_on" -> s.copy(speakerColors = value as Boolean)
        "tts_enabled" -> s.copy(tts = value as Boolean)
        "cat_dialogue" -> s.copy(dialogue = value as Boolean)
        "cat_menu" -> s.copy(menu = value as Boolean)
        "cat_controls" -> s.copy(controls = value as Boolean)
        "cat_other" -> s.copy(other = value as Boolean)
        "cat_nav" -> s.copy(nav = value as Boolean)
        "profile" -> s.copy(profile = value as String)
        "engine" -> s.copy(engine = value as String)
        "font" -> s.copy(font = (value as String).takeIf { it in setOf("default", "condensed", "rounded", "clean") } ?: "default")
        "fps" -> s.copy(fps = (value as Number).toInt().coerceIn(10, 60))
        "instant" -> s.copy(instant = value as Boolean)
        "auto_mode" -> s.copy(autoMode = value as Boolean)
        "output" -> s.copy(output = (value as String).takeIf { it in setOf("pc", "tv", "both") } ?: s.output)
        else -> s
    }

    private fun updateFromStyle(o: JSONObject) {
        val cats = o.optJSONObject("cats")
        val styleOpacity = if (o.has("opacity")) (o.optInt("opacity", 255).coerceIn(0, 255) * 100 / 255) else settings.opacity
        settings = settings.copy(
            scale = o.optDouble("scale", settings.scale), bgm = o.optString("bgm", settings.bgm),
            opacity = styleOpacity,
            tts = o.optBoolean("tts", settings.tts), speakerColors = o.optBoolean("spkcol", settings.speakerColors),
            dialogue = cats?.optBoolean("dialogue", settings.dialogue) ?: settings.dialogue,
            menu = cats?.optBoolean("menu", settings.menu) ?: settings.menu,
            controls = cats?.optBoolean("controls", settings.controls) ?: settings.controls,
            other = cats?.optBoolean("other", settings.other) ?: settings.other,
            nav = cats?.optBoolean("nav", settings.nav) ?: settings.nav,
            output = o.optString("output", settings.output),
            fps = o.optInt("fps", settings.fps).coerceIn(10, 60),
            instant = o.optBoolean("instant", settings.instant),
            autoMode = o.optBoolean("auto", settings.autoMode),
            profiles = stringList(o, "profiles", settings.profiles),
            profile = o.optString("profile", settings.profile),
            engine = o.optString("engine", settings.engine),
            engines = stringList(o, "engines", settings.engines),
            // Eski PC sürümleri font alanı göndermez; varsayılan fontta kal.
            font = o.optString("font", "default").takeIf { it in setOf("default", "condensed", "rounded", "clean") } ?: "default",
            fonts = stringList(o, "fonts", settings.fonts),
            pcVersion = o.optString("pcver", "—").ifBlank { "—" },
            geminiStatus = when {
                !o.has("refine") -> "—"
                o.isNull("refine") -> "Kapalı"
                else -> o.optString("refine", "—").ifBlank { "—" }
            },
            pcEngine = o.optString("engine", "—").ifBlank { "—" },
            pcProfile = o.optString("profile", "—").ifBlank { "—" }
        )
        alignDx = o.optDouble("dx", alignDx.toDouble()).toFloat()
        alignDy = o.optDouble("dy", alignDy.toDouble()).toFloat()
        alignSx = o.optDouble("sx", alignSx.toDouble()).toFloat()
        alignSy = o.optDouble("sy", alignSy.toDouble()).toFloat()
        main.post { sendBroadcast(Intent(SETTINGS_ACTION).setPackage(packageName)) }
    }

    private fun connectionChanged(isConnected: Boolean) {
        connected = isConnected
        main.removeCallbacks(warningShow); main.removeCallbacks(warningRepeat); main.removeCallbacks(warningHide)
        if (isConnected) {
            view?.setConnectionWarning(false)
        } else {
            view?.setConnectionWarning(false)
            main.postDelayed(warningShow, 10_000L)
        }
        sendBroadcast(Intent(SETTINGS_ACTION).setPackage(packageName))
    }

    private fun showDisconnectWarning() {
        if (connected || !getSharedPreferences("settings", MODE_PRIVATE).getBoolean("disconnect_warning", true)) return
        val now = SystemClock.elapsedRealtime()
        if (lastWarningAt != 0L && now - lastWarningAt < 120_000L) {
            main.postDelayed(warningRepeat, 120_000L - (now - lastWarningAt))
            return
        }
        lastWarningAt = now
        view?.setConnectionWarning(true)
        main.postDelayed(warningHide, 5_000L)
        main.postDelayed(warningRepeat, 120_000L)
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        activeService = this
        goForeground()
        val filmFilter = IntentFilter().apply {
            addAction(IndependentModeService.ACTION_STABLE_LINES)
            addAction(IndependentModeService.ACTION_CLEAR_FILM)
        }
        if (Build.VERSION.SDK_INT >= 33) registerReceiver(filmReceiver, filmFilter, Context.RECEIVER_NOT_EXPORTED) else registerReceiver(filmReceiver, filmFilter)
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
        try { unregisterReceiver(filmReceiver) } catch (_: Exception) {}
        localFilmTranslator?.close(); localFilmTranslator = null
        filmFallbacks.values.forEach(main::removeCallbacks); filmFallbacks.clear()
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
            .setContentTitle("Brolis Game Translate")
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
        // FLAG_NOT_TOUCHABLE YOK: Android 12+ dokunulamaz bindirme pencerelerinin opaklığını 0.8'e kısıyor
        // (dumpsys: alpha=0.8) ve simsiyah zemin saydam görünüyordu. TV'de dokunmatik yok; kumanda tuşları
        // FLAG_NOT_FOCUSABLE sayesinde yine alttaki uygulamaya gidiyor.
        val lp = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
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
            main.post { view?.banner("Güncelleme var — Brolis Game Translate'i açıp Güncelle'ye basın", 6000L) }
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
                lastMessageAt = SystemClock.elapsedRealtime()
                val o = JSONObject(line)
                when (o.optString("t")) {
                    "hello" -> {
                        val dm = resources.displayMetrics
                        send(w, JSONObject().put("t", "hello").put("app", "trceviri-tv").put("v", 1)
                            .put("w", dm.widthPixels).put("h", dm.heightPixels).put("overlay", view != null))
                        if (o.optBoolean("probe")) break   // sadece tarama
                        computerName = o.optString("name", "Bilgisayar").ifBlank { "Bilgisayar" }
                        val old = client
                        synchronized(writerLock) { client = s; clientWriter = w }
                        isMain = true
                        if (old != null && old !== s) try { old.close() } catch (_: Exception) {}
                        val name = o.optString("name", "Bilgisayar")
                        status = "Bağlı: $name"
                        main.post { connectionChanged(true); if (view == null) addOverlay(); view?.banner("Brolis Game Translate bağlandı ($name)") }
                    }
                    "items" -> {
                        synchronized(diagnosticsLock) {
                            val now = SystemClock.elapsedRealtime()
                            while (itemMessageTimes.isNotEmpty() && now - itemMessageTimes.first() > 10_000L) itemMessageTimes.removeFirst()
                            itemMessageTimes.addLast(now)
                        }
                        val z = o.optString("z", "auto")
                        val items = OverlayView.parseItems(o.optJSONArray("items"))
                        recordHistory(z, items)
                        main.post { view?.setItems(z, items) }
                    }
                    "clear" -> main.post { view?.clearGameZones() }
                    "style" -> { updateFromStyle(o); main.post { view?.setStyle(o) } }
                    "visible" -> {
                        val vis = o.optBoolean("v", true)
                        settings = settings.copy(visible = vis)
                        main.post { view?.setShown(vis); sendBroadcast(Intent(SETTINGS_ACTION).setPackage(packageName)) }
                    }
                    "ping" -> send(w, JSONObject().put("t", "pong"))
                    "tr" -> receiveFilmTranslation(o)
                }
            }
        } catch (e: Exception) {
            Log.i(TAG, "bağlantı kapandı: ${e.message}")
        } finally {
            try { s.close() } catch (_: Exception) {}
            if (isMain && client === s) {
                synchronized(writerLock) { if (client === s) { client = null; clientWriter = null } }
                status = "Bilgisayar bekleniyor"
                main.post { connectionChanged(false); view?.clearGameZones() }
            }
        }
    }

    private fun handleFilmLines(raw: String?) {
        if (raw.isNullOrBlank() || !IndependentModeService.active) return
        val array = runCatching { org.json.JSONArray(raw) }.getOrNull() ?: return
        val lines = (0 until array.length()).mapNotNull { index ->
            val item = array.optJSONObject(index) ?: return@mapNotNull null
            val bounds = item.optJSONArray("b") ?: return@mapNotNull null
            if (bounds.length() < 4) return@mapNotNull null
            val box = (0..3).map { bounds.optDouble(it, 0.0).toFloat() }
            FilmLine(item.optString("en"), box, item.optDouble("lh", 0.02).toFloat(), item.optString("prefix"), item.optBoolean("effect"))
        }.filter { it.text.isNotBlank() }
        if (lines.isEmpty()) return
        latestFilmId = maxOf(SystemClock.elapsedRealtime().toInt(), latestFilmId + 1, 1)
        val id = latestFilmId
        main.post { view?.clearZoneImmediately("film") }
        filmLinesById[id] = lines
        while (filmLinesById.size > 2000) filmLinesById.remove(filmLinesById.keys.first())
        val ocrLines = org.json.JSONArray()
        lines.forEach { line ->
            ocrLines.put(JSONObject().put("en", line.text).put("b", org.json.JSONArray(line.box)).put("lh", line.lineHeight))
        }
        val message = JSONObject().put("t", "ocr").put("id", id).put("src", "film").put("lines", ocrLines)
        if (isPcConnected() && sendToClient(message)) {
            IndependentModeService.translationSource = "PC"
            val fallback = Runnable {
                filmFallbacks.remove(id)
                if (id == latestFilmId && filmReplies[id] == null) translateFilmLocally(id)
            }
            filmFallbacks[id] = fallback
            main.postDelayed(fallback, 600L)
            IndependentModeService.publishExternalStatus("PC yanıtı bekleniyor")
        } else translateFilmLocally(id)
    }

    private fun receiveFilmTranslation(o: JSONObject) {
        val id = o.optInt("id", -1)
        val array = o.optJSONArray("tr") ?: return
        val translations = (0 until array.length()).map { array.optString(it) }
        val changed = filmReplies.put(id, translations)
        filmPcTranslations.add(id)
        while (filmPcTranslations.size > 2000) filmPcTranslations.remove(filmPcTranslations.first())
        filmFallbacks.remove(id)?.let(main::removeCallbacks)
        if (changed && id == latestFilmId) showFilmTranslations(id, translations, "PC")
    }

    private fun translateFilmLocally(id: Int) {
        val lines = filmLinesById[id] ?: return
        if (id != latestFilmId) return
        IndependentModeService.translationSource = "cihazda"
        val translator = localFilmTranslator ?: LocalFilmTranslator(applicationContext).also { localFilmTranslator = it }
        translator.translate(lines) { translations, error ->
            if (error != null || translations == null) {
                if (filmPcTranslations.contains(id)) return@translate
                IndependentModeService.publishExternalStatus("Cihaz çevirisi hazır değil · Wi‑Fi ile modeli indirin")
                return@translate
            }
            if (filmPcTranslations.contains(id)) return@translate
            if (id != latestFilmId) return@translate
            filmReplies.put(id, translations)
            showFilmTranslations(id, translations, "cihazda")
        }
        IndependentModeService.publishExternalStatus(translator.state)
    }

    private fun showFilmTranslations(id: Int, translations: List<String>, source: String) {
        val lines = filmLinesById[id] ?: return
        if (id != latestFilmId || !filmShown) return
        IndependentModeService.translationSource = source
        val items = lines.mapIndexedNotNull { index, line ->
            val translated = translations.getOrNull(index)?.trim().orEmpty()
            if (translated.isBlank()) return@mapIndexedNotNull null
            val x = line.box[0].coerceIn(0f, 0.999f)
            val y = line.box[1].coerceIn(0f, 0.999f)
            val w = line.box[2].coerceIn(0.001f, 1f - x)
            val h = line.box[3].coerceIn(0.001f, 1f - y)
            OverlayItem(listOf(x, y, x + w, y + h), line.lineHeight, "", line.formatted(translated), "film", 1, null, null, null, "c")
        }
        recordHistory("film", items)
        main.post { view?.setItems("film", items) }
        val engine = currentSettings().geminiStatus.takeIf { source == "PC" && !it.equals("Kapalı", true) && it != "—" }
            ?.let { "PC ($it)" } ?: source
        IndependentModeService.publishExternalStatus("Çeviri: $engine")
    }
}

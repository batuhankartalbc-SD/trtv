package com.trtv

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.Image
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.media.session.MediaSession
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.IBinder
import android.os.SystemClock
import android.view.KeyEvent
import android.util.Log
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import org.json.JSONArray
import org.json.JSONObject
import java.nio.ByteBuffer
import kotlin.math.max

/** TV'de film altyazısını 5 FPS yakalayıp Latin OCR yapan foreground service. */
class IndependentModeService : Service() {
    private var projection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var reader: ImageReader? = null
    private var worker: HandlerThread? = null
    private var workerHandler: Handler? = null
    private var mediaSession: MediaSession? = null
    private val recognizer by lazy { TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS) }
    private val stability = StableFilmLines(2)
    private var lastFrameAt = 0L
    private var awaitingCleanFrame = false
    private var cleanFrameAfter = 0L
    private var lastSummary = Long.MIN_VALUE
    private var latestRecognized = emptyList<FilmLine>()
    private var lastSentKey: List<String>? = null
    private var subtitleVisible = false
    private var bandPercent = 35
    private var lastSubtitleAt = 0L
    private val clearTask = Runnable {
        if (SystemClock.elapsedRealtime() - lastSubtitleAt >= CLEAR_DELAY_MS) {
            sendBroadcast(Intent(ACTION_CLEAR_FILM).setPackage(packageName))
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            getSharedPreferences(PREFS, MODE_PRIVATE).edit().putBoolean(KEY_ENABLED, false).apply()
            stopSelf(startId)
            return START_NOT_STICKY
        }
        val resultCode = intent?.getIntExtra(EXTRA_RESULT_CODE, 0) ?: 0
        val resultData = intent?.let { readParcelableIntent(it, EXTRA_RESULT_DATA) }
        if (resultCode == 0 || resultData == null) { stopSelf(startId); return START_NOT_STICKY }
        startProjectionForeground()
        try {
            val manager = getSystemService(MediaProjectionManager::class.java)
            projection = manager.getMediaProjection(resultCode, resultData)
            startCapture()
        } catch (error: Exception) {
            Log.e(TAG, "Bağımsız mod başlatılamadı", error)
            publishStatus("Ekran yakalama başlatılamadı")
            stopSelf(startId)
        }
        return START_NOT_STICKY // Projection token'ı yeniden başlatılamaz; kullanıcıdan tekrar izin alınmalı.
    }

    private fun startCapture() {
        val metrics = resources.displayMetrics
        val width = metrics.widthPixels.coerceAtLeast(1)
        val height = metrics.heightPixels.coerceAtLeast(1)
        bandPercent = getSharedPreferences(PREFS, MODE_PRIVATE).getInt(KEY_BAND, 35).coerceIn(35, 100)
        worker = HandlerThread("brolis-film-ocr").also { it.start() }
        workerHandler = Handler(worker!!.looper)
        reader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)
        reader!!.setOnImageAvailableListener({ source -> onImage(source) }, workerHandler)
        projection?.registerCallback(object : MediaProjection.Callback() {
            override fun onStop() { stopSelf() }
        }, workerHandler)
        virtualDisplay = projection?.createVirtualDisplay(
            "Brolis film OCR", width, height, metrics.densityDpi,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR, reader!!.surface, null, workerHandler
        )
        active = true
        enableSubtitleRemoteShortcut()
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putBoolean(KEY_ENABLED, true).apply()
        publishStatus("Altyazı bandı yakalanıyor")
    }

    private fun onImage(source: ImageReader) {
        val now = SystemClock.elapsedRealtime()
        bandPercent = getSharedPreferences(PREFS, MODE_PRIVATE).getInt(KEY_BAND, bandPercent).coerceIn(35, 100)
        val interval = 200L // 5 FPS (hedef aralık 4–6 FPS)
        if (awaitingCleanFrame) {
            if (now < cleanFrameAfter) return
            awaitingCleanFrame = false
            lastFrameAt = now
            OverlayService.suppressOverlayUi(false)
        } else {
            if (now - lastFrameAt < interval) return
            awaitingCleanFrame = true
            cleanFrameAfter = now + 40L
            OverlayService.suppressOverlayUi(true)
            return
        }
        val image = try { source.acquireLatestImage() } catch (_: Exception) { null } ?: return
        try {
            val full = imageToBitmap(image) ?: return
            val frameWidth = image.width
            val frameHeight = image.height
            val cropTop = (full.height * (100 - bandPercent) / 100).coerceIn(0, full.height - 1)
            val crop = Bitmap.createBitmap(full, 0, cropTop, full.width, full.height - cropTop)
            if (crop !== full) full.recycle()
            val summary = grayscaleSummary(crop)
            if (summary == lastSummary) {
                crop.recycle()
                onRecognized(latestRecognized)
                return
            }
            lastSummary = summary
            val started = SystemClock.elapsedRealtime()
            recognizer.process(InputImage.fromBitmap(crop, 0))
                .addOnSuccessListener { text ->
                    val lines = text.textBlocks.flatMap { it.lines }.mapNotNull { line ->
                        val bounds = line.boundingBox ?: return@mapNotNull null
                        val cleaned = cleanFilmLine(line.text) ?: return@mapNotNull null
                        val x = bounds.left.toFloat() / frameWidth
                        val y = (bounds.top.toFloat() + cropTop) / frameHeight
                        val w = bounds.width().toFloat() / frameWidth
                        val h = bounds.height().toFloat() / frameHeight
                        FilmLine(cleaned.english, listOf(x, y, w, h), max(0.008f, h), cleaned.dialoguePrefix, cleaned.effect)
                    }
                    val latency = SystemClock.elapsedRealtime() - started
                    crop.recycle()
                    workerHandler?.post {
                        latestRecognized = lines
                        ocrLatencyMs = latency
                        onRecognized(lines)
                    }
                }
                .addOnFailureListener { error ->
                    Log.w(TAG, "Film altyazısı OCR hatası", error)
                    crop.recycle()
                    workerHandler?.post { latestRecognized = emptyList(); onRecognized(emptyList()) }
                }
        } catch (error: Exception) {
            Log.w(TAG, "Yakalanan kare işlenemedi", error)
        } finally { image.close() }
    }

    private fun onRecognized(lines: List<FilmLine>) {
        val stable = stability.accept(lines)
        if (stable.isEmpty()) {
            if (lines.isEmpty() && subtitleVisible) {
                subtitleVisible = false
                lastSentKey = null
                scheduleClear()
            } else if (lines.isNotEmpty()) workerHandler?.removeCallbacks(clearTask)
            return
        }
        val stableKey = filmLineSetKey(stable)
        if (stableKey == lastSentKey) return
        lastSentKey = stableKey
        subtitleVisible = true
        lastSubtitleAt = SystemClock.elapsedRealtime()
        workerHandler?.removeCallbacks(clearTask)
        val array = JSONArray()
        stable.forEach { line ->
            array.put(JSONObject().put("en", line.text).put("b", JSONArray(line.box)).put("lh", line.lineHeight)
                .put("prefix", line.prefix).put("effect", line.effect))
        }
        sendBroadcast(Intent(ACTION_STABLE_LINES).setPackage(packageName).putExtra(EXTRA_LINES, array.toString()))
    }

    private fun scheduleClear() {
        workerHandler?.removeCallbacks(clearTask)
        workerHandler?.postDelayed(clearTask, CLEAR_DELAY_MS)
    }

    /** TV kumandasında altyazı tuşu varsa bağımsız çeviriyi hızlıca gösterip gizler. */
    private fun enableSubtitleRemoteShortcut() {
        mediaSession?.release()
        mediaSession = MediaSession(this, "BrolisFilmMode").apply {
            setFlags(MediaSession.FLAG_HANDLES_MEDIA_BUTTONS)
            setCallback(object : MediaSession.Callback() {
                override fun onMediaButtonEvent(mediaButtonIntent: Intent): Boolean {
                    @Suppress("DEPRECATION")
                    val event = mediaButtonIntent.getParcelableExtra(Intent.EXTRA_KEY_EVENT) as? KeyEvent ?: return false
                    if (event.action != KeyEvent.ACTION_DOWN || event.repeatCount != 0 ||
                        event.keyCode != KeyEvent.KEYCODE_CAPTIONS) return false
                    val shown = OverlayService.toggleFilmShown()
                    publishStatus(if (shown) "Altyazı çevirisi açık" else "Altyazı çevirisi gizli")
                    return true
                }
            })
            isActive = true
        }
    }

    private fun imageToBitmap(image: Image): Bitmap? {
        val plane = image.planes.firstOrNull() ?: return null
        val pixelStride = plane.pixelStride
        val rowPadding = plane.rowStride - pixelStride * image.width
        val paddedWidth = image.width + rowPadding / pixelStride
        val padded = Bitmap.createBitmap(paddedWidth, image.height, Bitmap.Config.ARGB_8888)
        val buffer: ByteBuffer = plane.buffer
        buffer.rewind(); padded.copyPixelsFromBuffer(buffer)
        val full = Bitmap.createBitmap(padded, 0, 0, image.width, image.height)
        if (padded !== full) padded.recycle()
        return full
    }

    /** Small grayscale thumbnail hash skips OCR on an unchanged frame. */
    private fun grayscaleSummary(bitmap: Bitmap): Long {
        var hash = -3750763034362895579L
        val sx = (bitmap.width / 24).coerceAtLeast(1)
        val sy = (bitmap.height / 12).coerceAtLeast(1)
        for (y in 0 until bitmap.height step sy) for (x in 0 until bitmap.width step sx) {
            val p = bitmap.getPixel(x, y)
            val gray = (77 * ((p shr 16) and 255) + 150 * ((p shr 8) and 255) + 29 * (p and 255)) shr 8
            hash = (hash xor gray.toLong()) * 1099511628211L
        }
        return hash
    }

    private fun startProjectionForeground() {
        val manager = getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= 26) manager.createNotificationChannel(NotificationChannel(CHANNEL, "Bağımsız çeviri", NotificationManager.IMPORTANCE_LOW))
        val note = (if (Build.VERSION.SDK_INT >= 26) Notification.Builder(this, CHANNEL) else Notification.Builder(this))
            .setSmallIcon(android.R.drawable.ic_menu_view).setContentTitle("Brolis bağımsız mod")
            .setContentText("Altyazı bandı yerel olarak okunuyor").setOngoing(true).build()
        if (Build.VERSION.SDK_INT >= 29) startForeground(3, note, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION)
        else startForeground(3, note)
    }

    private fun publishStatus(text: String) {
        statusText = text
        sendBroadcast(Intent(ACTION_STATUS).setPackage(packageName).putExtra(EXTRA_STATUS, text))
    }

    private fun release() {
        active = false
        awaitingCleanFrame = false
        workerHandler?.removeCallbacksAndMessages(null)
        try { virtualDisplay?.release() } catch (_: Exception) {}; virtualDisplay = null
        try { reader?.close() } catch (_: Exception) {}; reader = null
        try { projection?.stop() } catch (_: Exception) {}; projection = null
        try { mediaSession?.isActive = false; mediaSession?.release() } catch (_: Exception) {}; mediaSession = null
        try { recognizer.close() } catch (_: Exception) {}
        try { worker?.quitSafely() } catch (_: Exception) {}; worker = null; workerHandler = null
        OverlayService.suppressOverlayUi(false)
    }

    override fun onDestroy() {
        release()
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putBoolean(KEY_ENABLED, false).apply()
        publishStatus("Kapalı")
        stopForeground(STOP_FOREGROUND_REMOVE)
        super.onDestroy()
    }

    @Suppress("DEPRECATION")
    private fun readParcelableIntent(intent: Intent, key: String): Intent? = if (Build.VERSION.SDK_INT >= 33) intent.getParcelableExtra(key, Intent::class.java) else intent.getParcelableExtra(key)

    companion object {
        const val ACTION_STABLE_LINES = "com.trtv.FILM_OCR_STABLE"
        const val ACTION_CLEAR_FILM = "com.trtv.FILM_OCR_CLEAR"
        const val ACTION_STATUS = "com.trtv.FILM_MODE_STATUS"
        const val ACTION_STOP = "com.trtv.FILM_MODE_STOP"
        const val EXTRA_LINES = "lines"
        const val EXTRA_STATUS = "status"
        const val EXTRA_RESULT_CODE = ProjectionProbeService.EXTRA_RESULT_CODE
        const val EXTRA_RESULT_DATA = ProjectionProbeService.EXTRA_RESULT_DATA
        const val PREFS = "film_mode"
        const val KEY_ENABLED = "enabled"
        const val KEY_BAND = "band_percent"
        private const val TAG = "BrolisFilmMode"
        private const val CHANNEL = "film_capture"
        private const val CLEAR_DELAY_MS = 300L
        @Volatile var active = false
            private set
        @Volatile var statusText: String = "Kapalı"
            private set
        @Volatile var ocrLatencyMs: Long = 0
            private set
        @Volatile var translationSource: String = "cihazda"
        @Volatile var externalStatus: String = ""

        fun publishExternalStatus(text: String) { externalStatus = text }
    }
}

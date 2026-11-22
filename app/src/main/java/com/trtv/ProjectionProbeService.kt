package com.trtv

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.IBinder
import android.util.Log
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer

/** Tanı ekranı için tek kare. Sürekli yakalama servisi bağımsız modda ayrı yönetilir. */
class ProjectionProbeService : Service() {
    private var projection: MediaProjection? = null
    private var display: VirtualDisplay? = null
    private var reader: ImageReader? = null
    private var thread: HandlerThread? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        enterForeground()
        val resultCode = intent?.getIntExtra(EXTRA_RESULT_CODE, 0) ?: 0
        val data = intent?.let { readIntent(it, EXTRA_RESULT_DATA) }
        if (data == null || resultCode == 0) { stopSelf(startId); return START_NOT_STICKY }
        try {
            val manager = getSystemService(MediaProjectionManager::class.java)
            projection = manager.getMediaProjection(resultCode, data)
            Handler(mainLooper).postDelayed({ captureOne(startId) }, 900L)
        } catch (e: Exception) {
            Log.w("BrolisProjectionProbe", "Ekran yakalama başarısız", e)
            broadcastResult(null, true)
            stopSelf(startId)
        }
        return START_NOT_STICKY
    }

    private fun captureOne(startId: Int) {
        val dm = resources.displayMetrics
        val width = dm.widthPixels.coerceAtLeast(1)
        val height = dm.heightPixels.coerceAtLeast(1)
        val density = dm.densityDpi.coerceAtLeast(1)
        thread = HandlerThread("brolis-projection-probe").also { it.start() }
        val handler = Handler(thread!!.looper)
        reader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)
        reader!!.setOnImageAvailableListener({ source ->
            val image = try { source.acquireLatestImage() } catch (_: Exception) { null } ?: return@setOnImageAvailableListener
            try {
                val plane = image.planes[0]
                val pixelStride = plane.pixelStride
                val rowPadding = plane.rowStride - pixelStride * image.width
                val paddedWidth = image.width + rowPadding / pixelStride
                val padded = Bitmap.createBitmap(paddedWidth, image.height, Bitmap.Config.ARGB_8888)
                val buffer: ByteBuffer = plane.buffer
                buffer.rewind(); padded.copyPixelsFromBuffer(buffer)
                val frame = Bitmap.createBitmap(padded, 0, 0, image.width, image.height)
                if (padded !== frame) padded.recycle()
                val black = isMostlyBlack(frame)
                val file = File(cacheDir, "projection-probe.png")
                FileOutputStream(file).use { frame.compress(Bitmap.CompressFormat.PNG, 100, it) }
                frame.recycle()
                broadcastResult(file, black)
            } catch (e: Exception) {
                Log.w("BrolisProjectionProbe", "Kare dönüştürülemedi", e)
                broadcastResult(null, true)
            } finally {
                image.close()
                handler.postDelayed({ release(); stopSelf(startId) }, 200L)
            }
        }, handler)
        display = projection?.createVirtualDisplay(
            "BrolisProjectionProbe", width, height, density,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR, reader!!.surface, null, handler
        )
        handler.postDelayed({
            if (reader != null) { broadcastResult(null, true); release(); stopSelf(startId) }
        }, 5000L)
    }

    private fun isMostlyBlack(bitmap: Bitmap): Boolean {
        var dark = 0; var total = 0
        val stepX = (bitmap.width / 48).coerceAtLeast(1)
        val stepY = (bitmap.height / 27).coerceAtLeast(1)
        for (y in 0 until bitmap.height step stepY) for (x in 0 until bitmap.width step stepX) {
            val p = bitmap.getPixel(x, y)
            val lum = (77 * ((p shr 16) and 255) + 150 * ((p shr 8) and 255) + 29 * (p and 255)) shr 8
            if (lum < 12) dark++
            total++
        }
        return total > 0 && dark.toFloat() / total > 0.985f
    }

    private fun broadcastResult(file: File?, black: Boolean) {
        getSharedPreferences("projection_probe", MODE_PRIVATE).edit()
            .putString("file", file?.absolutePath)
            .putBoolean("black", black)
            .putLong("captured_at", System.currentTimeMillis())
            .apply()
        sendBroadcast(Intent(ACTION_RESULT).setPackage(packageName)
            .putExtra(EXTRA_FILE, file?.absolutePath).putExtra(EXTRA_BLACK, black))
    }

    private fun enterForeground() {
        val manager = getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= 26) manager.createNotificationChannel(NotificationChannel(CHANNEL, "Ekran testi", NotificationManager.IMPORTANCE_LOW))
        val notification = (if (Build.VERSION.SDK_INT >= 26) Notification.Builder(this, CHANNEL) else Notification.Builder(this))
            .setSmallIcon(android.R.drawable.ic_menu_view).setContentTitle("Brolis ekran testi")
            .setContentText("Bir test karesi alınıyor").setOngoing(true).build()
        if (Build.VERSION.SDK_INT >= 29) startForeground(2, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION)
        else startForeground(2, notification)
    }

    private fun release() {
        display?.release(); display = null
        reader?.close(); reader = null
        projection?.stop(); projection = null
        thread?.quitSafely(); thread = null
    }

    override fun onDestroy() { release(); stopForeground(STOP_FOREGROUND_REMOVE); super.onDestroy() }

    @Suppress("DEPRECATION")
    private fun readIntent(intent: Intent, key: String): Intent? = if (Build.VERSION.SDK_INT >= 33) intent.getParcelableExtra(key, Intent::class.java) else intent.getParcelableExtra(key)

    companion object {
        const val ACTION_RESULT = "com.trtv.PROJECTION_PROBE_RESULT"
        const val EXTRA_RESULT_CODE = "result_code"
        const val EXTRA_RESULT_DATA = "result_data"
        const val EXTRA_FILE = "file"
        const val EXTRA_BLACK = "black"
        private const val CHANNEL = "projection_probe"
    }
}

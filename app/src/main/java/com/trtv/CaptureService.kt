package com.trtv

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.graphics.ImageFormat
import android.graphics.PixelFormat
import android.media.ImageReader
import android.media.MediaCodec
import android.media.MediaFormat
import android.os.Handler
import android.os.HandlerThread
import android.os.Looper
import android.provider.Settings
import android.util.Log
import android.view.Gravity
import android.view.WindowManager
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import java.io.BufferedInputStream
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.ConcurrentHashMap

class CaptureService : Service() {
    companion object {
        var listener: ((String) -> Unit)? = null
        var last = ""
    }

    private val main = Handler(Looper.getMainLooper())
    @Volatile private var running = true
    private var shell: Shell? = null
    private var overlay: LinearLayout? = null
    private lateinit var img: ImageView
    private lateinit var txt: TextView
    private var worker: Thread? = null

    override fun onBind(i: Intent?) = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel("c", "Yakalama", NotificationManager.IMPORTANCE_LOW))
        val n = Notification.Builder(this, "c").setContentTitle("TR Çeviri test").setSmallIcon(android.R.drawable.ic_menu_camera).build()
        startForeground(1, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
        val mode = intent?.getStringExtra("mode") ?: "png"
        running = false
        worker?.join(3000)
        running = true
        worker = Thread { work(mode) }.apply { start() }
        return START_NOT_STICKY
    }

    private fun log(s: String) {
        Log.i("TRTV", s)
        last = s
        main.post {
            listener?.invoke(s)
            if (overlay != null) txt.text = s
        }
    }

    private fun work(mode: String) {
        if (shell == null) shell = openShell(this, ::log)
        val sh = shell ?: return
        log("Bağlandı: ${sh.name}")
        if (!Settings.canDrawOverlays(this)) runCatching { sh.run("appops set $packageName SYSTEM_ALERT_WINDOW allow") }
        main.post { showOverlay() }
        try {
            when (mode) {
                "png" -> loopScreencap(sh, true)
                "raw" -> loopScreencap(sh, false)
                else -> loopH264(sh)
            }
        } catch (e: Throwable) {
            log("Hata: ${e.javaClass.simpleName} ${e.message}")
        }
    }

    private fun showOverlay() {
        if (overlay != null || !Settings.canDrawOverlays(this)) {
            if (overlay == null) log("Overlay izni yok!")
            return
        }
        img = ImageView(this)
        txt = TextView(this).apply { setTextColor(Color.WHITE); textSize = 12f; setPadding(8, 4, 8, 4) }
        overlay = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(0xCC000000.toInt())
            addView(img, LinearLayout.LayoutParams(384, 216))
            addView(txt, LinearLayout.LayoutParams(384, LinearLayout.LayoutParams.WRAP_CONTENT))
        }
        val lp = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT, WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE,
            PixelFormat.TRANSLUCENT
        ).apply { gravity = Gravity.TOP or Gravity.END }
        getSystemService(WindowManager::class.java).addView(overlay, lp)
    }

    private fun thumb(b: Bitmap) = main.post { if (overlay != null) img.setImageBitmap(b) }

    // luminance stats on a grid, excluding top-right overlay area
    private fun stats(w: Int, h: Int, lum: (Int, Int) -> Int): Pair<Double, Double> {
        var s = 0.0; var s2 = 0.0; var n = 0
        val step = maxOf(4, w / 160)
        var y = 0
        while (y < h) {
            var x = 0
            while (x < w) {
                if (!(x > w * 0.7 && y < h * 0.35)) {
                    val l = lum(x, y); s += l; s2 += l * l; n++
                }
                x += step
            }
            y += step
        }
        val m = s / n
        return m to (s2 / n - m * m)
    }

    private fun bmpLum(b: Bitmap, x: Int, y: Int): Int {
        val c = b.getPixel(x, y)
        return (Color.red(c) * 299 + Color.green(c) * 587 + Color.blue(c) * 114) / 1000
    }

    private fun loopScreencap(sh: Shell, png: Boolean) {
        var cnt = 0; var sumCap = 0L; var blacks = 0
        while (running) {
            val t0 = System.currentTimeMillis()
            val bytes = sh.exec(if (png) "screencap -p" else "screencap") { it.readBytes() }
            val t1 = System.currentTimeMillis()
            val bmp = if (png) BitmapFactory.decodeByteArray(bytes, 0, bytes.size) else {
                val bb = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
                val w = bb.getInt(0); val h = bb.getInt(4)
                val hdr = bytes.size - w * h * 4
                Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888).apply {
                    copyPixelsFromBuffer(ByteBuffer.wrap(bytes, hdr, w * h * 4))
                }
            }
            val t2 = System.currentTimeMillis()
            if (bmp == null) { log("Çözülemedi (${bytes.size} bayt)"); Thread.sleep(1000); continue }
            val (m, v) = stats(bmp.width, bmp.height) { x, y -> bmpLum(bmp, x, y) }
            val black = m < 16 && v < 25
            cnt++; sumCap += t1 - t0; if (black) blacks++
            thumb(Bitmap.createScaledBitmap(bmp, 384, 216, true))
            bmp.recycle()
            log("${if (png) "PNG" else "RAW"} ${bytes.size / 1024}KB yakalama=${t1 - t0}ms çözme=${t2 - t1}ms ort=${sumCap / cnt}ms\n" +
                "parlaklık=%.1f varyans=%.0f ${if (black) "SİYAH" else "GÖRÜNTÜ VAR"} (siyah $blacks/$cnt)".format(m, v))
            val left = 1000 - (System.currentTimeMillis() - t0)
            if (left > 0) Thread.sleep(left)
        }
    }

    private fun loopH264(sh: Shell) {
        while (running) {
            try {
                sh.exec("screenrecord --output-format=h264 --size 1280x720 --bit-rate 4000000 --time-limit 170 -") { decode(it) }
            } catch (e: Throwable) {
                log("H264 yeniden: ${e.javaClass.simpleName} ${e.message}")
                Thread.sleep(1000)
            }
        }
    }

    private fun decode(ins: InputStream) {
        val W = 1280; val H = 720
        val ht = HandlerThread("img").apply { start() }
        val reader = ImageReader.newInstance(W, H, ImageFormat.YUV_420_888, 3)
        val queued = ConcurrentHashMap<Long, Long>()
        var frames = 0; var winStart = System.currentTimeMillis(); var winFrames = 0; var latSum = 0L
        var codec: MediaCodec? = null
        var sps: ByteArray? = null; var pps: ByteArray? = null
        var pts = 0L
        val tStart = System.currentTimeMillis()
        reader.setOnImageAvailableListener({ r ->
            val im = r.acquireNextImage() ?: return@setOnImageAvailableListener
            val now = System.currentTimeMillis()
            val q = queued.remove(im.timestamp / 1000)
            if (q != null) latSum += now - q
            frames++; winFrames++
            if (now - winStart >= 1000) {
                val p = im.planes[0]; val buf = p.buffer; val rs = p.rowStride
                val (m, v) = stats(im.width, im.height) { x, y -> buf.get(y * rs + x).toInt() and 0xFF }
                val tb = Bitmap.createBitmap(192, 108, Bitmap.Config.ARGB_8888)
                for (y in 0 until 108) for (x in 0 until 192) {
                    val l = buf.get((y * im.height / 108) * rs + x * im.width / 192).toInt() and 0xFF
                    tb.setPixel(x, y, Color.rgb(l, l, l))
                }
                thumb(tb)
                val fps = winFrames * 1000.0 / (now - winStart)
                log("H264 fps=%.1f kare=$frames çözme gecikmesi=${latSum / frames}ms\nparlaklık=%.1f varyans=%.0f ${if (m < 16 && v < 25) "SİYAH" else "GÖRÜNTÜ VAR"}".format(fps, m, v))
                winStart = now; winFrames = 0
            }
            im.close()
        }, Handler(ht.looper))
        try {
            nals(ins) { nal ->
                if (!running) throw InterruptedException()
                val type = nal[4].toInt() and 0x1F
                if (codec == null) {
                    if (type == 7) sps = nal
                    if (type == 8) pps = nal
                    if (sps != null && pps != null) {
                        val f = MediaFormat.createVideoFormat("video/avc", W, H).apply {
                            setByteBuffer("csd-0", ByteBuffer.wrap(sps!!))
                            setByteBuffer("csd-1", ByteBuffer.wrap(pps!!))
                        }
                        codec = MediaCodec.createDecoderByType("video/avc").apply {
                            configure(f, reader.surface, null, 0); start()
                        }
                        log("Kodek hazır (${System.currentTimeMillis() - tStart}ms)")
                    }
                    return@nals
                }
                if (type == 7 || type == 8) return@nals
                val c = codec!!
                var idx: Int
                do { idx = c.dequeueInputBuffer(10000); drain(c) } while (idx < 0 && running)
                if (idx < 0) return@nals
                c.getInputBuffer(idx)!!.apply { clear(); put(nal) }
                pts += 1000
                queued[pts] = System.currentTimeMillis()
                c.queueInputBuffer(idx, 0, nal.size, pts, 0)
                drain(c)
            }
        } finally {
            runCatching { codec?.stop(); codec?.release() }
            reader.close(); ht.quitSafely()
        }
    }

    private val info = MediaCodec.BufferInfo()
    private fun drain(c: MediaCodec) {
        while (true) {
            val o = c.dequeueOutputBuffer(info, 0)
            if (o >= 0) c.releaseOutputBuffer(o, info.presentationTimeUs * 1000) else if (o == MediaCodec.INFO_TRY_AGAIN_LATER) return
        }
    }

    private fun nals(ins: InputStream, emit: (ByteArray) -> Unit) {
        val b = BufferedInputStream(ins, 1 shl 16)
        val cur = ByteArrayOutputStream(1 shl 16)
        var zeros = 0; var started = false
        while (true) {
            val c = b.read()
            if (c < 0) break
            if (c == 0) { zeros++; continue }
            if (c == 1 && zeros >= 2) {
                if (started && cur.size() > 4) emit(cur.toByteArray())
                cur.reset(); cur.write(byteArrayOf(0, 0, 0, 1)); started = true; zeros = 0
                continue
            }
            repeat(zeros) { cur.write(0) }; zeros = 0
            cur.write(c)
        }
        if (started && cur.size() > 4) emit(cur.toByteArray())
    }

    override fun onDestroy() {
        running = false
        overlay?.let { runCatching { getSystemService(WindowManager::class.java).removeView(it) } }
        overlay = null
        Thread { runCatching { shell?.close() } }.start()
        super.onDestroy()
    }
}

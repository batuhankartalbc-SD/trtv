package com.trtv

import android.content.Context
import dadb.AdbKeyPair
import dadb.Dadb
import rikka.shizuku.Shizuku
import java.io.File
import java.io.InputStream

interface Shell : AutoCloseable {
    val name: String
    fun <T> exec(cmd: String, block: (InputStream) -> T): T
    fun run(cmd: String): String = exec(cmd) { it.readBytes().decodeToString() }
}

class DadbShell(ctx: Context) : Shell {
    override val name = "ADB"
    private val d: Dadb

    init {
        val priv = File(ctx.filesDir, "adbkey")
        val pub = File(ctx.filesDir, "adbkey.pub")
        if (!priv.exists()) AdbKeyPair.generate(priv, pub)
        d = Dadb.create("127.0.0.1", 5555, AdbKeyPair.read(priv, pub))
    }

    override fun <T> exec(cmd: String, block: (InputStream) -> T): T =
        d.open("exec:$cmd").use { block(it.source.inputStream()) }

    override fun close() = d.close()
}

class ShizukuShell : Shell {
    override val name = "Shizuku"
    private val m = Shizuku::class.java.getDeclaredMethod(
        "newProcess", Array<String>::class.java, Array<String>::class.java, String::class.java
    ).apply { isAccessible = true }

    override fun <T> exec(cmd: String, block: (InputStream) -> T): T {
        val p = m.invoke(null, arrayOf("sh", "-c", cmd), null, null) as Process
        try { return block(p.inputStream) } finally { p.destroy() }
    }

    override fun close() {}

    companion object {
        fun ready() = runCatching { Shizuku.pingBinder() && Shizuku.checkSelfPermission() == 0 }.getOrDefault(false)
    }
}

fun openShell(ctx: Context, log: (String) -> Unit): Shell? {
    var err = ""
    try {
        log("ADB 127.0.0.1:5555 bağlanıyor… TV'de izin isteğini onaylayın")
        val s = DadbShell(ctx)
        if (s.run("echo ok").trim() == "ok") return s
    } catch (e: Throwable) { err = "ADB: ${e.javaClass.simpleName} ${e.message} ${e.cause?.message ?: ""}" }
    val shz = runCatching { Shizuku.pingBinder() }.getOrDefault(false)
    if (ShizukuShell.ready()) {
        val s = ShizukuShell()
        if (runCatching { s.run("echo ok").trim() }.getOrNull() == "ok") return s
    }
    log("Kabuk yok.\n$err\nShizuku: ${if (shz) "çalışıyor, izin yok/başarısız" else "çalışmıyor"}")
    return null
}

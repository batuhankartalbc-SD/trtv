package com.trtv

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Settings

/** TV açılınca katman servisini kendiliğinden başlatır; kullanıcının uygulamayı açmasına gerek kalmaz. */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(ctx: Context, intent: Intent) {
        if (Settings.canDrawOverlays(ctx)) {
            try { OverlayService.start(ctx) } catch (_: Exception) {}
        }
    }
}

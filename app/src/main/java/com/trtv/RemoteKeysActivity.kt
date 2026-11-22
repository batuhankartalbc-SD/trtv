package com.trtv

import android.app.Activity
import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.view.Gravity
import android.view.KeyEvent
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/** TV kumandası ve PC kısayolları için kısa başvuru ekranı. */
class RemoteKeysActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(48, 28, 48, 26)
            setBackgroundColor(Color.rgb(10, 14, 19))
        }
        root.addView(TextView(this).apply {
            text = "Kumanda tuşları"
            textSize = 32f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.rgb(62, 230, 160))
            gravity = Gravity.CENTER
            setPadding(8, 6, 8, 18)
        })
        val scroll = ScrollView(this).apply { isFocusable = true; isFillViewport = true }
        val content = TextView(this).apply {
            text = """
                TV MENÜLERİ
                ↑ / ↓   Menüde gezin
                OK      Seç / aç / boolean ayarı değiştir
                ← / →  Ayar değerini azalt / artır
                Geri    Önceki ekrana dön veya kapat

                HİZALAMA
                ← / → / ↑ / ↓   Çeviriyi kaydır
                OK              Kaydırma ve ölçek modu arasında geçiş
                Ölçek modunda ↑ / ↓   Boyutu artır / azalt
                Uzun OK veya MENU   Hizalamayı sıfırla
                Geri                Hizalamayı bitir

                TV AYARLARI
                Yazı tipi, yazı boyutu ve arka plan için ← / → kullan.
                Türkçe yazıları açıp kapatmak için OK'ye bas.
                Son konuşmayı tekrar göster satırında OK'ye bas.

                BİLGİSAYAR KISAYOLLARI
                F6    Son konuşmayı göster
                F8    Çeviri katmanını aç / kapat
                F9    Çeviriyi duraklat / sürdür
                F10   Bölge düzenleyiciyi aç / kapat
                F11   Ekranı yeniden çevir

                Geri ile bu sayfayı kapat.
            """.trimIndent()
            textSize = 21f
            setTextColor(Color.WHITE)
            setLineSpacing(8f, 1f)
            setPadding(24, 20, 24, 24)
            isFocusable = false
            setBackgroundColor(Color.rgb(22, 29, 38))
        }
        scroll.addView(content, ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        root.addView(scroll, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
        root.addView(Button(this).apply {
            text = "Geri dön"
            textSize = 20f
            setOnClickListener { finish() }
        })
        setContentView(root)
        scroll.requestFocus()
    }

    override fun onResume() {
        super.onResume()
        OverlayService.suppressOverlayUi(true)
    }

    override fun onPause() {
        OverlayService.suppressOverlayUi(false)
        super.onPause()
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        if (keyCode == KeyEvent.KEYCODE_BACK) { finish(); return true }
        return super.onKeyDown(keyCode, event)
    }
}

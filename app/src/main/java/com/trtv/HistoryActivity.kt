package com.trtv

import android.app.Activity
import android.graphics.Color
import android.os.Bundle
import android.text.SpannableString
import android.text.Spanned
import android.text.style.ForegroundColorSpan
import android.view.Gravity
import android.view.View
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/** Son 50 oyun altyazısını kumandayla okuyabileceğiniz yarı saydam TV ekranı. */
class HistoryActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = FrameLayout(this)
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 26, 32, 22)
            setBackgroundColor(Color.argb(235, 10, 14, 19))
        }
        val title = TextView(this).apply {
            text = "Konuşma geçmişi"
            textSize = 30f
            setTextColor(Color.rgb(62, 230, 160))
            setPadding(4, 4, 4, 6)
        }
        panel.addView(title)
        panel.addView(TextView(this).apply {
            text = "En yeni konuşmalar üstte · Geri ile kapat"
            textSize = 16f
            setTextColor(Color.rgb(191, 202, 215))
            setPadding(4, 0, 4, 16)
        })
        val scroll = ScrollView(this).apply { isFocusable = true; isFillViewport = true }
        val list = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        val entries = OverlayService.historySnapshot().asReversed()
        if (entries.isEmpty()) {
            list.addView(TextView(this).apply {
                text = "Henüz konuşma yok"
                textSize = 23f
                setTextColor(Color.WHITE)
                setPadding(8, 22, 8, 22)
            })
        } else entries.forEachIndexed { index, entry ->
            val speakerPrefix = if (entry.speaker.isBlank()) "" else "${entry.speaker}: "
            val line = SpannableString(speakerPrefix + entry.text)
            if (speakerPrefix.isNotEmpty() && entry.color != null) {
                line.setSpan(ForegroundColorSpan(entry.color), 0, speakerPrefix.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            }
            list.addView(TextView(this).apply {
                text = line
                textSize = 22f
                setTextColor(Color.WHITE)
                setPadding(12, 12, 12, 12)
                isFocusable = true
                isFocusableInTouchMode = false
                background = if (index == 0) focusBackground() else null
                contentDescription = if (speakerPrefix.isBlank()) entry.text else "$speakerPrefix${entry.text}"
            })
        }
        scroll.addView(list)
        panel.addView(scroll, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f))
        root.addView(panel, FrameLayout.LayoutParams((resources.displayMetrics.widthPixels * 0.52f).toInt(), FrameLayout.LayoutParams.MATCH_PARENT, Gravity.LEFT))
        setContentView(root)
        if (entries.isNotEmpty()) scroll.post { (list.getChildAt(0) as? View)?.requestFocus() }
    }

    override fun onResume() {
        super.onResume()
        OverlayService.suppressOverlayUi(true)
    }

    override fun onPause() {
        OverlayService.suppressOverlayUi(false)
        super.onPause()
    }

    private fun focusBackground() = android.graphics.drawable.GradientDrawable().apply {
        setColor(Color.argb(70, 62, 230, 160))
        setStroke(2, Color.rgb(62, 230, 160))
        cornerRadius = 12f
    }
}

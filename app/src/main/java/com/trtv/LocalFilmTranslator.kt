package com.trtv

import android.content.Context
import com.google.mlkit.common.model.DownloadConditions
import com.google.mlkit.nl.translate.TranslateLanguage
import com.google.mlkit.nl.translate.Translation
import com.google.mlkit.nl.translate.Translator
import com.google.mlkit.nl.translate.TranslatorOptions
import java.util.LinkedHashMap

/** On-device EN→TR fallback. Google ML Kit downloads its language model as needed. */
class LocalFilmTranslator(context: Context) : AutoCloseable {
    private val translator: Translator = Translation.getClient(
        TranslatorOptions.Builder()
            .setSourceLanguage(TranslateLanguage.ENGLISH)
            .setTargetLanguage(TranslateLanguage.TURKISH)
            .build()
    )
    private val cache = object : LinkedHashMap<String, String>(256, 0.75f, true) {
        override fun removeEldestEntry(eldest: MutableMap.MutableEntry<String, String>?): Boolean = size > 2000
    }
    @Volatile var state: String = "Cihaz çevirisi hazır değil"
        private set

    fun translate(lines: List<FilmLine>, completion: (List<String>?, String?) -> Unit) {
        state = "Cihaz çeviri modeli indiriliyor · Wi‑Fi gerekli"
        translator.downloadModelIfNeeded(DownloadConditions.Builder().requireWifi().build())
            .addOnSuccessListener {
                state = "Cihazda çeviri"
                val result = MutableList(lines.size) { "" }
                val pending = lines.indices.filter { index ->
                    val value = synchronized(cache) { cache[lines[index].text.lowercase()] }
                    if (value != null) result[index] = value
                    value == null
                }
                if (pending.isEmpty()) { completion(result, null); return@addOnSuccessListener }
                var cursor = 0
                fun next() {
                    if (cursor >= pending.size) { completion(result, null); return }
                    val index = pending[cursor++]
                    translator.translate(lines[index].text)
                        .addOnSuccessListener { translated ->
                            result[index] = translated
                            synchronized(cache) { cache[lines[index].text.lowercase()] = translated }
                            next()
                        }
                        .addOnFailureListener { error -> completion(null, error.message ?: "Çeviri yapılamadı") }
                }
                next()
            }
            .addOnFailureListener { error ->
                state = "Çeviri modeli indirilemedi"
                completion(null, error.message ?: state)
            }
    }

    override fun close() = translator.close()
}

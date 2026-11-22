package com.trtv

/** A cleaned subtitle plus the formatting that must survive translation. */
data class CleanFilmLine(
    val english: String,
    val dialoguePrefix: String = "",
    val effect: Boolean = false
) {
    fun format(translated: String): String = dialoguePrefix + if (effect) "[${translated.trim().removeSurrounding("[", "]")}]" else translated.trim()
}

data class FilmLine(
    val text: String,
    val box: List<Float>, // normalized x, y, width, height
    val lineHeight: Float,
    val prefix: String = "",
    val effect: Boolean = false
) {
    val key: String get() = "${text.lowercase()}|${box.joinToString(":") { (it * 100).toInt().toString() }}"
    fun formatted(translation: String): String = CleanFilmLine(text, prefix, effect).format(translation)
}

/** Strips only formatting markers; musical lyrics are deliberately excluded. */
fun cleanFilmLine(raw: String): CleanFilmLine? {
    var value = raw.trim()
    if (value.isBlank() || '♪' in value) return null
    var prefix = ""
    if (value.startsWith("- ") || value.startsWith("– ") || value.startsWith("— ")) {
        prefix = value.substring(0, 2)
        value = value.substring(2).trimStart()
    }
    val effect = (value.startsWith("[") && value.endsWith("]")) || (value.startsWith("(") && value.endsWith(")"))
    if (effect) value = value.substring(1, value.length - 1).trim()
    if (value.isBlank()) return null
    return CleanFilmLine(value, prefix, effect)
}

/** Requires the same ordered OCR result in consecutive sampled frames. */
class StableFilmLines(private val requiredFrames: Int = 2) {
    private var lastKeys: List<String>? = null
    private var streak = 0

    fun accept(lines: List<FilmLine>): List<FilmLine> {
        val keys = lines.map(FilmLine::key)
        if (keys.isEmpty()) { lastKeys = emptyList(); streak = 0; return emptyList() }
        if (keys == lastKeys) streak++ else { lastKeys = keys; streak = 1 }
        return if (streak >= requiredFrames) lines else emptyList()
    }
}

/** Keeps the latest translation revision for each OCR request id, including a later Gemini result. */
class TranslationRevisionCache(private val limit: Int = 2000) {
    private val values = LinkedHashMap<Int, List<String>>(16, 0.75f, true)

    fun put(id: Int, translations: List<String>): Boolean {
        val previous = values[id]
        values[id] = translations.toList()
        while (values.size > limit) values.entries.iterator().run { next(); remove() }
        return previous != translations
    }

    operator fun get(id: Int): List<String>? = values[id]
}

/** Normalizes a subtitle change summary so tiny OCR box jitter does not reset stability. */
fun filmLineSetKey(lines: List<FilmLine>): List<String> = lines.map { "${it.text.lowercase()}|${it.box[0].times(100).toInt()}|${it.box[1].times(100).toInt()}" }

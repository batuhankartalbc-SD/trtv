package com.trtv

/** Android bağımlılığı olmayan oyun metni, geometri ve protokol yardımcıları. */
data class OverlayItem(
    val b: List<Float>,
    val lh: Float,
    val speaker: String,
    val tr: String,
    val kind: String,
    val lines: Int,
    val fg: Int?,
    val bg: Int?,
    val sc: Int?,
    val align: String
)

data class HistoryEntry(val speaker: String, val text: String, val color: Int? = null)

fun wrapText(text: String, measure: (String) -> Float, maxWidth: Float): List<String> {
    val result = ArrayList<String>()
    var line = ""
    for (word in text.split(' ').filter(String::isNotEmpty)) {
        val candidate = if (line.isEmpty()) word else "$line $word"
        if (measure(candidate) <= maxWidth || line.isEmpty()) line = candidate
        else { result.add(line); line = word }
    }
    if (line.isNotEmpty()) result.add(line)
    return result.ifEmpty { listOf("") }
}

fun mapX(value: Float, scale: Float, offset: Float, width: Float): Float =
    ((value - 0.5f) * scale + 0.5f + offset) * width

fun mapY(value: Float, scale: Float, offset: Float, height: Float): Float =
    ((value - 0.5f) * scale + 0.5f + offset) * height

/** Parses the `items` array JSON without org.json, so the exact wire payload is JVM-testable. */
fun parseItemsJson(json: String?): List<OverlayItem> {
    if (json.isNullOrBlank()) return emptyList()
    val root = runCatching { JsonReader(json).read() }.getOrNull() as? List<*> ?: return emptyList()
    return root.mapNotNull { raw ->
        val item = raw as? Map<*, *> ?: return@mapNotNull null
        val bounds = (item["b"] as? List<*>)?.takeIf { it.size >= 4 }
            ?.take(4)?.mapNotNull { (it as? Number)?.toFloat() } ?: return@mapNotNull null
        if (bounds.size != 4) return@mapNotNull null
        OverlayItem(
            b = bounds,
            lh = (item["lh"] as? Number)?.toFloat() ?: 0.03f,
            speaker = item["s"] as? String ?: "",
            tr = item["tr"] as? String ?: "",
            kind = item["k"] as? String ?: "text",
            lines = (item["n"] as? Number)?.toInt() ?: 1,
            fg = parseHexColor(item["fg"] as? String),
            bg = parseHexColor(item["bg"] as? String),
            sc = parseHexColor(item["sc"] as? String),
            align = item["a"] as? String ?: "c"
        )
    }
}

private fun parseHexColor(value: String?): Int? {
    val hex = value?.removePrefix("#") ?: return null
    if (hex.length != 6 && hex.length != 8) return null
    return runCatching {
        val color = hex.toLong(16)
        if (hex.length == 6) (0xff000000L or color).toInt() else color.toInt()
    }.getOrNull()
}

fun isSameHistoryLine(left: HistoryEntry, right: HistoryEntry): Boolean {
    if (!left.speaker.trim().equals(right.speaker.trim(), ignoreCase = true)) return false
    val a = normalizeHistoryText(left.text)
    val b = normalizeHistoryText(right.text)
    if (a.isEmpty() || b.isEmpty()) return false
    if (a == b) return true
    val longest = maxOf(a.length, b.length)
    if (longest < 12) return false
    if (minOf(a.length, b.length).toFloat() / longest < 0.72f) return false
    return 1f - editDistance(a, b).toFloat() / longest >= 0.84f
}

fun addHistoryEntry(history: List<HistoryEntry>, incoming: HistoryEntry, limit: Int = 50): List<HistoryEntry> {
    if (limit <= 0 || incoming.text.isBlank()) return emptyList()
    val result = history.toMutableList()
    val last = result.lastOrNull()
    if (last != null && isSameHistoryLine(last, incoming)) result[result.lastIndex] = incoming
    else result.add(incoming)
    if (result.size > limit) result.subList(0, result.size - limit).clear()
    return result
}

private fun normalizeHistoryText(text: String): String =
    text.lowercase().replace(Regex("[^\\p{L}\\p{N}]+"), " ").trim().replace(Regex("\\s+"), " ")

private fun editDistance(a: String, b: String): Int {
    var previous = IntArray(b.length + 1) { it }
    for (i in a.indices) {
        val current = IntArray(b.length + 1)
        current[0] = i + 1
        for (j in b.indices) current[j + 1] = minOf(
            current[j] + 1, previous[j + 1] + 1, previous[j] + if (a[i] == b[j]) 0 else 1
        )
        previous = current
    }
    return previous[b.length]
}

/** Minimal JSON reader for the known items payload; no Android or third-party JSON classes. */
private class JsonReader(private val source: String) {
    private var index = 0
    fun read(): Any? {
        val value = value(); whitespace()
        require(index == source.length)
        return value
    }
    private fun value(): Any? {
        whitespace(); require(index < source.length)
        return when (source[index]) {
            '{' -> objectValue()
            '[' -> arrayValue()
            '"' -> stringValue()
            't' -> literal("true", true)
            'f' -> literal("false", false)
            'n' -> literal("null", null)
            else -> numberValue()
        }
    }
    private fun objectValue(): Map<String, Any?> {
        index++; whitespace(); val result = LinkedHashMap<String, Any?>()
        if (take('}')) return result
        while (true) {
            whitespace(); require(source.getOrNull(index) == '"')
            val key = stringValue(); whitespace(); require(take(':'))
            result[key] = value(); whitespace()
            if (take('}')) return result
            require(take(','))
        }
    }
    private fun arrayValue(): List<Any?> {
        index++; whitespace(); val result = ArrayList<Any?>()
        if (take(']')) return result
        while (true) {
            result.add(value()); whitespace()
            if (take(']')) return result
            require(take(','))
        }
    }
    private fun stringValue(): String {
        require(take('"')); val out = StringBuilder()
        while (index < source.length) {
            val ch = source[index++]
            when (ch) {
                '"' -> return out.toString()
                '\\' -> {
                    require(index < source.length)
                    when (val escaped = source[index++]) {
                        '"', '\\', '/' -> out.append(escaped)
                        'b' -> out.append('\b')
                        'f' -> out.append('\u000c')
                        'n' -> out.append('\n')
                        'r' -> out.append('\r')
                        't' -> out.append('\t')
                        'u' -> { require(index + 4 <= source.length); out.append(source.substring(index, index + 4).toInt(16).toChar()); index += 4 }
                        else -> error("invalid escape")
                    }
                }
                else -> out.append(ch)
            }
        }
        error("unterminated string")
    }
    private fun numberValue(): Double {
        val start = index
        if (source.getOrNull(index) == '-') index++
        while (source.getOrNull(index)?.isDigit() == true) index++
        if (source.getOrNull(index) == '.') { index++; while (source.getOrNull(index)?.isDigit() == true) index++ }
        if (source.getOrNull(index)?.lowercaseChar() == 'e') {
            index++; if (source.getOrNull(index) == '+' || source.getOrNull(index) == '-') index++
            while (source.getOrNull(index)?.isDigit() == true) index++
        }
        require(index > start)
        return source.substring(start, index).toDouble()
    }
    private fun <T> literal(token: String, value: T): T { require(source.startsWith(token, index)); index += token.length; return value }
    private fun take(char: Char): Boolean { if (source.getOrNull(index) != char) return false; index++; return true }
    private fun whitespace() { while (source.getOrNull(index)?.isWhitespace() == true) index++ }
}

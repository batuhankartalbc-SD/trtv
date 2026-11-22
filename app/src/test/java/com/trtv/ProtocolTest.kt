package com.trtv

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ProtocolTest {
    @Test fun wrapsWordsToFitMeasuredWidth() {
        assertEquals(listOf("press jump", "to continue"), wrapText("press jump to continue", { it.length.toFloat() }, 11f))
        assertEquals(listOf("unbrokenword"), wrapText("unbrokenword", { it.length.toFloat() }, 3f))
    }

    @Test fun mapsCalibrationOffsetAndScale() {
        assertEquals(100f, mapX(0.5f, 1f, 0f, 200f), 0.001f)
        assertEquals(120f, mapX(0.5f, 1f, 0.1f, 200f), 0.001f)
        assertEquals(50f, mapY(0.25f, 1f, 0f, 200f), 0.001f)
    }

    @Test fun parsesItemsJsonAndColorFields() {
        val items = parseItemsJson("""[{"b":[0.1,0.2,0.8,0.3],"lh":0.04,"s":"Lucia","tr":"Nereye gidiyorsun?","k":"subtitle","n":1,"fg":"#FFFFFF","bg":"#000000","sc":"#FF80C0","a":"c"}]""")
        assertEquals(1, items.size)
        assertEquals(listOf(0.1f, 0.2f, 0.8f, 0.3f), items[0].b)
        assertEquals("Lucia", items[0].speaker)
        assertEquals("Nereye gidiyorsun?", items[0].tr)
        assertEquals("subtitle", items[0].kind)
        assertEquals(0xffff80c0.toInt(), items[0].sc)
    }

    @Test fun skipsMalformedItemsAndHandlesInvalidJson() {
        assertEquals(0, parseItemsJson("not json").size)
        assertEquals(1, parseItemsJson("""[{"b":[0,0,1],"tr":"bad"},{"b":[0,0,1,1],"tr":"ok"}]""").size)
    }

    @Test fun recognizesRepeatedSubtitleAndSimilarImprovement() {
        assertTrue(isSameHistoryLine(HistoryEntry("Lucia", "Where are you going?"), HistoryEntry("lucia", "Where are you going?")))
        assertTrue(isSameHistoryLine(HistoryEntry("Lucia", "I will meet you by the station."), HistoryEntry("Lucia", "I will meet you at the station.")))
        assertFalse(isSameHistoryLine(HistoryEntry("Lucia", "Where are you going?"), HistoryEntry("Jason", "Where are you going?")))
    }

    @Test fun historyUpdatesSimilarLastLineAndKeepsLatestFifty() {
        val updated = addHistoryEntry(listOf(HistoryEntry("Lucia", "Wait here for me.")), HistoryEntry("Lucia", "Wait here for me!"))
        assertEquals(1, updated.size)
        assertEquals("Wait here for me!", updated.last().text)
        val capped = (1..55).fold(emptyList<HistoryEntry>()) { acc, n -> addHistoryEntry(acc, HistoryEntry("", "line $n")) }
        assertEquals(50, capped.size)
        assertEquals("line 6", capped.first().text)
        assertEquals("line 55", capped.last().text)
    }

    @Test fun filmLinesRequireTwoStableFramesAndPreserveFormatting() {
        val tracker = StableFilmLines()
        val line = FilmLine("Get in the car", listOf(.1f, .8f, .5f, .05f), .04f, prefix = "- ")
        assertTrue(tracker.accept(listOf(line)).isEmpty())
        assertEquals(listOf(line), tracker.accept(listOf(line)))
        assertEquals("- Arabaya bin", line.formatted("Arabaya bin"))
        assertEquals("[Yardım]", cleanFilmLine("[Help]")?.format("Yardım"))
        assertEquals(null, cleanFilmLine("♪ Song lyric ♪"))
    }

    @Test fun laterPcTranslationReplacesFallbackAndCacheIsBounded() {
        val cache = TranslationRevisionCache(limit = 2)
        assertTrue(cache.put(1, listOf("Yerel")))
        assertTrue(cache.put(1, listOf("PC düzeltmesi")))
        assertEquals(listOf("PC düzeltmesi"), cache[1])
        cache.put(2, listOf("İki")); cache.put(3, listOf("Üç"))
        assertEquals(null, cache[1])
    }
}

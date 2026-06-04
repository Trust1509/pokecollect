package at.pokecollect.scan

import android.graphics.Bitmap
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

data class ScanResult(
    val kartenname: String?,
    val setKuerzel: String?,
    val kartenNr: String?,
    val sprache: String?,
    val confidence: Float,
)

/**
 * On-device OCR pipeline using ML Kit.
 * Phase 1: Latin text recognition for DE/EN/FR/ES/IT cards.
 * CN/JP cards get basic detection; manual correction is expected.
 */
object CardScanner {

    private val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)

    // Set abbreviations known from the collection
    private val SET_PATTERN = Regex(
        """\b(ASC|MEG|PAF|PAL|JTG|DRI|PFL|WHT|BLK|MEP|PRE|SVI|sv2a|s8a)\b""",
        RegexOption.IGNORE_CASE
    )
    private val CARD_NR_PATTERN = Regex("""(\d{1,3})\s*/\s*(\d{1,3})""")

    suspend fun scan(bitmap: Bitmap): ScanResult {
        val text = runOcr(bitmap)
        val lines = text.textBlocks.flatMap { it.lines }.map { it.text.trim() }
        val fullText = lines.joinToString("\n")

        val kartenname = lines.firstOrNull { it.length in 3..40 && it.first().isUpperCase() }
        val setMatch = SET_PATTERN.find(fullText)
        val nrMatch = CARD_NR_PATTERN.find(fullText)

        val sprache = detectLanguage(fullText)

        val confidence = listOfNotNull(kartenname, setMatch, nrMatch).size / 3f

        return ScanResult(
            kartenname = kartenname,
            setKuerzel = setMatch?.value?.uppercase(),
            kartenNr = nrMatch?.let { "${it.groupValues[1]}/${it.groupValues[2]}" },
            sprache = sprache,
            confidence = confidence,
        )
    }

    private fun detectLanguage(text: String): String {
        return when {
            text.contains(Regex("[\\u4E00-\\u9FFF]")) -> "CN"
            text.contains(Regex("[\\u3040-\\u30FF]")) -> "JP"
            text.contains(Regex("\\bKP\\b|Energie|Schwäche|Widerstand", RegexOption.IGNORE_CASE)) -> "DE"
            text.contains(Regex("\\bHP\\b|Weakness|Resistance|Retreat", RegexOption.IGNORE_CASE)) -> "EN"
            else -> "DE"
        }
    }

    private suspend fun runOcr(bitmap: Bitmap) = suspendCancellableCoroutine { cont ->
        val image = InputImage.fromBitmap(bitmap, 0)
        recognizer.process(image)
            .addOnSuccessListener { cont.resume(it) }
            .addOnFailureListener { cont.resumeWithException(it) }
    }
}

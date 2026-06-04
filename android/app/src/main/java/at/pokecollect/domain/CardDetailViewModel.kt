package at.pokecollect.domain

import android.content.Context
import android.net.Uri
import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import at.pokecollect.data.CardEntity
import at.pokecollect.data.CardRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.File
import javax.inject.Inject

@HiltViewModel
class CardDetailViewModel @Inject constructor(
    private val repo: CardRepository,
    @ApplicationContext private val context: Context,
) : ViewModel() {

    private val _card = MutableStateFlow<CardEntity?>(null)
    val card = _card.asStateFlow()

    private val _busy = MutableStateFlow(false)
    val busy = _busy.asStateFlow()

    private var currentId: Int = -1

    fun load(id: Int) {
        currentId = id
        viewModelScope.launch { _card.value = repo.getCard(id) }
    }

    /** Felder per PUT /cards/{id} aktualisieren. */
    fun save(fields: Map<String, Any?>, onDone: () -> Unit = {}) = run("save") {
        repo.updateCard(currentId, fields)?.let { _card.value = it }
        onDone()
    }

    /** Bild-URL setzen (oder mit null entfernen → Platzhalter). */
    fun setImageUrl(url: String?) = save(mapOf("bild_pokedex_url" to url))

    /** Hochgeladenes Foto löschen → Backend liefert wieder Platzhalter. */
    fun deletePhoto() = run("deletePhoto") {
        repo.deleteImage(currentId)?.let { _card.value = it }
    }

    /** Foto aus Galerie hochladen (Uri → temporäre Datei → Multipart-Upload). */
    fun uploadPhoto(uri: Uri) = run("uploadPhoto") {
        val file = uriToTempFile(context, uri)
        if (file != null) {
            try {
                repo.uploadImage(currentId, file)?.let { _card.value = it }
            } finally {
                file.delete()
            }
        }
    }

    private fun run(tag: String, block: suspend () -> Unit) {
        viewModelScope.launch {
            _busy.value = true
            try {
                block()
            } catch (e: Exception) {
                Log.w("CardDetailViewModel", "$tag failed", e)
            } finally {
                _busy.value = false
            }
        }
    }
}

private fun uriToTempFile(context: Context, uri: Uri): File? = try {
    context.contentResolver.openInputStream(uri)?.use { input ->
        val file = File.createTempFile("upload", ".jpg", context.cacheDir)
        file.outputStream().use { output -> input.copyTo(output) }
        file
    }
} catch (e: Exception) {
    Log.w("CardDetailViewModel", "uriToTempFile failed", e)
    null
}

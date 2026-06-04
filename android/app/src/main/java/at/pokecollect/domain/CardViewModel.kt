package at.pokecollect.domain

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import at.pokecollect.data.CardCreate
import at.pokecollect.data.CardEntity
import at.pokecollect.data.CardRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject
import javax.inject.Named

@HiltViewModel
class CardViewModel @Inject constructor(
    private val repo: CardRepository,
    @Named("apiBase") val apiBase: String,
) : ViewModel() {

    private val _cards = MutableStateFlow<List<CardEntity>>(emptyList())
    val cards = _cards.asStateFlow()

    private val _loading = MutableStateFlow(false)
    val loading = _loading.asStateFlow()

    // Aktueller Suchtext – lebt im ViewModel, damit er beim Wechseln in die
    // Detailansicht und zurück erhalten bleibt.
    private val _query = MutableStateFlow("")
    val query = _query.asStateFlow()

    private var searchJob: Job? = null

    init {
        search("", debounce = false)
    }

    fun search(query: String) = search(query, debounce = true)

    private fun search(query: String, debounce: Boolean) {
        _query.value = query
        // Vorherige (evtl. noch laufende) Suche abbrechen, damit sich
        // parallele Anfragen nicht gegenseitig überschreiben.
        searchJob?.cancel()
        searchJob = viewModelScope.launch {
            if (debounce) delay(300)
            _loading.value = true
            try {
                _cards.value = repo.getCards(query.takeIf { it.isNotBlank() })
            } finally {
                _loading.value = false
            }
        }
    }

    fun createCard(card: CardCreate, onSuccess: () -> Unit) {
        viewModelScope.launch {
            repo.createCard(card)
            search("")
            onSuccess()
        }
    }
}

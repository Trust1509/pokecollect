package at.pokecollect.domain

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import at.pokecollect.data.CardCreate
import at.pokecollect.data.CardEntity
import at.pokecollect.data.CardRepository
import dagger.hilt.android.lifecycle.HiltViewModel
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

    init {
        search("")
    }

    fun search(query: String) {
        viewModelScope.launch {
            _loading.value = true
            _cards.value = repo.getCards(query.takeIf { it.isNotBlank() })
            _loading.value = false
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

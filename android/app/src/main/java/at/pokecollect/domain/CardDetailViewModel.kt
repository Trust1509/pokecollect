package at.pokecollect.domain

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import at.pokecollect.data.CardEntity
import at.pokecollect.data.CardRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class CardDetailViewModel @Inject constructor(
    private val repo: CardRepository,
) : ViewModel() {

    private val _card = MutableStateFlow<CardEntity?>(null)
    val card = _card.asStateFlow()

    fun load(id: Int) {
        viewModelScope.launch {
            _card.value = repo.getCard(id)
        }
    }
}

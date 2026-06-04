package at.pokecollect.domain

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import at.pokecollect.di.DEFAULT_API_BASE
import at.pokecollect.di.KEY_API_BASE
import at.pokecollect.di.dataStore
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class SettingsViewModel @Inject constructor(
    @ApplicationContext private val context: Context,
) : ViewModel() {

    private val _url = MutableStateFlow("")
    val url = _url.asStateFlow()

    init {
        viewModelScope.launch {
            _url.value = context.dataStore.data.first()[KEY_API_BASE] ?: DEFAULT_API_BASE
        }
    }

    fun save(newUrl: String, onSaved: () -> Unit) {
        viewModelScope.launch {
            context.dataStore.edit { it[KEY_API_BASE] = newUrl.trim() }
            onSaved()
        }
    }
}

package at.pokecollect.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import at.pokecollect.domain.CardDetailViewModel
import coil.compose.AsyncImage

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CardDetailScreen(
    cardId: Int,
    apiBase: String,
    onBack: () -> Unit,
    vm: CardDetailViewModel = hiltViewModel(),
) {
    LaunchedEffect(cardId) { vm.load(cardId) }
    val card by vm.card.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(card?.kartenname ?: "Karte") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, null)
                    }
                }
            )
        }
    ) { padding ->
        card?.let { c ->
            Column(
                modifier = Modifier
                    .padding(padding)
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                val imgUrl = c.bild_thumbnail_pfad?.let { "$apiBase/images/${it.removePrefix("/app/images/")}" }
                    ?: c.bild_pokedex_url
                AsyncImage(
                    model = imgUrl,
                    contentDescription = c.kartenname,
                    modifier = Modifier.size(180.dp, 250.dp),
                )
                HorizontalDivider()
                InfoRow("Pokédex-Nr.", c.pokedex_nr?.toString() ?: "–")
                InfoRow("Englischer Name", c.englischer_name ?: "–")
                InfoRow("Set", c.set_edition ?: "–")
                InfoRow("Karten-Nr.", c.karten_nr ?: "–")
                InfoRow("Seltenheit", c.seltenheit ?: "–")
                InfoRow("Kartenversion", c.kartenversion ?: "–")
                InfoRow("Folierung", c.folierung ?: "–")
                InfoRow("Sprache", c.sprache)
                InfoRow("Zustand", c.zustand ?: "–")
                InfoRow("Besossen", if (c.besessen) "Ja" else "Nein")
                c.wert_eur?.let { InfoRow("Wert", "€$it") }
                c.notizen?.let { InfoRow("Notizen", it) }
            }
        } ?: Box(Modifier.fillMaxSize(), contentAlignment = androidx.compose.ui.Alignment.Center) {
            CircularProgressIndicator()
        }
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
        Text(value, style = MaterialTheme.typography.bodyMedium)
    }
}

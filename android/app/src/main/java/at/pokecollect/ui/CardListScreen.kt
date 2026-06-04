package at.pokecollect.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import at.pokecollect.data.CardEntity
import coil.compose.AsyncImage

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CardListScreen(
    cards: List<CardEntity>,
    loading: Boolean,
    onSearch: (String) -> Unit,
    onCardClick: (Int) -> Unit,
    onScanClick: () -> Unit,
    apiBase: String,
) {
    var query by remember { mutableStateOf("") }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("PokéCollect") },
                actions = {
                    IconButton(onClick = onScanClick) {
                        Icon(Icons.Default.Add, contentDescription = "Scannen")
                    }
                }
            )
        }
    ) { padding ->
        Column(modifier = Modifier.padding(padding)) {
            OutlinedTextField(
                value = query,
                onValueChange = { query = it; onSearch(it) },
                placeholder = { Text("Suche …") },
                leadingIcon = { Icon(Icons.Default.Search, null) },
                singleLine = true,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 8.dp),
            )

            if (loading) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            } else {
                LazyColumn {
                    items(cards, key = { it.id }) { card ->
                        CardListItem(card, apiBase) { onCardClick(card.id) }
                    }
                }
            }
        }
    }
}

@Composable
private fun CardListItem(card: CardEntity, apiBase: String, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        val thumbUrl = card.bild_thumbnail_pfad?.let { "$apiBase/images/${it.removePrefix("/app/images/")}" }
            ?: card.bild_pokedex_url

        AsyncImage(
            model = thumbUrl,
            contentDescription = card.kartenname,
            modifier = Modifier.size(44.dp, 62.dp),
        )

        Column(modifier = Modifier.weight(1f)) {
            Text(card.kartenname, style = MaterialTheme.typography.bodyMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text(
                "${card.set_edition ?: "–"} ${card.karten_nr?.let { "· $it" } ?: ""}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }

        if (card.besessen) {
            Text("✓", color = MaterialTheme.colorScheme.primary)
        }

        card.wert_eur?.let {
            Text("€${it}", style = MaterialTheme.typography.bodySmall)
        }
    }
    HorizontalDivider()
}

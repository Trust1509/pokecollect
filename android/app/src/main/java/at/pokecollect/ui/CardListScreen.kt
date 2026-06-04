package at.pokecollect.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items as gridItems
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import at.pokecollect.data.CardEntity
import coil.compose.AsyncImage

enum class ViewMode { ALBUM, LIST }

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CardListScreen(
    cards: List<CardEntity>,
    loading: Boolean,
    query: String,
    onSearch: (String) -> Unit,
    onCardClick: (Int) -> Unit,
    onScanClick: () -> Unit,
    onSettingsClick: () -> Unit,
    apiBase: String,
) {
    var viewMode by rememberSaveable { mutableStateOf(ViewMode.ALBUM) }
    val apiConfigured = !apiBase.contains("x.x")

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("PokéCollect") },
                actions = {
                    TextButton(onClick = {
                        viewMode = if (viewMode == ViewMode.ALBUM) ViewMode.LIST else ViewMode.ALBUM
                    }) {
                        Text(if (viewMode == ViewMode.ALBUM) "Liste" else "Album")
                    }
                    IconButton(onClick = onScanClick) {
                        Icon(Icons.Default.Add, contentDescription = "Scannen")
                    }
                    IconButton(onClick = onSettingsClick) {
                        Icon(Icons.Default.Settings, contentDescription = "Einstellungen")
                    }
                }
            )
        }
    ) { padding ->
        Column(modifier = Modifier.padding(padding)) {
            if (!apiConfigured) {
                Surface(
                    color = MaterialTheme.colorScheme.errorContainer,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(12.dp),
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(
                            "API-URL nicht gesetzt – tippe oben aufs Zahnrad und trage die Adresse ein.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onErrorContainer,
                        )
                        TextButton(onClick = onSettingsClick) { Text("Zu den Einstellungen") }
                    }
                }
            }
            OutlinedTextField(
                value = query,
                onValueChange = onSearch,
                placeholder = { Text("Name oder Pokédex-Nr. …") },
                leadingIcon = { Icon(Icons.Default.Search, null) },
                singleLine = true,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 8.dp),
            )

            Text(
                "${cards.size} Karten",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 2.dp),
            )

            when {
                loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
                viewMode == ViewMode.ALBUM -> LazyVerticalGrid(
                    columns = GridCells.Fixed(3),
                    contentPadding = PaddingValues(8.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    gridItems(cards, key = { it.id }) { card ->
                        CardGridItem(card, apiBase) { onCardClick(card.id) }
                    }
                }
                else -> LazyColumn {
                    items(cards, key = { it.id }) { card ->
                        CardListItem(card, apiBase) { onCardClick(card.id) }
                    }
                }
            }
        }
    }
}

@Composable
private fun CardGridItem(card: CardEntity, apiBase: String, onClick: () -> Unit) {
    Column(
        modifier = Modifier
            .clickable(onClick = onClick)
            .padding(2.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(modifier = Modifier.fillMaxWidth()) {
            AsyncImage(
                model = cardImageUrl(
                    apiBase = apiBase,
                    localPfad = card.bild_thumbnail_pfad,
                    pokedexUrl = card.bild_pokedex_url,
                    karteUrl = card.bild_karte_url,
                    pokedexNr = card.pokedex_nr,
                ),
                contentDescription = card.kartenname,
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(63f / 88f),
            )
            if (card.besessen) {
                Box(
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(4.dp)
                        .size(12.dp)
                        .background(Color(0xFF4CAF50), CircleShape),
                )
            }
        }
        Text(
            card.kartenname,
            style = MaterialTheme.typography.bodySmall,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.padding(top = 2.dp),
        )
        Text(
            "#${card.pokedex_nr ?: "—"}${card.wert_eur?.let { " · €$it" } ?: ""}",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
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
        val thumbUrl = cardImageUrl(
            apiBase = apiBase,
            localPfad = card.bild_thumbnail_pfad,
            pokedexUrl = card.bild_pokedex_url,
            karteUrl = card.bild_karte_url,
            pokedexNr = card.pokedex_nr,
        )

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

/**
 * Bild-Priorität (wie im Web-Frontend):
 * 1. eigenes/serverseitiges Bild (localPfad)  2. manuelle URL  3. Auto-URL  4. Pokédex-Platzhalter.
 */
fun cardImageUrl(
    apiBase: String,
    localPfad: String?,
    pokedexUrl: String?,
    karteUrl: String?,
    pokedexNr: Int?,
): String? = when {
    // Server-Bilder liegen unter <root>/images/… (OHNE /api/v1).
    localPfad != null -> "${serverRoot(apiBase)}/images/${localPfad.substringAfterLast("/images/")}"
    pokedexUrl != null -> pokedexUrl
    karteUrl != null -> karteUrl
    else -> pokemonPlaceholderUrl(pokedexNr)
}

/** Server-Wurzel ohne das API-Präfix /api/v1 (für Bild-Auslieferung). */
fun serverRoot(apiBase: String): String =
    apiBase.removeSuffix("/").removeSuffix("/api/v1").removeSuffix("/")

/** Offizielles Pokédex-Artwork von pokemon.com als Platzhalter (Pokédex 1–1025). */
fun pokemonPlaceholderUrl(pokedexNr: Int?): String? {
    if (pokedexNr == null || pokedexNr < 1 || pokedexNr > 1025) return null
    val nr = pokedexNr.toString().padStart(3, '0')
    return "https://www.pokemon.com/static-assets/content-assets/cms2/img/pokedex/full/$nr.png"
}

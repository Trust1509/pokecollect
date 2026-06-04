package at.pokecollect.ui

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import at.pokecollect.data.CardEntity
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
    val busy by vm.busy.collectAsState()
    var editing by remember { mutableStateOf(false) }
    var showUrlDialog by remember { mutableStateOf(false) }

    val photoPicker = rememberLauncherForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri -> uri?.let { vm.uploadPhoto(it) } }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(card?.kartenname ?: "Karte") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, null)
                    }
                },
                actions = {
                    if (card != null) {
                        TextButton(onClick = { editing = !editing }) {
                            Text(if (editing) "Abbrechen" else "Bearbeiten")
                        }
                    }
                },
            )
        }
    ) { padding ->
        val c = card
        if (c == null) {
            Box(
                Modifier
                    .fillMaxSize()
                    .padding(padding),
                contentAlignment = Alignment.Center,
            ) { CircularProgressIndicator() }
        } else {
            Column(
                modifier = Modifier
                    .padding(padding)
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                val imgUrl = cardImageUrl(
                    apiBase = apiBase,
                    localPfad = c.bild_karte_pfad ?: c.bild_thumbnail_pfad,
                    pokedexUrl = c.bild_pokedex_url,
                    karteUrl = c.bild_karte_url,
                    pokedexNr = c.pokedex_nr,
                )
                val isPlaceholder = c.bild_karte_pfad == null && c.bild_thumbnail_pfad == null &&
                    c.bild_pokedex_url == null && c.bild_karte_url == null

                AsyncImage(
                    model = imgUrl,
                    contentDescription = c.kartenname,
                    modifier = Modifier
                        .fillMaxWidth(0.72f)
                        .aspectRatio(63f / 88f)
                        .align(Alignment.CenterHorizontally),
                )
                if (isPlaceholder) {
                    Text(
                        "Pokédex-Platzhalter",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.align(Alignment.CenterHorizontally),
                    )
                }

                // Bild-Aktionen
                FlowImageActions(
                    hasPhoto = c.bild_karte_pfad != null,
                    hasUrl = c.bild_pokedex_url != null,
                    busy = busy,
                    onUploadPhoto = { photoPicker.launch("image/*") },
                    onSetUrl = { showUrlDialog = true },
                    onDeletePhoto = { vm.deletePhoto() },
                    onClearUrl = { vm.setImageUrl(null) },
                )

                if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())

                HorizontalDivider()

                if (editing) {
                    EditFields(c, busy) { fields -> vm.save(fields) { editing = false } }
                } else {
                    InfoTable(c)
                }
            }

            if (showUrlDialog) {
                UrlDialog(
                    initial = c.bild_pokedex_url ?: "",
                    onDismiss = { showUrlDialog = false },
                    onSave = { url ->
                        vm.setImageUrl(url.ifBlank { null })
                        showUrlDialog = false
                    },
                )
            }
        }
    }
}

@Composable
private fun FlowImageActions(
    hasPhoto: Boolean,
    hasUrl: Boolean,
    busy: Boolean,
    onUploadPhoto: () -> Unit,
    onSetUrl: () -> Unit,
    onDeletePhoto: () -> Unit,
    onClearUrl: () -> Unit,
) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        OutlinedButton(onClick = onUploadPhoto, enabled = !busy) { Text("Foto") }
        OutlinedButton(onClick = onSetUrl, enabled = !busy) { Text("Bild-URL") }
    }
    if (hasPhoto || hasUrl) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            if (hasPhoto) TextButton(onClick = onDeletePhoto, enabled = !busy) { Text("Foto entfernen") }
            if (hasUrl) TextButton(onClick = onClearUrl, enabled = !busy) { Text("URL entfernen") }
        }
    }
}

@Composable
private fun InfoTable(c: CardEntity) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        InfoRow("Pokédex-Nr.", c.pokedex_nr?.toString() ?: "–")
        InfoRow("Deutscher Name", c.kartenname)
        InfoRow("Englischer Name", c.englischer_name ?: "–")
        InfoRow("Set", c.set_edition ?: "–")
        InfoRow("Karten-Nr.", c.karten_nr ?: "–")
        InfoRow("Seltenheit", c.seltenheit ?: "–")
        InfoRow("Kartenversion", c.kartenversion ?: "–")
        InfoRow("Folierung", c.folierung ?: "–")
        InfoRow("Sprache", c.sprache)
        InfoRow("Zustand", c.zustand ?: "–")
        InfoRow("Besessen", if (c.besessen) "Ja" else "Nein")
        InfoRow("Wert", c.wert_eur?.let { "€$it" } ?: "–")
        InfoRow("Wert aktualisiert", c.wert_aktualisiert ?: "–")
        InfoRow("Notizen", c.notizen ?: "–")
        InfoRow("Hinzugefügt", c.hinzugefuegt_am ?: "–")
        InfoRow("Aktualisiert", c.aktualisiert_am ?: "–")
    }
}

@Composable
private fun EditFields(
    card: CardEntity,
    busy: Boolean,
    onSave: (Map<String, Any?>) -> Unit,
) {
    var name by remember(card) { mutableStateOf(card.kartenname) }
    var eng by remember(card) { mutableStateOf(card.englischer_name ?: "") }
    var pdex by remember(card) { mutableStateOf(card.pokedex_nr?.toString() ?: "") }
    var setEd by remember(card) { mutableStateOf(card.set_edition ?: "") }
    var kartenNr by remember(card) { mutableStateOf(card.karten_nr ?: "") }
    var seltenheit by remember(card) { mutableStateOf(card.seltenheit ?: "") }
    var version by remember(card) { mutableStateOf(card.kartenversion ?: "") }
    var folierung by remember(card) { mutableStateOf(card.folierung ?: "") }
    var sprache by remember(card) { mutableStateOf(card.sprache) }
    var zustand by remember(card) { mutableStateOf(card.zustand ?: "") }
    var wert by remember(card) { mutableStateOf(card.wert_eur ?: "") }
    var notizen by remember(card) { mutableStateOf(card.notizen ?: "") }
    var besessen by remember(card) { mutableStateOf(card.besessen) }

    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        EditRow("Kartenname", name) { name = it }
        EditRow("Englischer Name", eng) { eng = it }
        EditRow("Pokédex-Nr.", pdex, KeyboardType.Number) { pdex = it }
        EditRow("Set", setEd) { setEd = it }
        EditRow("Karten-Nr.", kartenNr) { kartenNr = it }
        EditRow("Seltenheit", seltenheit) { seltenheit = it }
        EditRow("Kartenversion", version) { version = it }
        EditRow("Folierung", folierung) { folierung = it }
        EditRow("Sprache", sprache) { sprache = it }
        EditRow("Zustand", zustand) { zustand = it }
        EditRow("Wert (€)", wert, KeyboardType.Decimal) { wert = it }
        EditRow("Notizen", notizen) { notizen = it }

        Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(checked = besessen, onCheckedChange = { besessen = it })
            Text("Besessen")
        }

        Button(
            onClick = {
                onSave(
                    mapOf(
                        "kartenname" to name.trim(),
                        "englischer_name" to eng.ifBlank { null },
                        "pokedex_nr" to pdex.toIntOrNull(),
                        "set_edition" to setEd.ifBlank { null },
                        "karten_nr" to kartenNr.ifBlank { null },
                        "seltenheit" to seltenheit.ifBlank { null },
                        "kartenversion" to version.ifBlank { null },
                        "folierung" to folierung.ifBlank { null },
                        "sprache" to sprache.ifBlank { "DE" },
                        "zustand" to zustand.ifBlank { null },
                        "wert_eur" to wert.ifBlank { null },
                        "notizen" to notizen.ifBlank { null },
                        "besessen" to besessen,
                    )
                )
            },
            enabled = !busy,
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Speichern") }
    }
}

@Composable
private fun EditRow(
    label: String,
    value: String,
    keyboardType: KeyboardType = KeyboardType.Text,
    onChange: (String) -> Unit,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun UrlDialog(
    initial: String,
    onDismiss: () -> Unit,
    onSave: (String) -> Unit,
) {
    var url by remember { mutableStateOf(initial) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Bild-URL hinterlegen") },
        text = {
            OutlinedTextField(
                value = url,
                onValueChange = { url = it },
                label = { Text("https://…") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
        },
        confirmButton = { TextButton(onClick = { onSave(url) }) { Text("Speichern") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Abbrechen") } },
    )
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
        Text(value, style = MaterialTheme.typography.bodyMedium)
    }
}

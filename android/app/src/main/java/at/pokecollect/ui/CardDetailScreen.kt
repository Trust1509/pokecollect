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
    val message by vm.message.collectAsState()
    val enums by vm.enums.collectAsState()
    val sets by vm.sets.collectAsState()

    var editing by remember { mutableStateOf(false) }
    var showUrlDialog by remember { mutableStateOf(false) }
    val snackbar = remember { SnackbarHostState() }

    val photoPicker = rememberLauncherForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri -> uri?.let { vm.uploadPhoto(it) } }

    LaunchedEffect(message) {
        message?.let { snackbar.showSnackbar(it); vm.clearMessage() }
    }

    // Editierbare Felder – hochgezogen, damit der schwebende Speichern-Button sie lesen kann.
    val c0 = card
    var name by remember(c0) { mutableStateOf(c0?.kartenname ?: "") }
    var eng by remember(c0) { mutableStateOf(c0?.englischer_name ?: "") }
    var pdex by remember(c0) { mutableStateOf(c0?.pokedex_nr?.toString() ?: "") }
    var setEd by remember(c0) { mutableStateOf(c0?.set_edition ?: "") }
    var kartenNr by remember(c0) { mutableStateOf(c0?.karten_nr ?: "") }
    var seltenheit by remember(c0) { mutableStateOf(c0?.seltenheit ?: "") }
    var version by remember(c0) { mutableStateOf(c0?.kartenversion ?: "") }
    var folierung by remember(c0) { mutableStateOf(c0?.folierung ?: "") }
    var sprache by remember(c0) { mutableStateOf(c0?.sprache ?: "DE") }
    var zustand by remember(c0) { mutableStateOf(c0?.zustand ?: "") }
    var wert by remember(c0) { mutableStateOf(c0?.wert_eur ?: "") }
    var notizen by remember(c0) { mutableStateOf(c0?.notizen ?: "") }
    var besessen by remember(c0) { mutableStateOf(c0?.besessen ?: false) }

    fun fieldsMap(): Map<String, Any?> = mapOf(
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
        },
        snackbarHost = { SnackbarHost(snackbar) },
        floatingActionButton = {
            if (card != null && editing) {
                ExtendedFloatingActionButton(
                    onClick = { vm.save(fieldsMap()) { editing = false } },
                ) { Text(if (busy) "…" else "Speichern") }
            }
        },
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

                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { photoPicker.launch("image/*") }, enabled = !busy) { Text("Foto") }
                    OutlinedButton(onClick = { showUrlDialog = true }, enabled = !busy) { Text("Bild-URL") }
                }
                if (c.bild_karte_pfad != null || c.bild_pokedex_url != null) {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        if (c.bild_karte_pfad != null) {
                            TextButton(onClick = { vm.deletePhoto() }, enabled = !busy) { Text("Foto entfernen") }
                        }
                        if (c.bild_pokedex_url != null) {
                            TextButton(onClick = { vm.setImageUrl(null) }, enabled = !busy) { Text("URL entfernen") }
                        }
                    }
                }

                if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())

                HorizontalDivider()

                if (editing) {
                    EditRow("Kartenname", name) { name = it }
                    EditRow("Englischer Name", eng) { eng = it }
                    EditRow("Pokédex-Nr.", pdex, KeyboardType.Number) { pdex = it }
                    DropdownField("Set", setEd, sets.map { "${it.name} (${it.code})" }) { setEd = it }
                    EditRow("Karten-Nr. (NNN/MAX)", kartenNr) { kartenNr = it }
                    DropdownField("Seltenheit", seltenheit, enums?.seltenheit ?: emptyList()) { seltenheit = it }
                    DropdownField("Kartenversion", version, enums?.kartenversion ?: emptyList()) { version = it }
                    DropdownField("Folierung", folierung, enums?.folierung ?: emptyList()) { folierung = it }
                    DropdownField("Sprache", sprache, enums?.sprache ?: emptyList()) { sprache = it }
                    DropdownField("Zustand", zustand, enums?.zustand ?: emptyList()) { zustand = it }
                    EditRow("Wert (€)", wert, KeyboardType.Decimal) { wert = it }
                    EditRow("Notizen", notizen) { notizen = it }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = besessen, onCheckedChange = { besessen = it })
                        Text("Besessen")
                    }
                    Spacer(Modifier.height(80.dp)) // Platz für den schwebenden Button
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun DropdownField(
    label: String,
    value: String,
    options: List<String>,
    onSelect: (String) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }) {
        OutlinedTextField(
            value = value,
            onValueChange = {},
            readOnly = true,
            label = { Text(label) },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
            modifier = Modifier
                .menuAnchor()
                .fillMaxWidth(),
        )
        ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            DropdownMenuItem(text = { Text("—") }, onClick = { onSelect(""); expanded = false })
            options.forEach { opt ->
                DropdownMenuItem(text = { Text(opt) }, onClick = { onSelect(opt); expanded = false })
            }
        }
    }
}

@Composable
private fun UrlDialog(
    initial: String,
    onDismiss: () -> Unit,
    onSave: (String) -> Unit,
) {
    var url by remember { mutableStateOf(initial) }
    val trimmed = url.trim()
    val base = trimmed.substringBefore("?").lowercase()
    val isImage = base.endsWith(".png") || base.endsWith(".jpg") || base.endsWith(".jpeg")
    val valid = trimmed.isEmpty() || isImage

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Bild-URL hinterlegen") },
        text = {
            Column {
                OutlinedTextField(
                    value = url,
                    onValueChange = { url = it },
                    label = { Text("https://….png / .jpg") },
                    singleLine = true,
                    isError = !valid,
                    supportingText = {
                        if (!valid) Text("Nur direkte Bildlinks (.png, .jpg, .jpeg).")
                    },
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        },
        confirmButton = {
            TextButton(onClick = { onSave(trimmed) }, enabled = valid) { Text("Speichern") }
        },
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

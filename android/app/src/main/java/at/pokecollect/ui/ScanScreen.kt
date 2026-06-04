package at.pokecollect.ui

import android.graphics.Bitmap
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import at.pokecollect.data.CardCreate
import at.pokecollect.scan.CardScanner
import at.pokecollect.scan.ScanResult
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ScanScreen(
    onSaveCard: (CardCreate) -> Unit,
    onDismiss: () -> Unit,
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val scope = rememberCoroutineScope()

    var scanResult by remember { mutableStateOf<ScanResult?>(null) }
    var scanning by remember { mutableStateOf(false) }
    var imageCapture by remember { mutableStateOf<ImageCapture?>(null) }

    // Editable confirmation form
    var name by remember(scanResult) { mutableStateOf(scanResult?.kartenname ?: "") }
    var setKuerzel by remember(scanResult) { mutableStateOf(scanResult?.setKuerzel ?: "") }
    var kartenNr by remember(scanResult) { mutableStateOf(scanResult?.kartenNr ?: "") }
    var sprache by remember(scanResult) { mutableStateOf(scanResult?.sprache ?: "DE") }
    var folierung by remember { mutableStateOf("Normal") }
    var besessen by remember { mutableStateOf(true) }

    if (scanResult != null) {
        // Confirmation sheet
        AlertDialog(
            onDismissRequest = { scanResult = null },
            title = { Text("Karte bestätigen") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("Kartenname") })
                    OutlinedTextField(value = setKuerzel, onValueChange = { setKuerzel = it }, label = { Text("Set-Kürzel") })
                    OutlinedTextField(value = kartenNr, onValueChange = { kartenNr = it }, label = { Text("Karten-Nr.") })
                    OutlinedTextField(value = sprache, onValueChange = { sprache = it }, label = { Text("Sprache") })
                    OutlinedTextField(value = folierung, onValueChange = { folierung = it }, label = { Text("Folierung (manuell)") })
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = besessen, onCheckedChange = { besessen = it })
                        Text("Besossen")
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    onSaveCard(CardCreate(
                        kartenname = name,
                        set_edition = setKuerzel.ifBlank { null },
                        karten_nr = kartenNr.ifBlank { null },
                        sprache = sprache.ifBlank { "DE" },
                        folierung = folierung.ifBlank { "Normal" },
                        besessen = besessen,
                    ))
                    scanResult = null
                    onDismiss()
                }) { Text("Speichern") }
            },
            dismissButton = {
                Row {
                    TextButton(onClick = { scanResult = null }) { Text("Erneut scannen") }
                    TextButton(onClick = onDismiss) { Text("Verwerfen") }
                }
            },
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Karte scannen") },
                navigationIcon = {
                    IconButton(onClick = onDismiss) {
                        Icon(Icons.Default.CameraAlt, null)
                    }
                },
            )
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentAlignment = Alignment.Center,
        ) {
            AndroidView(
                factory = { ctx ->
                    val previewView = PreviewView(ctx)
                    val cameraProviderFuture = ProcessCameraProvider.getInstance(ctx)
                    cameraProviderFuture.addListener({
                        val provider = cameraProviderFuture.get()
                        val preview = Preview.Builder().build().also {
                            it.setSurfaceProvider(previewView.surfaceProvider)
                        }
                        val capture = ImageCapture.Builder()
                            .setCaptureMode(ImageCapture.CAPTURE_MODE_MAXIMIZE_QUALITY)
                            .build()
                        imageCapture = capture
                        provider.bindToLifecycle(
                            lifecycleOwner,
                            CameraSelector.DEFAULT_BACK_CAMERA,
                            preview,
                            capture,
                        )
                    }, ContextCompat.getMainExecutor(ctx))
                    previewView
                },
                modifier = Modifier.fillMaxSize(),
            )

            // Card frame guide
            Box(
                modifier = Modifier
                    .size(220.dp, 308.dp)
                    .border(2.dp, Color.Yellow, RoundedCornerShape(8.dp))
            )

            // Capture button
            Button(
                onClick = {
                    val capture = imageCapture ?: return@Button
                    scanning = true
                    capture.takePicture(
                        ContextCompat.getMainExecutor(context),
                        object : ImageCapture.OnImageCapturedCallback() {
                            override fun onCaptureSuccess(image: ImageProxy) {
                                val bitmap = image.toBitmap()
                                image.close()
                                scope.launch {
                                    scanResult = CardScanner.scan(bitmap)
                                    scanning = false
                                }
                            }
                            override fun onError(exc: ImageCaptureException) {
                                scanning = false
                            }
                        }
                    )
                },
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = 32.dp),
                enabled = !scanning,
            ) {
                if (scanning) CircularProgressIndicator(modifier = Modifier.size(20.dp))
                else Text("Scannen")
            }
        }
    }
}

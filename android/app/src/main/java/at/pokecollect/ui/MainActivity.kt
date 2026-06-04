package at.pokecollect.ui

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.*
import androidx.compose.ui.graphics.Color
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import at.pokecollect.domain.CardViewModel
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            PokéCollectTheme {
                AppNavigation()
            }
        }
    }
}

@Composable
private fun PokéCollectTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Color(0xFFFFCA28),
            background = Color(0xFF1A1A2E),
            surface = Color(0xFF16213E),
        ),
        content = content,
    )
}

@Composable
private fun AppNavigation() {
    val navController = rememberNavController()
    val vm: CardViewModel = hiltViewModel()
    val cards by vm.cards.collectAsState()
    val loading by vm.loading.collectAsState()
    val query by vm.query.collectAsState()

    NavHost(navController, startDestination = "list") {
        composable("list") {
            CardListScreen(
                cards = cards,
                loading = loading,
                query = query,
                onSearch = vm::search,
                onCardClick = { navController.navigate("detail/$it") },
                onScanClick = { navController.navigate("scan") },
                apiBase = vm.apiBase,
            )
        }
        composable("scan") {
            ScanScreen(
                onSaveCard = { card ->
                    vm.createCard(card) { navController.popBackStack() }
                },
                onDismiss = { navController.popBackStack() },
            )
        }
        composable("detail/{id}") { back ->
            val id = back.arguments?.getString("id")?.toIntOrNull() ?: return@composable
            CardDetailScreen(
                cardId = id,
                apiBase = vm.apiBase,
                onBack = { navController.popBackStack() },
            )
        }
    }
}

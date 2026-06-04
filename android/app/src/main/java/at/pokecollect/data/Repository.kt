package at.pokecollect.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class CardRepository @Inject constructor(
    private val api: ApiService,
    private val dao: CardDao,
) {
    suspend fun getCards(search: String? = null): List<CardEntity> = withContext(Dispatchers.IO) {
        try {
            val remote = if (search.isNullOrBlank()) {
                var page = 1
                val all = mutableListOf<Card>()
                while (true) {
                    val r = api.listCards(page = page, limit = 100)
                    all += r.items
                    if (page >= r.pages) break
                    page++
                }
                all
            } else {
                api.listCards(search = search, limit = 200).items
            }
            dao.upsertAll(remote.map { it.toEntity() })
            dao.getAll()
        } catch (e: Exception) {
            if (search.isNullOrBlank()) dao.getAll() else dao.search(search)
        }
    }

    suspend fun getCard(id: Int): CardEntity? = withContext(Dispatchers.IO) {
        try {
            val remote = api.getCard(id)
            dao.upsertAll(listOf(remote.toEntity()))
            dao.getById(id)
        } catch (e: Exception) {
            dao.getById(id)
        }
    }

    suspend fun createCard(card: CardCreate): Card = withContext(Dispatchers.IO) {
        val result = api.createCard(card)
        dao.upsertAll(listOf(result.toEntity()))
        result
    }

    suspend fun uploadImage(cardId: Int, file: File): Card = withContext(Dispatchers.IO) {
        val body = file.asRequestBody("image/*".toMediaType())
        val part = MultipartBody.Part.createFormData("file", file.name, body)
        val result = api.uploadImage(cardId, part)
        dao.upsertAll(listOf(result.toEntity()))
        result
    }
}

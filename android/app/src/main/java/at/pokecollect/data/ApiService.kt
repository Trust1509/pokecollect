package at.pokecollect.data

import okhttp3.MultipartBody
import retrofit2.http.*

data class Card(
    val id: Int,
    val kartenname: String,
    val pokedex_nr: Int?,
    val englischer_name: String?,
    val set_edition: String?,
    val karten_nr: String?,
    val seltenheit: String?,
    val kartenversion: String?,
    val folierung: String?,
    val sprache: String,
    val besessen: Boolean,
    val wert_eur: String?,
    val notizen: String?,
    val zustand: String?,
    val bild_pokedex_url: String?,
    val bild_karte_pfad: String?,
    val bild_thumbnail_pfad: String?,
    val hinzugefuegt_am: String,
    val aktualisiert_am: String,
)

data class CardListResponse(
    val items: List<Card>,
    val total: Int,
    val page: Int,
    val limit: Int,
    val pages: Int,
)

data class CardCreate(
    val kartenname: String,
    val pokedex_nr: Int? = null,
    val englischer_name: String? = null,
    val set_edition: String? = null,
    val karten_nr: String? = null,
    val seltenheit: String? = null,
    val kartenversion: String? = null,
    val folierung: String? = null,
    val sprache: String = "DE",
    val besessen: Boolean = false,
    val notizen: String? = null,
    val zustand: String? = null,
)

data class LoginRequest(val username: String, val password: String)
data class TokenResponse(val access_token: String, val token_type: String)

interface ApiService {
    @POST("auth/login")
    suspend fun login(@Body req: LoginRequest): TokenResponse

    @GET("cards")
    suspend fun listCards(
        @Query("besessen") besessen: Boolean? = null,
        @Query("search") search: String? = null,
        @Query("sort") sort: String = "pokedex_nr",
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 50,
    ): CardListResponse

    @GET("cards/{id}")
    suspend fun getCard(@Path("id") id: Int): Card

    @POST("cards")
    suspend fun createCard(@Body card: CardCreate): Card

    @PUT("cards/{id}")
    suspend fun updateCard(@Path("id") id: Int, @Body card: Map<String, Any?>): Card

    @DELETE("cards/{id}")
    suspend fun deleteCard(@Path("id") id: Int)

    @Multipart
    @POST("cards/{id}/image")
    suspend fun uploadImage(
        @Path("id") id: Int,
        @Part file: MultipartBody.Part,
    ): Card
}

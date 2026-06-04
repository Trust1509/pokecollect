package at.pokecollect.data

import androidx.room.*

@Entity(tableName = "cards")
data class CardEntity(
    @PrimaryKey val id: Int,
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
    val wert_aktualisiert: String?,
    val notizen: String?,
    val zustand: String?,
    val bild_pokedex_url: String?,
    val bild_karte_url: String?,
    val bild_karte_pfad: String?,
    val bild_thumbnail_pfad: String?,
    val hinzugefuegt_am: String?,
    val aktualisiert_am: String?,
)

@Dao
interface CardDao {
    @Query("SELECT * FROM cards ORDER BY pokedex_nr IS NULL, pokedex_nr ASC")
    suspend fun getAll(): List<CardEntity>

    @Query("SELECT * FROM cards WHERE id = :id")
    suspend fun getById(id: Int): CardEntity?

    @Query(
        "SELECT * FROM cards WHERE kartenname LIKE '%' || :q || '%' " +
        "OR englischer_name LIKE '%' || :q || '%' " +
        "OR CAST(pokedex_nr AS TEXT) LIKE '%' || :q || '%' " +
        "ORDER BY pokedex_nr IS NULL, pokedex_nr ASC"
    )
    suspend fun search(q: String): List<CardEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(cards: List<CardEntity>)

    @Delete
    suspend fun delete(card: CardEntity)

    @Query("DELETE FROM cards")
    suspend fun deleteAll()
}

@Database(entities = [CardEntity::class], version = 4, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun cardDao(): CardDao
}

fun Card.toEntity() = CardEntity(
    id = id,
    kartenname = kartenname,
    pokedex_nr = pokedex_nr,
    englischer_name = englischer_name,
    set_edition = set_edition,
    karten_nr = karten_nr,
    seltenheit = seltenheit,
    kartenversion = kartenversion,
    folierung = folierung,
    sprache = sprache,
    besessen = besessen,
    wert_eur = wert_eur,
    wert_aktualisiert = wert_aktualisiert,
    notizen = notizen,
    zustand = zustand,
    bild_pokedex_url = bild_pokedex_url,
    bild_karte_url = bild_karte_url,
    bild_karte_pfad = bild_karte_pfad,
    bild_thumbnail_pfad = bild_thumbnail_pfad,
    hinzugefuegt_am = hinzugefuegt_am,
    aktualisiert_am = aktualisiert_am,
)

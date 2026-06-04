package at.pokecollect.di

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import androidx.room.Room
import com.google.gson.GsonBuilder
import at.pokecollect.data.ApiService
import at.pokecollect.data.AppDatabase
import at.pokecollect.data.CardDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import javax.inject.Named
import javax.inject.Singleton

val Context.dataStore: DataStore<Preferences> by preferencesDataStore("settings")
val KEY_API_BASE = stringPreferencesKey("api_base")
val KEY_TOKEN = stringPreferencesKey("token")

const val DEFAULT_API_BASE = "http://192.168.x.x:3010/api/v1"

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides @Singleton
    fun db(@ApplicationContext ctx: Context): AppDatabase =
        Room.databaseBuilder(ctx, AppDatabase::class.java, "pokecollect.db")
            .fallbackToDestructiveMigration()
            .build()

    @Provides
    fun dao(db: AppDatabase): CardDao = db.cardDao()

    @Provides @Named("apiBase") @Singleton
    fun apiBase(@ApplicationContext ctx: Context): String = runBlocking {
        ctx.dataStore.data.first()[KEY_API_BASE] ?: DEFAULT_API_BASE
    }

    @Provides @Singleton
    fun retrofit(@ApplicationContext ctx: Context, @Named("apiBase") base: String): Retrofit {
        val token = runBlocking { ctx.dataStore.data.first()[KEY_TOKEN] }
        val client = OkHttpClient.Builder()
            .addInterceptor(HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC })
            .addInterceptor { chain ->
                val req = if (token != null)
                    chain.request().newBuilder().addHeader("Authorization", "Bearer $token").build()
                else chain.request()
                chain.proceed(req)
            }
            .build()
        return Retrofit.Builder()
            .baseUrl("$base/")
            .client(client)
            .addConverterFactory(
                // serializeNulls: damit z.B. {"bild_pokedex_url": null} wirklich
                // gesendet wird (zum Entfernen einer Bild-URL), statt weggelassen zu werden.
                GsonConverterFactory.create(GsonBuilder().serializeNulls().create())
            )
            .build()
    }

    @Provides @Singleton
    fun api(retrofit: Retrofit): ApiService = retrofit.create(ApiService::class.java)
}

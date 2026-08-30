package com.agentpay.guard.data.remote

import okhttp3.OkHttpClient
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import java.util.concurrent.TimeUnit

@JvmSuppressWildcards
interface GuardApi {

    @GET("guard/pending")
    suspend fun pending(): Response<List<Map<String, Any>>>

    @POST("guard/approvals/{requestId}/action")
    suspend fun approvalAction(
        @Path("requestId") requestId: String,
        @Body body: Map<String, String>
    ): Response<Map<String, Any>>

    @GET("agent/payment-status/{requestId}")
    suspend fun paymentStatus(@Path("requestId") requestId: String): Response<Map<String, Any>>

    @POST("sync/audit")
    suspend fun syncAudit(@Body events: List<Map<String, Any>>): Response<Map<String, Any>>

    @POST("agent/payment-request")
    suspend fun submitPaymentRequest(@Body body: Map<String, Any>): Response<Map<String, Any>>

    @GET("agents")
    suspend fun getAgents(): Response<Map<String, List<Map<String, Any>>>>

    @GET("policies")
    suspend fun getPolicies(): Response<Map<String, List<Map<String, Any>>>>

    @GET("intents")
    suspend fun getIntents(): Response<Map<String, List<Map<String, Any>>>>

    @GET("transactions")
    suspend fun getTransactions(): Response<Map<String, List<Map<String, Any>>>>

    companion object {
        fun create(baseUrl: String, deviceToken: String? = null): GuardApi {
            var normalized = baseUrl.trim().trimEnd('/')
            if (normalized.isNotEmpty() && !normalized.startsWith("http://") && !normalized.startsWith("https://")) {
                normalized = if (normalized.contains("ngrok")) "https://$normalized" else "http://$normalized"
            }
            if (!normalized.endsWith("/")) {
                normalized += "/"
            }
            val client = OkHttpClient.Builder()
                .addInterceptor { chain ->
                    val original = chain.request()
                    val builder = original.newBuilder()
                        .header("ngrok-skip-browser-warning", "true")
                        .header("User-Agent", "AgentPayGuard/1.0")
                    if (!deviceToken.isNullOrBlank() && original.header("Authorization") == null) {
                        builder.header("Authorization", "Bearer $deviceToken")
                    }
                    chain.proceed(builder.build())
                }
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(15, TimeUnit.SECONDS)
                .build()
            return Retrofit.Builder()
                .baseUrl(normalized)
                .client(client)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(GuardApi::class.java)
        }
    }
}


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

interface GuardApi {

    @GET("guard/pending")
    suspend fun pending(): Response<List<Map<String, Any?>>>

    @POST("guard/approvals/{requestId}/action")
    suspend fun approvalAction(
        @Path("requestId") requestId: String,
        @Body body: Map<String, String>
    ): Response<Map<String, Any?>>

    @GET("agent/payment-status/{requestId}")
    suspend fun paymentStatus(@Path("requestId") requestId: String): Response<Map<String, Any?>>

    @POST("sync/audit")
    suspend fun syncAudit(@Body events: List<Map<String, Any?>>): Response<Map<String, Any?>>

    @POST("agent/payment-request")
    suspend fun submitPaymentRequest(@Body body: Map<String, Any?>): Response<Map<String, Any?>>

    companion object {
        fun create(baseUrl: String): GuardApi {
            val client = OkHttpClient.Builder()
                .connectTimeout(5, TimeUnit.SECONDS)
                .readTimeout(10, TimeUnit.SECONDS)
                .build()
            return Retrofit.Builder()
                .baseUrl(if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/")
                .client(client)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(GuardApi::class.java)
        }
    }
}

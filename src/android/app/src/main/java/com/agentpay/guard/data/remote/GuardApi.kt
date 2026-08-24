package com.agentpay.guard.data.remote

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.POST
import java.util.concurrent.TimeUnit

interface GuardApi {

    @POST("sync/audit")
    suspend fun syncAudit(@Body events: List<Map<String, Any?>>): Response<Map<String, Any?>>

    @POST("agent/payment-request")
    suspend fun submitPaymentRequest(@Body body: Map<String, Any?>): Response<Map<String, Any?>>

    companion object {
        fun create(baseUrl: String): GuardApi {
            val client = OkHttpClient.Builder()
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(15, TimeUnit.SECONDS)
                .build()
            return Retrofit.Builder()
                .baseUrl(if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/")
                .client(client)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(GuardApi::class.java)
        }

        @Suppress("unused")
        private val jsonMedia = "application/json; charset=utf-8".toMediaType()
    }
}

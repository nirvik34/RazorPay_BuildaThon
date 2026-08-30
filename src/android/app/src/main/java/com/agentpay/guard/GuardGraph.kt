package com.agentpay.guard

import android.content.Context
import com.agentpay.guard.core.model.PaymentRequest
import com.agentpay.guard.data.remote.GuardApi
import com.agentpay.guard.data.repository.GuardRepository
import com.agentpay.guard.notifications.NotificationHelper
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

object GuardGraph {
    private val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private const val PREFS = "guard_settings"
    private const val KEY_BACKEND_URL = "backend_base_url"

    const val DEFAULT_BACKEND_URL = "http://10.0.2.2:8000"

    @Volatile var backendBaseUrl: String = DEFAULT_BACKEND_URL
        private set

    @Volatile private var apiClient: GuardApi? = null

    fun repository(context: Context): GuardRepository = GuardRepository.get(context)

    /** Cached Retrofit client — rebuilt only when the backend URL changes. */
    fun api(context: Context): GuardApi? = try {
        synchronized(this) {
            apiClient ?: GuardApi.create(backendBaseUrl).also { apiClient = it }
        }
    } catch (e: Exception) {
        null
    }

    private fun normalizeUrl(url: String): String {
        var trimmed = url.trim().trimEnd('/')
        if (trimmed.isEmpty()) return DEFAULT_BACKEND_URL
        if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) {
            trimmed = if (trimmed.contains("ngrok")) "https://$trimmed" else "http://$trimmed"
        }
        return trimmed
    }

    fun loadSettings(context: Context) {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val saved = prefs.getString(KEY_BACKEND_URL, DEFAULT_BACKEND_URL) ?: DEFAULT_BACKEND_URL
        backendBaseUrl = normalizeUrl(saved)
    }

    fun setBackendBaseUrl(context: Context, url: String) {
        val normalized = normalizeUrl(url)
        backendBaseUrl = normalized
        synchronized(this) { apiClient = null }
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY_BACKEND_URL, backendBaseUrl).apply()
    }

    fun submitIncomingRequest(context: Context, request: PaymentRequest) {
        applicationScope.launch {
            val repository = repository(context)
            repository.seedIfEmpty()
            val result = repository.submitRequest(request)
            val decision = result.decision ?: return@launch
            if (decision.decision == com.agentpay.guard.core.model.DecisionType.USER_APPROVAL) {
                val history = repository.history()
                val record = history.firstOrNull { it.request.requestId == request.requestId } ?: return@launch
                NotificationHelper.ensureChannel(context)
                NotificationHelper.notifyApproval(context, record)
            }
        }
    }
}

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

    @Volatile private var apiOverride: GuardApi? = null
    @Volatile var backendBaseUrl: String = "http://10.0.2.2:8000"

    fun repository(context: Context): GuardRepository = GuardRepository.get(context)

    fun api(context: Context): GuardApi? = try {
        apiOverride ?: GuardApi.create(backendBaseUrl)
    } catch (e: Exception) {
        null
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

package com.agentpay.guard.sync

import android.content.Context
import com.agentpay.guard.GuardGraph
import com.agentpay.guard.core.model.DecisionType
import com.agentpay.guard.core.model.PaymentRequest
import com.agentpay.guard.notifications.NotificationHelper
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * Live bridge between the Guard backend and this device.
 *
 * Real AI agents (Claude Desktop via MCP, custom GPT actions, the CLI simulator)
 * POST payment requests to the backend. This poller pulls them within seconds,
 * re-evaluates each one through the LOCAL decision engine (the phone is the trust
 * anchor — the backend's verdict is advisory), raises the approval notification,
 * and pushes the user's ACCEPT/REJECT back to the backend so the agent's payment
 * can proceed or die.
 */
object LiveSync {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private const val POLL_INTERVAL_MS = 4_000L

    @Volatile
    private var running = false

    fun start(context: Context) {
        if (running) return
        running = true
        val appContext = context.applicationContext
        scope.launch {
            while (running) {
                try {
                    syncOnce(appContext)
                } catch (e: Exception) {
                    backendReachable = false
                }
                delay(POLL_INTERVAL_MS)
            }
        }
    }

    fun stop() {
        running = false
    }

    @Volatile
    var backendReachable: Boolean = false
        private set

    suspend fun syncOnce(context: Context): Int {
        val api = GuardGraph.api(context) ?: return 0
        val response = api.pending()
        if (!response.isSuccessful) {
            backendReachable = false
            return 0
        }
        backendReachable = true
        val repository = GuardGraph.repository(context)

        // Sync agents from backend if available
        try {
            val agentsResp = api.getAgents()
            if (agentsResp.isSuccessful) {
                val remoteAgents = agentsResp.body()?.get("agents").orEmpty()
                val parsedAgents = remoteAgents.mapNotNull { raw ->
                    val id = raw["agentId"] as? String ?: return@mapNotNull null
                    val name = raw["name"] as? String ?: id
                    val statusStr = raw["status"] as? String ?: "ACTIVE"
                    val status = try { com.agentpay.guard.core.model.AgentStatus.valueOf(statusStr) } catch (e: Exception) { com.agentpay.guard.core.model.AgentStatus.ACTIVE }
                    val trust = (raw["trustScore"] as? Number)?.toInt() ?: 90
                    com.agentpay.guard.core.model.Agent(
                        agentId = id,
                        name = name,
                        ownerId = raw["ownerId"] as? String ?: "user_001",
                        status = status,
                        trustScore = trust
                    )
                }
                if (parsedAgents.isNotEmpty()) {
                    repository.upsertAgents(parsedAgents)
                }
            }
        } catch (_: Exception) {}

        // Sync intents from backend if available
        try {
            val intentsResp = api.getIntents()
            if (intentsResp.isSuccessful) {
                val remoteIntents = intentsResp.body()?.get("intents").orEmpty()
                val parsedIntents = remoteIntents.mapNotNull { raw ->
                    val id = raw["intentId"] as? String ?: return@mapNotNull null
                    val agentId = raw["agentId"] as? String ?: return@mapNotNull null
                    com.agentpay.guard.core.model.IntentRecord(
                        intentId = id,
                        agentId = agentId,
                        goal = raw["goal"] as? String ?: "",
                        category = raw["category"] as? String ?: "electronics",
                        budget = (raw["budget"] as? Number)?.toLong() ?: 0L
                    )
                }
                if (parsedIntents.isNotEmpty()) {
                    repository.upsertIntents(parsedIntents)
                }
            }
        } catch (_: Exception) {}

        var raised = 0
        val items = response.body().orEmpty()
        for (item in items) {
            val request = item["request"] as? Map<*, *> ?: continue
            val requestId = request["requestId"] as? String ?: continue
            if (repository.hasRequest(requestId)) continue

            val paymentRequest = PaymentRequest(
                requestId = requestId,
                agentId = request["agentId"] as? String ?: "unknown-agent",
                intentId = request["intentId"] as? String,
                merchant = request["merchant"] as? String ?: "unknown",
                product = request["product"] as? String ?: "Unknown item",
                amount = (request["amount"] as? Number)?.toLong() ?: 0L,
                category = request["category"] as? String ?: "electronics",
                sessionId = request["sessionId"] as? String ?: "sess_remote"
            )

            val result = repository.submitRequest(paymentRequest)
            val decision = result.decision
            if (decision?.decision == DecisionType.USER_APPROVAL) {
                raised += 1
                NotificationHelper.ensureChannel(context)
                val record = repository.history().firstOrNull { it.request.requestId == requestId }
                if (record != null) {
                    NotificationHelper.notifyApproval(context, record)
                }
            }
        }
        return raised
    }


    fun pushDecision(context: Context, requestId: String, accept: Boolean) {
        scope.launch {
            try {
                GuardGraph.api(context)?.approvalAction(
                    requestId,
                    mapOf("action" to if (accept) "accept" else "reject")
                )
            } catch (e: Exception) {
                void()
            }
        }
    }

    private fun void() = Unit
}

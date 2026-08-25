package com.agentpay.guard.sync

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.agentpay.guard.GuardGraph
import java.util.concurrent.TimeUnit

class SyncWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val repository = GuardGraph.repository(applicationContext)
        val unsynced = repository.unsyncedAudit()
        if (unsynced.isEmpty()) return successOrRetry()

        return try {
            val api = GuardGraph.api(applicationContext) ?: return Result.success()
            val response = api.syncAudit(
                events = unsynced.map { event ->
                    mapOf(
                        "eventId" to event.eventId,
                        "requestId" to event.requestId,
                        "atMs" to event.atMs,
                        "label" to event.label,
                        "detail" to event.detail
                    )
                }
            )
            if (response.isSuccessful) {
                repository.markSynced(unsynced)
                successOrRetry()
            } else {
                Result.retry()
            }
        } catch (e: Exception) {
            Result.retry()
        }
    }

    /**
     * Background best-effort pass: while we have connectivity, pull undecided
     * approvals and raise notifications. LiveSync (app open) remains the fast
     * path; this catches requests that arrived while the app was closed.
     */
    private suspend fun successOrRetry(): Result {
        val context = applicationContext
        return try {
            val api = GuardGraph.api(context) ?: return Result.success()
            val response = api.pending()
            if (!response.isSuccessful) return Result.success()
            val repository = GuardGraph.repository(context)
            repository.seedIfEmpty()
            for (item in response.body().orEmpty()) {
                val req = item["request"] as? Map<*, *> ?: continue
                val requestId = req["requestId"] as? String ?: continue
                if (repository.hasRequest(requestId)) continue
                val request = com.agentpay.guard.core.model.PaymentRequest(
                    requestId = requestId,
                    agentId = req["agentId"] as? String ?: "unknown-agent",
                    intentId = req["intentId"] as? String,
                    merchant = req["merchant"] as? String ?: "unknown",
                    product = req["product"] as? String ?: "Unknown item",
                    amount = (req["amount"] as? Number)?.toLong() ?: 0L,
                    category = req["category"] as? String ?: "electronics",
                    sessionId = req["sessionId"] as? String ?: "sess_bg"
                )
                val result = repository.submitRequest(request)
                val decision = result.decision
                if (decision?.decision == com.agentpay.guard.core.model.DecisionType.USER_APPROVAL) {
                    com.agentpay.guard.notifications.NotificationHelper.ensureChannel(context)
                    val record = repository.history().firstOrNull { it.request.requestId == requestId }
                    if (record != null) {
                        com.agentpay.guard.notifications.NotificationHelper.notifyApproval(context, record)
                    }
                }
            }
            Result.success()
        } catch (e: Exception) {
            Result.success()
        }
    }

    companion object {
        private const val WORK_NAME = "guard_audit_sync"

        fun schedule(context: Context) {
            val request = PeriodicWorkRequestBuilder<SyncWorker>(15, TimeUnit.MINUTES)
                .setConstraints(
                    androidx.work.Constraints.Builder()
                        .setRequiredNetworkType(androidx.work.NetworkType.CONNECTED)
                        .build()
                )
                .build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                request
            )
        }
    }
}

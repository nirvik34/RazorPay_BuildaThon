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
        if (unsynced.isEmpty()) return Result.success()

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
                Result.success()
            } else {
                Result.retry()
            }
        } catch (e: Exception) {
            Result.retry()
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

package com.agentpay.guard.notifications

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.agentpay.guard.GuardGraph
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class ApprovalActionReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        val requestId = intent.getStringExtra(NotificationHelper.EXTRA_REQUEST_ID) ?: return
        val accept = intent.action == NotificationHelper.ACTION_ACCEPT
        val appContext = context.applicationContext
        val pending = goAsync()

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val repository = GuardGraph.repository(appContext)
                val request = repository.requestById(requestId)
                if (request != null) {
                    repository.decide(request, accept)
                }
                NotificationHelper.cancel(appContext, requestId)
            } finally {
                pending.finish()
            }
        }
    }
}

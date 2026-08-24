package com.agentpay.guard.notifications

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationCompat
import com.agentpay.guard.ApprovalActivity
import com.agentpay.guard.MainActivity
import com.agentpay.guard.R
import com.agentpay.guard.core.model.PaymentRequest
import com.agentpay.guard.core.model.TransactionRecord

object NotificationHelper {

    const val CHANNEL_ID = "guard_approvals"
    const val APPROVAL_NOTIFICATION_ID_BASE = 4200

    fun ensureChannel(context: Context) {
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channel = NotificationChannel(
            CHANNEL_ID,
            "AI purchase approvals",
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "Requests from AI agents that need your decision"
        }
        manager.createNotificationChannel(channel)
    }

    fun notifyApproval(context: Context, record: TransactionRecord) {
        val request: PaymentRequest = record.request
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val notificationId = APPROVAL_NOTIFICATION_ID_BASE + (request.requestId.hashCode() and 0x7FFFFFFF) % 800

        val contentIntent = Intent(context, ApprovalActivity::class.java).apply {
            putExtra(ApprovalActivity.EXTRA_REQUEST_ID, request.requestId)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val contentPi = PendingIntent.getActivity(
            context, notificationId, contentIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val homeIntent = Intent(context, MainActivity::class.java)
        val homePi = PendingIntent.getActivity(
            context, notificationId + 1, homeIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val blockReason = record.decision.blockReason()?.label ?: "User approval required"
        val text = buildString {
            append("${request.product} · ${request.merchant}\n")
            append("₹${request.amount}")
            append(" · risk ${record.decision.riskLevel()}")
        }

        val notification: Notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_guard_shield)
            .setContentTitle("AI PURCHASE REQUEST")
            .setStyle(NotificationCompat.BigTextStyle().bigText(text).setBigContentTitle("AI PURCHASE REQUEST"))
            .setSubText(blockReason)
            .setContentIntent(contentPi)
            .setDeleteIntent(homePi)
            .setAutoCancel(true)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .addAction(action(context, notificationId, request.requestId, true, "ACCEPT"))
            .addAction(action(context, notificationId, request.requestId, false, "REJECT"))
            .build()

        manager.notify(notificationId, notification)
    }

    private fun action(context: Context, id: Int, requestId: String, accept: Boolean, label: String): NotificationCompat.Action {
        val intent = Intent(context, ApprovalActionReceiver::class.java).apply {
            this.action = if (accept) ACTION_ACCEPT else ACTION_REJECT
            putExtra(EXTRA_REQUEST_ID, requestId)
        }
        val pi = PendingIntent.getBroadcast(
            context,
            id + if (accept) 10 else 20,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Action.Builder(0, label, pi).build()
    }

    fun cancel(context: Context, requestId: String) {
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val notificationId = APPROVAL_NOTIFICATION_ID_BASE + (requestId.hashCode() and 0x7FFFFFFF) % 800
        manager.cancel(notificationId)
    }

    const val ACTION_ACCEPT = "com.agentpay.guard.ACTION_ACCEPT"
    const val ACTION_REJECT = "com.agentpay.guard.ACTION_REJECT"
    const val EXTRA_REQUEST_ID = "request_id"
}

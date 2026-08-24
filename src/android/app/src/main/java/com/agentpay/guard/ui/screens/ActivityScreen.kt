package com.agentpay.guard.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentpay.guard.core.model.TransactionRecord
import com.agentpay.guard.ui.GuardViewModel
import com.agentpay.guard.ui.components.StatusPill
import com.agentpay.guard.ui.components.formatINR

@Composable
fun ActivityScreen(viewModel: GuardViewModel) {
    val history by viewModel.history.collectAsState()

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            Spacer(Modifier.height(8.dp))
            Text("Activity", style = MaterialTheme.typography.headlineSmall)
            Text("Permanent local timeline of every decision.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(4.dp))
        }
        items(history.sortedByDescending { it.request.timestampMs }, key = { it.request.requestId }) { record ->
            ActivityCard(record)
        }
        item { Spacer(Modifier.height(24.dp)) }
    }
}

@Composable
private fun ActivityCard(record: TransactionRecord) {
    val accent = when {
        record.decision.decision == com.agentpay.guard.core.model.DecisionType.BLOCK -> com.agentpay.guard.ui.theme.GuardColors.Danger
        record.outcome == TransactionRecord.Outcome.DENIED -> com.agentpay.guard.ui.theme.GuardColors.Danger
        record.isPendingApproval -> com.agentpay.guard.ui.theme.GuardColors.Warning
        else -> com.agentpay.guard.ui.theme.GuardColors.Success
    }
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(6.dp))
            .background(MaterialTheme.colorScheme.surface)
    ) {
        Box(Modifier.width(4.dp).fillMaxHeight().background(accent))
        Row(
            modifier = Modifier.padding(12.dp).fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(record.request.product, fontWeight = FontWeight.SemiBold, fontSize = 14.sp, maxLines = 1)
                Text(
                    "${record.request.merchant} · ${formatTime(record.request.timestampMs)}",
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                val reason = record.decision.blockReason()?.label
                if (reason != null) {
                    Text(reason, fontSize = 12.sp, color = com.agentpay.guard.ui.theme.GuardColors.DangerText, fontWeight = FontWeight.Medium)
                }
                when {
                    record.decision.decision == com.agentpay.guard.core.model.DecisionType.BLOCK ->
                        Text("Blocked by policy — no approval requested", fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    record.outcome == TransactionRecord.Outcome.DENIED ->
                        Text("User rejected · Authorization denied", fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    else ->
                        Text("User approved · Authorization issued", fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            Column(horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(formatINR(record.request.amount), fontWeight = FontWeight.Bold, fontSize = 15.sp, fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace)
                StatusPill(record)
            }
        }
    }
}

private fun formatTime(timestampMs: Long): String =
    java.text.SimpleDateFormat("HH:mm", java.util.Locale.getDefault()).format(java.util.Date(timestampMs))

package com.agentpay.guard.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.agentpay.guard.ui.GuardViewModel
import com.agentpay.guard.ui.components.EmptyState
import com.agentpay.guard.ui.components.GuardDecisionCard

@Composable
fun ApprovalsScreen(viewModel: GuardViewModel) {
    val history by viewModel.history.collectAsState()
    val intents by viewModel.intents.collectAsState()
    val pending = history.filter { it.isPendingApproval }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Spacer(Modifier.height(8.dp))
            Text("Approvals", style = MaterialTheme.typography.headlineSmall)
            Text("Requests waiting for your decision. Nothing is charged without you.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(4.dp))
        }
        if (pending.isEmpty()) {
            item {
                EmptyState(
                    title = "You're all caught up.",
                    body = "No AI agent currently needs your approval. Local protection stays active."
                )
            }
        } else {
            items(pending, key = { it.request.requestId }) { record ->
                val intent = intents.firstOrNull { it.intentId == record.request.intentId && it.agentId == record.request.agentId }
                GuardDecisionCard(
                    record = record,
                    intent = intent,
                    onAccept = { viewModel.decide(record, accept = true) },
                    onReject = { viewModel.decide(record, accept = false) }
                )
            }
        }
        item { Spacer(Modifier.height(24.dp)) }
    }
}

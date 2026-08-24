package com.agentpay.guard.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentpay.guard.core.model.AgentStatus
import com.agentpay.guard.ui.GuardViewModel
import com.agentpay.guard.ui.components.formatINR
import com.agentpay.guard.ui.theme.GuardColors

@Composable
fun AgentsScreen(viewModel: GuardViewModel) {
    val agents by viewModel.agents.collectAsState()
    val history by viewModel.history.collectAsState()
    var freezeTarget by remember { mutableStateOf<String?>(null) }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Spacer(Modifier.height(8.dp))
            Text("Agents", style = MaterialTheme.typography.headlineSmall)
            Text("Explicit identity, scoped authority, local enforcement.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(4.dp))
        }
        items(agents, key = { it.agentId }) { agent ->
            val agentHistory = history.filter { it.request.agentId == agent.agentId }
            val spendToday = agentHistory.filter { it.outcome == com.agentpay.guard.core.model.TransactionRecord.Outcome.CAPTURED }.sumOf { it.request.amount }

            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(6.dp))
                    .background(MaterialTheme.colorScheme.surface)
                    .padding(14.dp)
            ) {
                Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Column {
                        Text(agent.name, fontWeight = FontWeight.SemiBold, fontSize = 15.sp)
                        Text(agent.agentId, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    Text(
                        when (agent.status) {
                            AgentStatus.ACTIVE -> "● ACTIVE"
                            AgentStatus.FROZEN -> "● FROZEN"
                            AgentStatus.REVOKED -> "● REVOKED"
                        },
                        color = if (agent.status == AgentStatus.ACTIVE) GuardColors.Info else GuardColors.Danger,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
                Spacer(Modifier.height(8.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Metric("TRUST", "${agent.trustScore}")
                    Metric("TODAY", "${agentHistory.size} txns")
                    Metric("SPENT", formatINR(spendToday))
                }
                Spacer(Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (agent.status == AgentStatus.FROZEN || agent.status == AgentStatus.REVOKED) {
                        Button(onClick = {
                            viewModel.setAgentStatus(agent, AgentStatus.ACTIVE, "Agent unfrozen on device")
                        }, modifier = Modifier.weight(1f)) { Text("UNFREEZE") }
                    } else {
                        Button(
                            onClick = { freezeTarget = agent.agentId },
                            colors = ButtonDefaults.buttonColors(containerColor = GuardColors.Danger),
                            modifier = Modifier.weight(1f)
                        ) { Text("FREEZE AGENT", fontWeight = FontWeight.Bold) }
                    }
                }
            }
        }
        item { Spacer(Modifier.height(24.dp)) }
    }

    freezeTarget?.let { agentId ->
        val agent = agents.firstOrNull { it.agentId == agentId }
        AlertDialog(
            onDismissRequest = { freezeTarget = null },
            title = { Text("Freeze ${agent?.name}?", fontWeight = FontWeight.Bold) },
            text = { Text("New financial requests will be blocked immediately on this device. Existing payments are unaffected.") },
            confirmButton = {
                Button(
                    onClick = {
                        agent?.let { viewModel.setAgentStatus(it, AgentStatus.FROZEN, "Agent frozen on device") }
                        freezeTarget = null
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = GuardColors.Danger)
                ) { Text("FREEZE AGENT") }
            },
            dismissButton = {
                OutlinedButton(onClick = { freezeTarget = null }) { Text("CANCEL") }
            }
        )
    }
}

@Composable
private fun Metric(label: String, value: String) {
    Column {
        Text(label, fontSize = 9.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
    }
}

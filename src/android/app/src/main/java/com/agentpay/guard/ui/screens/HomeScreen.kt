package com.agentpay.guard.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.clickable
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
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentpay.guard.core.model.DecisionType
import com.agentpay.guard.core.model.TransactionRecord
import com.agentpay.guard.ui.GuardViewModel
import com.agentpay.guard.ui.components.StatusPill
import com.agentpay.guard.ui.components.formatINR
import com.agentpay.guard.ui.theme.GuardColors

@Composable
fun HomeScreen(viewModel: GuardViewModel, onOpenApprovals: () -> Unit, onOpenSettings: () -> Unit = {}) {
    val history by viewModel.history.collectAsState()
    val agents by viewModel.agents.collectAsState()

    val capturedToday = history.filter {
        it.outcome == TransactionRecord.Outcome.CAPTURED && isToday(it.request.timestampMs)
    }
    val spend = capturedToday.sumOf { it.request.amount }
    val pendingCount = history.count { it.isPendingApproval }
    val blocked = history.count { it.decision.decision == DecisionType.BLOCK }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Spacer(Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = androidx.compose.ui.Alignment.CenterVertically
            ) {
                Text("AgentPay Guard", style = MaterialTheme.typography.headlineSmall)
                Text(
                    "SETTINGS",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    color = GuardColors.Brand,
                    modifier = Modifier.clip(RoundedCornerShape(6.dp))
                        .clickable { onOpenSettings() }
                        .padding(4.dp)
                )
            }
            Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Box(Modifier.height(8.dp).width(8.dp).clip(RoundedCornerShape(4.dp)).background(GuardColors.Success))
                Text(if (pendingCount > 0) "ACTION REQUIRED" else "DEVICE PROTECTED", fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                StatCard("SPENT TODAY", formatINR(spend), Modifier.weight(1f))
                StatCard("AGENTS", "${agents.count { it.status == com.agentpay.guard.core.model.AgentStatus.ACTIVE }}", Modifier.weight(1f))
            }
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                StatCard("APPROVALS NEEDED", "$pendingCount", Modifier.weight(1f), highlight = pendingCount > 0)
                StatCard("BLOCKED", "$blocked", Modifier.weight(1f), danger = blocked > 0)
            }
        }
        if (pendingCount > 0) {
            item {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(6.dp))
                        .background(GuardColors.WarningBg)
                        .padding(14.dp)
                ) {
                    Column {
                        Text("$pendingCount approval(s) waiting for your decision.", fontWeight = FontWeight.SemiBold, color = GuardColors.WarningText)
                        Text("Open the Approvals tab to review.", fontSize = 13.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }
        item { SectionTitle("RECENT ACTIVITY") }
        items(history.take(6)) { record ->
            ActivityRow(record)
        }
        item { SectionTitle("ACTIVE AGENTS") }
        items(agents.filter { it.status == com.agentpay.guard.core.model.AgentStatus.ACTIVE }) { agent ->
            Row(
                modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(6.dp)).background(MaterialTheme.colorScheme.surface).padding(14.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = androidx.compose.ui.Alignment.CenterVertically
            ) {
                Column {
                    Text(agent.name, style = MaterialTheme.typography.titleMedium.copy(fontSize = 14.sp))
                    Text(agent.agentId, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Text("● Active", color = GuardColors.Info, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
            }
        }
        item { Spacer(Modifier.height(24.dp)) }
    }
}

@Composable
private fun StatCard(label: String, value: String, modifier: Modifier = Modifier, highlight: Boolean = false, danger: Boolean = false) {
    val accent = when {
        danger -> GuardColors.Danger
        highlight -> GuardColors.Warning
        else -> null
    }
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(6.dp))
            .background(MaterialTheme.colorScheme.surface)
            .padding(14.dp)
    ) {
        if (accent != null) {
            Box(Modifier.width(28.dp).height(3.dp).clip(RoundedCornerShape(2.dp)).background(accent))
            Spacer(Modifier.height(8.dp))
        }
        Text(label, fontSize = 9.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, fontSize = 20.sp, fontWeight = FontWeight.Bold, fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace)
    }
}

@Composable
private fun SectionTitle(title: String) {
    Text(title, fontSize = 11.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.5.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
}

@Composable
private fun ActivityRow(record: TransactionRecord) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(6.dp))
            .background(MaterialTheme.colorScheme.surface)
            .padding(12.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = androidx.compose.ui.Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(record.request.product, style = MaterialTheme.typography.titleMedium.copy(fontSize = 14.sp), maxLines = 1)
            Text("${record.request.merchant} · ${formatINR(record.request.amount)}", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        StatusPill(record)
    }
}

private fun isToday(timestampMs: Long): Boolean {
    val cal = java.util.Calendar.getInstance().apply { timeInMillis = timestampMs }
    val today = java.util.Calendar.getInstance()
    return cal.get(java.util.Calendar.DAY_OF_YEAR) == today.get(java.util.Calendar.DAY_OF_YEAR) &&
        cal.get(java.util.Calendar.YEAR) == today.get(java.util.Calendar.YEAR)
}

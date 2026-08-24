package com.agentpay.guard.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentpay.guard.core.model.DecisionType
import com.agentpay.guard.core.model.RiskLevel
import com.agentpay.guard.core.model.TransactionRecord
import com.agentpay.guard.ui.theme.GuardColors

private val inrFormat = java.text.NumberFormat.getNumberInstance(java.util.Locale("en", "IN"))

fun formatINR(amount: Long): String = "₹" + inrFormat.format(amount)

@Composable
fun StatusPill(record: TransactionRecord) {
    val (bg, fg, label) = when {
        record.decision.decision == DecisionType.BLOCK -> Triple(GuardColors.DangerBg, GuardColors.DangerText, "BLOCKED")
        record.outcome == TransactionRecord.Outcome.DENIED -> Triple(GuardColors.DangerBg, GuardColors.DangerText, "REJECTED")
        record.isPendingApproval -> Triple(GuardColors.WarningBg, GuardColors.WarningText, "PENDING")
        else -> Triple(GuardColors.SuccessBg, GuardColors.SuccessText, "APPROVED")
    }
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(999.dp))
            .background(bg)
            .padding(horizontal = 8.dp, vertical = 2.dp)
    ) {
        Text(label, color = fg, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.5.sp)
    }
}

@Composable
fun AgentStatusDot(status: String) {
    val color = when (status) {
        "ACTIVE" -> GuardColors.Info
        "FROZEN", "REVOKED" -> GuardColors.Danger
        else -> GuardColors.Muted
    }
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        Box(modifier = Modifier.size(8.dp).clip(CircleShape).background(color))
        Text(status, fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
fun RiskScale(score: Int, modifier: Modifier = Modifier) {
    val activeIndex = when {
        score < 25 -> 0
        score < 50 -> 1
        score < 75 -> 2
        else -> 3
    }
    val colors = listOf(GuardColors.Success, GuardColors.Warning, GuardColors.Danger, Color(0xFFB3261E))
    Column(modifier = modifier.fillMaxWidth()) {
        Row(horizontalArrangement = Arrangement.spacedBy(4.dp), modifier = Modifier.fillMaxWidth()) {
            repeat(4) { i ->
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .height(5.dp)
                        .clip(RoundedCornerShape(3.dp))
                        .background(if (i <= activeIndex) colors[i] else GuardColors.Border)
                )
            }
        }
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            listOf("LOW", "MED", "HIGH", "CRIT").forEachIndexed { i, label ->
                Text(
                    label,
                    fontSize = 9.sp,
                    fontWeight = if (i == activeIndex) FontWeight.Bold else FontWeight.Normal,
                    color = if (i == activeIndex) colors[i] else MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
fun EmptyState(title: String, body: String, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .border(1.dp, GuardColors.Border, RoundedCornerShape(6.dp))
            .background(MaterialTheme.colorScheme.surface)
            .padding(vertical = 40.dp, horizontal = 24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        Text(title, style = MaterialTheme.typography.titleMedium)
        Text(body, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

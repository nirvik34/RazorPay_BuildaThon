package com.agentpay.guard.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentpay.guard.core.model.DecisionType
import com.agentpay.guard.core.model.IntentRecord
import com.agentpay.guard.core.model.ReasonCode
import com.agentpay.guard.core.model.TransactionRecord
import com.agentpay.guard.ui.theme.GuardColors

@Composable
fun GuardDecisionCard(
    record: TransactionRecord,
    intent: IntentRecord?,
    onAccept: (() -> Unit)? = null,
    onReject: (() -> Unit)? = null
) {
    val decision = record.decision
    val borderColor = when {
        decision.decision == DecisionType.BLOCK -> GuardColors.Danger
        record.isPendingApproval -> GuardColors.Warning
        else -> GuardColors.Success
    }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .background(MaterialTheme.colorScheme.surface)
            .padding(start = 0.dp, top = 16.dp, bottom = 16.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(borderColor)
                .padding(vertical = 4.dp),
            horizontalArrangement = Arrangement.Center
        ) {
            val label = when {
                decision.decision == DecisionType.BLOCK -> "BLOCKED BY POLICY"
                record.isPendingApproval -> "ACTION REQUIRED"
                record.outcome == TransactionRecord.Outcome.DENIED -> "REJECTED"
                else -> "APPROVED"
            }
            Text(label, color = MaterialTheme.colorScheme.surface, fontSize = 11.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
        }

        Column(modifier = Modifier.padding(horizontal = 16.dp)) {
            Spacer(Modifier.height(12.dp))
            Text(record.request.agentId, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)

            Spacer(Modifier.height(8.dp))
            Text(record.request.product, style = MaterialTheme.typography.titleMedium)
            Text(record.request.merchant.replaceFirstChar { it.uppercase() }, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)

            Spacer(Modifier.height(8.dp))
            Text(formatINR(record.request.amount), fontSize = 30.sp, fontWeight = FontWeight.Bold)

            HorizontalDivider(modifier = Modifier.padding(vertical = 12.dp))

            if (intent != null && record.isPendingApproval) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(6.dp))
                        .background(GuardColors.PurpleBg)
                        .padding(10.dp)
                ) {
                    Text("USER INTENT", fontSize = 9.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp, color = GuardColors.Purple)
                    Text("“${intent.goal}”", fontSize = 13.sp, fontStyle = FontStyle.Italic)
                    Text("budget ${formatINR(intent.budget)} · category ${intent.category}", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Spacer(Modifier.height(12.dp))
            }

            Text(
                if (decision.decision == DecisionType.BLOCK) "WHY IT WAS BLOCKED" else "GUARD CHECKS",
                fontSize = 9.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(Modifier.height(4.dp))
            val ordered = listOfNotNull(decision.blockReason()) + decision.reasonCodes.filter { it.severity != ReasonCode.Severity.BLOCK }
            for (reason in ordered.distinctBy { it.code }) {
                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(vertical = 2.dp)) {
                    val markColor = when (reason.severity) {
                        ReasonCode.Severity.OK -> GuardColors.Success
                        ReasonCode.Severity.WARN -> GuardColors.Warning
                        ReasonCode.Severity.BLOCK -> GuardColors.Danger
                    }
                    Box(Modifier.size(6.dp).clip(RoundedCornerShape(3.dp)).background(markColor))
                    Spacer(Modifier.height(0.dp))
                    Text(
                        "  ${reason.label}",
                        fontSize = 13.sp,
                        fontWeight = if (reason.severity == ReasonCode.Severity.BLOCK) FontWeight.SemiBold else FontWeight.Normal,
                        color = if (reason.severity == ReasonCode.Severity.BLOCK) GuardColors.DangerText else MaterialTheme.colorScheme.onSurface
                    )
                }
            }

            Spacer(Modifier.height(12.dp))
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Column {
                    Text("RISK", fontSize = 9.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text("${decision.riskLevel()} · ${decision.riskScore}/100", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                }
                RiskScale(score = decision.riskScore, modifier = Modifier.weight(1f).padding(start = 16.dp))
            }

            if (onAccept != null && onReject != null && record.isPendingApproval) {
                Spacer(Modifier.height(16.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
                    Button(
                        onClick = onReject,
                        colors = ButtonDefaults.buttonColors(containerColor = GuardColors.Danger),
                        modifier = Modifier.weight(1f).height(48.dp)
                    ) { Text("REJECT", fontWeight = FontWeight.Bold) }
                    Button(
                        onClick = onAccept,
                        colors = ButtonDefaults.buttonColors(containerColor = GuardColors.Success),
                        modifier = Modifier.weight(1f).height(48.dp)
                    ) { Text("ACCEPT", fontWeight = FontWeight.Bold) }
                }
            }
        }
    }
}

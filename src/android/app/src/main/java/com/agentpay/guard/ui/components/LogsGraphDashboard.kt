package com.agentpay.guard.ui.components

import androidx.compose.foundation.Canvas
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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentpay.guard.core.model.DecisionType
import com.agentpay.guard.core.model.TransactionRecord
import com.agentpay.guard.ui.theme.GuardColors

@Composable
fun LogsGraphDashboard(
    history: List<TransactionRecord>,
    modifier: Modifier = Modifier
) {
    val totalCount = history.size
    val totalSpend = history.sumOf { it.request.amount }
    val capturedSpend = history.filter { it.outcome == TransactionRecord.Outcome.CAPTURED }.sumOf { it.request.amount }
    val allowedCount = history.count { it.decision.decision == DecisionType.ALLOW }
    val pendingCount = history.count { it.isPendingApproval }
    val blockedCount = history.count { it.decision.decision == DecisionType.BLOCK }
    val avgRisk = if (totalCount > 0) (history.sumOf { it.decision.riskScore } / totalCount) else 0
    val blockRate = if (totalCount > 0) String.format("%.1f", (blockedCount.toFloat() / totalCount) * 100) else "0.0"

    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        // Metric Row 1
        Row(
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            MetricCard(
                title = "TOTAL SPEND",
                value = formatINR(totalSpend),
                sub = "${formatINR(capturedSpend)} captured",
                modifier = Modifier.weight(1f)
            )
            MetricCard(
                title = "LOG RECORDS",
                value = "$totalCount",
                sub = "$allowedCount passed · $pendingCount pending",
                modifier = Modifier.weight(1f)
            )
        }

        // Metric Row 2
        Row(
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            MetricCard(
                title = "BLOCK RATE",
                value = "$blockRate%",
                sub = "$blockedCount blocked by policy",
                accentColor = GuardColors.Danger,
                modifier = Modifier.weight(1f)
            )
            MetricCard(
                title = "AVG RISK SCORE",
                value = "$avgRisk / 100",
                sub = "Risk evaluation engine",
                accentColor = GuardColors.Warning,
                modifier = Modifier.weight(1f)
            )
        }

        // Timeline Activity Canvas Chart
        TimelineChartCard(history)

        // Decision Distribution & Risk Score Charts
        Row(
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            DecisionDonutCard(
                allowed = allowedCount,
                pending = pendingCount,
                blocked = blockedCount,
                modifier = Modifier.weight(1f)
            )
            RiskHistogramCard(
                history = history,
                modifier = Modifier.weight(1f)
            )
        }

        // Agent Breakdown Card
        AgentBreakdownCard(history)
    }
}

@Composable
private fun MetricCard(
    title: String,
    value: String,
    sub: String,
    modifier: Modifier = Modifier,
    accentColor: Color? = null
) {
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(8.dp))
            .background(MaterialTheme.colorScheme.surface)
            .padding(12.dp)
    ) {
        if (accentColor != null) {
            Box(
                Modifier
                    .width(24.dp)
                    .height(3.dp)
                    .clip(RoundedCornerShape(2.dp))
                    .background(accentColor)
            )
            Spacer(Modifier.height(6.dp))
        }
        Text(
            title,
            fontSize = 9.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 1.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Text(
            value,
            fontSize = 17.sp,
            fontWeight = FontWeight.Bold,
            fontFamily = FontFamily.Monospace,
            color = MaterialTheme.colorScheme.onSurface
        )
        Text(
            sub,
            fontSize = 10.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun TimelineChartCard(history: List<TransactionRecord>) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(MaterialTheme.colorScheme.surface)
            .padding(14.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                "TRANSACTION TIMELINE",
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 1.2.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Text(
                "Spend Volume",
                fontSize = 10.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color(0xFF2563EB)
            )
        }
        Spacer(Modifier.height(12.dp))

        val sorted = history.sortedBy { it.request.timestampMs }
        val points = if (sorted.isNotEmpty()) {
            val maxAmount = sorted.maxOf { it.request.amount }.coerceAtLeast(1.0)
            sorted.takeLast(12).map { (it.request.amount / maxAmount).toFloat() }
        } else {
            listOf(0.2f, 0.5f, 0.3f, 0.8f, 0.4f, 0.9f)
        }

        Canvas(
            modifier = Modifier
                .fillMaxWidth()
                .height(100.dp)
        ) {
            if (points.isEmpty()) return@Canvas
            val width = size.width
            val height = size.height
            val step = width / (points.size - 1).coerceAtLeast(1)

            val path = Path().apply {
                moveTo(0f, height * (1f - points[0]))
                for (i in 1 until points.size) {
                    val x = i * step
                    val y = height * (1f - points[i])
                    lineTo(x, y)
                }
            }

            val fillPath = Path().apply {
                addPath(path)
                lineTo(width, height)
                lineTo(0f, height)
                close()
            }

            drawPath(
                path = fillPath,
                brush = Brush.verticalGradient(
                    colors = listOf(Color(0xFF2563EB).copy(alpha = 0.3f), Color.Transparent)
                )
            )

            drawPath(
                path = path,
                color = Color(0xFF2563EB),
                style = Stroke(width = 4f)
            )
        }
    }
}

@Composable
private fun DecisionDonutCard(
    allowed: Int,
    pending: Int,
    blocked: Int,
    modifier: Modifier = Modifier
) {
    val total = (allowed + pending + blocked).coerceAtLeast(1)

    Column(
        modifier = modifier
            .clip(RoundedCornerShape(8.dp))
            .background(MaterialTheme.colorScheme.surface)
            .padding(12.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            "DECISIONS",
            fontSize = 9.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 1.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.align(Alignment.Start)
        )
        Spacer(Modifier.height(8.dp))

        Box(contentAlignment = Alignment.Center) {
            Canvas(modifier = Modifier.size(70.dp)) {
                val strokeWidth = 14f
                val sweepAllow = (allowed.toFloat() / total) * 360f
                val sweepPending = (pending.toFloat() / total) * 360f
                val sweepBlock = (blocked.toFloat() / total) * 360f

                var start = -90f
                drawArc(
                    color = Color(0xFF10B981),
                    startAngle = start,
                    sweepAngle = sweepAllow,
                    useCenter = false,
                    style = Stroke(width = strokeWidth)
                )
                start += sweepAllow

                drawArc(
                    color = Color(0xFFF59E0B),
                    startAngle = start,
                    sweepAngle = sweepPending,
                    useCenter = false,
                    style = Stroke(width = strokeWidth)
                )
                start += sweepPending

                drawArc(
                    color = Color(0xFFEF4444),
                    startAngle = start,
                    sweepAngle = sweepBlock,
                    useCenter = false,
                    style = Stroke(width = strokeWidth)
                )
            }
            Text(
                "$total",
                fontSize = 14.sp,
                fontWeight = FontWeight.Bold,
                fontFamily = FontFamily.Monospace
            )
        }

        Spacer(Modifier.height(8.dp))
        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
            LegendRow("Pass", "$allowed", Color(0xFF10B981))
            LegendRow("Pending", "$pending", Color(0xFFF59E0B))
            LegendRow("Block", "$blocked", Color(0xFFEF4444))
        }
    }
}

@Composable
private fun LegendRow(label: String, count: String, color: Color) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Box(
            Modifier
                .size(6.dp)
                .clip(CircleShape)
                .background(color)
        )
        Text(label, fontSize = 9.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(count, fontSize = 9.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
    }
}

@Composable
private fun RiskHistogramCard(
    history: List<TransactionRecord>,
    modifier: Modifier = Modifier
) {
    var low = 0
    var med = 0
    var high = 0
    var crit = 0

    for (rec in history) {
        val score = rec.decision.riskScore
        if (score <= 25) low++
        else if (score <= 50) med++
        else if (score <= 75) high++
        else crit++
    }

    val maxVal = maxOf(low, med, high, crit, 1)

    Column(
        modifier = modifier
            .clip(RoundedCornerShape(8.dp))
            .background(MaterialTheme.colorScheme.surface)
            .padding(12.dp)
    ) {
        Text(
            "RISK BUCKETS",
            fontSize = 9.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 1.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(Modifier.height(12.dp))

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(65.dp),
            horizontalArrangement = Arrangement.SpaceEvenly,
            verticalAlignment = Alignment.Bottom
        ) {
            BarColumn("Low", low, maxVal, Color(0xFF10B981))
            BarColumn("Med", med, maxVal, Color(0xFF3B82F6))
            BarColumn("High", high, maxVal, Color(0xFFF59E0B))
            BarColumn("Crit", crit, maxVal, Color(0xFFEF4444))
        }
    }
}

@Composable
private fun BarColumn(label: String, count: Int, maxVal: Int, color: Color) {
    val heightFraction = (count.toFloat() / maxVal).coerceIn(0.1f, 1f)

    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Bottom
    ) {
        Text("$count", fontSize = 8.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
        Spacer(Modifier.height(2.dp))
        Box(
            modifier = Modifier
                .width(12.dp)
                .height((40 * heightFraction).dp)
                .clip(RoundedCornerShape(topStart = 3.dp, topEnd = 3.dp))
                .background(color)
        )
        Spacer(Modifier.height(2.dp))
        Text(label, fontSize = 8.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun AgentBreakdownCard(history: List<TransactionRecord>) {
    val agentsMap = history.groupBy { it.request.agentId.take(10).uppercase() }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(MaterialTheme.colorScheme.surface)
            .padding(14.dp)
    ) {
        Text(
            "AGENT SPEND & ACTIVITY BREAKDOWN",
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 1.2.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(Modifier.height(10.dp))

        if (agentsMap.isEmpty()) {
            Text("No agent breakdown data available.", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                agentsMap.forEach { (agent, records) =>
                    val spend = records.sumOf { it.request.amount }
                    val count = records.size
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(agent, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                            Text("$count requests logged", fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        Text(
                            formatINR(spend),
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace,
                            color = Color(0xFF2563EB)
                        )
                    }
                }
            }
        }
    }
}

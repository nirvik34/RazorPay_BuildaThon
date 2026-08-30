package com.agentpay.guard.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentpay.guard.demo.DemoScenarios
import com.agentpay.guard.ui.GuardViewModel
import com.agentpay.guard.ui.theme.GuardColors

@Composable
fun SettingsScreen(viewModel: GuardViewModel) {
    var lastResult by remember { mutableStateOf("Ready.") }
    val agents by viewModel.agents.collectAsState()
    val intents by viewModel.intents.collectAsState()
    val activeAgentId = agents.firstOrNull { it.status == com.agentpay.guard.core.model.AgentStatus.ACTIVE }?.agentId ?: "agent-01"
    val activeIntentId = intents.firstOrNull { it.agentId == activeAgentId }?.intentId ?: intents.firstOrNull()?.intentId

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            Spacer(Modifier.height(8.dp))
            Text("Settings & Dynamic Simulation", style = MaterialTheme.typography.headlineSmall)
            Text(
                "Simulate incoming agent requests. The Guard evaluates each one dynamically with active backend policies.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Text(
                "Target Agent: $activeAgentId | Intent: ${activeIntentId ?: "None"}",
                style = MaterialTheme.typography.labelMedium,
                color = GuardColors.Brand,
                modifier = Modifier.padding(top = 4.dp)
            )
            Spacer(Modifier.height(4.dp))
        }
        item {
            BackendUrlField(viewModel, onStatusChange = { lastResult = it })
        }
        item {
            DemoButton("RUN NORMAL PURCHASE", GuardColors.Brand) {
                viewModel.submitRemote(DemoScenarios.normal(activeAgentId, activeIntentId)) { lastResult = it }
            }
        }
        item {
            DemoButton("RUN OVER-LIMIT TEST", GuardColors.Danger) {
                viewModel.submitRemote(DemoScenarios.overLimit(activeAgentId)) { lastResult = it }
            }
        }
        item {
            DemoButton("RUN INTENT MISMATCH TEST", GuardColors.Danger) {
                viewModel.submitRemote(DemoScenarios.intentMismatch(activeAgentId, activeIntentId)) { lastResult = it }
            }
        }
        item {
            DemoButton("RUN SPLITTING ATTACK TEST", GuardColors.Danger) {
                for (step in 0..2) viewModel.submitRemote(DemoScenarios.splitting(step, activeAgentId)) { lastResult = it }
                lastResult = "Splitting sequence sent to backend (expect circumvention on 3rd)"
            }
        }
        item {
            DemoButton("RUN COMPROMISED BURST TEST", GuardColors.Danger) {
                for (i in 0..9) viewModel.submitRemote(DemoScenarios.compromisedBurst(i, activeAgentId)) { lastResult = it }
                lastResult = "Burst sent to backend (expect velocity anomaly on Risk page)"
            }
        }
        item {
            Spacer(Modifier.height(4.dp))
            Text(lastResult, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(
                "Backend sync URL: ${com.agentpay.guard.GuardGraph.backendBaseUrl}",
                style = MaterialTheme.typography.labelSmall,
                color = Color(0xFF98A2B3),
                modifier = Modifier.padding(top = 8.dp, bottom = 24.dp)
            )
        }
    }
}


@Composable
private fun BackendUrlField(viewModel: GuardViewModel, onStatusChange: (String) -> Unit) {
    val context = androidx.compose.ui.platform.LocalContext.current
    var url by remember { mutableStateOf(com.agentpay.guard.GuardGraph.backendBaseUrl) }
    var isDiscovering by remember { mutableStateOf(false) }

    Column(modifier = Modifier.fillMaxWidth()) {
        Text("Backend URL", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
        Text(
            "Auto-detects laptop on Wi-Fi/LAN, or manually enter URL.",
            fontSize = 12.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(Modifier.height(6.dp))
        androidx.compose.material3.OutlinedTextField(
            value = url,
            onValueChange = { url = it },
            singleLine = true,
            textStyle = androidx.compose.ui.text.TextStyle(fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace, fontSize = 13.sp),
            modifier = Modifier.fillMaxWidth()
        )
        Spacer(Modifier.height(6.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Button(
                onClick = {
                    com.agentpay.guard.GuardGraph.setBackendBaseUrl(context, url)
                    viewModel.refresh()
                    onStatusChange("Saved URL: $url")
                },
                modifier = Modifier.weight(1f).height(42.dp)
            ) {
                Text("SAVE URL", fontWeight = FontWeight.Bold)
            }
            OutlinedButton(
                onClick = {
                    isDiscovering = true
                    viewModel.autoDiscover { res ->
                        isDiscovering = false
                        url = com.agentpay.guard.GuardGraph.backendBaseUrl
                        onStatusChange(res)
                    }
                },
                enabled = !isDiscovering,
                modifier = Modifier.weight(1f).height(42.dp)
            ) {
                Text(if (isDiscovering) "SCANNING..." else "AUTO DISCOVER", fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun DemoButton(label: String, color: Color, onClick: () -> Unit) {
    Button(
        onClick = onClick,
        colors = androidx.compose.material3.ButtonDefaults.buttonColors(containerColor = color),
        modifier = Modifier.fillMaxWidth().height(46.dp).clip(RoundedCornerShape(8.dp))
    ) {
        Text(label, fontWeight = FontWeight.Bold)
    }
}

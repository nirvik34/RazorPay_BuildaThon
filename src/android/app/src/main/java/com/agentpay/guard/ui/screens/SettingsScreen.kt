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

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            Spacer(Modifier.height(8.dp))
            Text("Settings & Demo", style = MaterialTheme.typography.headlineSmall)
            Text(
                "Simulate incoming agent requests. The Guard evaluates each one locally — offline capable.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(Modifier.height(4.dp))
        }
        item {
            DemoButton("RUN NORMAL PURCHASE", GuardColors.Brand) {
                viewModel.submitRemote(DemoScenarios.normal()) { lastResult = it }
            }
        }
        item {
            DemoButton("RUN OVER-LIMIT ATTACK", GuardColors.Danger) {
                viewModel.submitRemote(DemoScenarios.overLimit()) { lastResult = it }
            }
        }
        item {
            DemoButton("RUN INTENT MISMATCH", GuardColors.Danger) {
                viewModel.submitRemote(DemoScenarios.intentMismatch()) { lastResult = it }
            }
        }
        item {
            DemoButton("RUN SPLITTING ATTACK", GuardColors.Danger) {
                for (step in 0..2) viewModel.submitRemote(DemoScenarios.splitting(step)) { lastResult = it }
                lastResult = "Splitting sequence sent to backend (expect circumvention on 3rd)"
            }
        }
        item {
            DemoButton("RUN COMPROMISED BURST", GuardColors.Danger) {
                for (i in 0..9) viewModel.submitRemote(DemoScenarios.compromisedBurst(i)) { lastResult = it }
                lastResult = "Burst sent to backend (expect velocity anomaly on Risk page)"
            }
        }
        item {
            Spacer(Modifier.height(4.dp))
            Text(lastResult, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(
                "Backend sync URL: ${com.agentpay.guard.GuardGraph.backendBaseUrl} (optional — authorization works offline)",
                style = MaterialTheme.typography.labelSmall,
                color = Color(0xFF98A2B3),
                modifier = Modifier.padding(top = 8.dp, bottom = 24.dp)
            )
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

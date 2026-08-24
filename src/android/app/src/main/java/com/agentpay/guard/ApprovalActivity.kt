package com.agentpay.guard

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.getValue
import androidx.lifecycle.viewmodel.compose.viewModel
import com.agentpay.guard.ui.GuardViewModel
import com.agentpay.guard.ui.components.GuardDecisionCard
import com.agentpay.guard.ui.theme.AgentPayTheme
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Text
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items

class ApprovalActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val requestId = intent?.getStringExtra(EXTRA_REQUEST_ID)

        setContent {
            AgentPayTheme {
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    val viewModel: GuardViewModel = viewModel()
                    val history by viewModel.history.collectAsState()
                    val intents by viewModel.intents.collectAsState()

                    val records = history.filter {
                        requestId == null || it.request.requestId == requestId
                    }
                    val pendingOnly = records.filter { it.isPendingApproval }
                    val shown = pendingOnly.ifEmpty { records.take(1) }

                    LazyColumn(contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp)) {
                        item {
                            Text("AgentPay Guard", style = MaterialTheme.typography.headlineSmall)
                            Text(
                                "Your decision is required before any payment proceeds.",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        items(shown, key = { it.request.requestId }) { record ->
                            Column(Modifier.padding(top = 12.dp)) {
                                GuardDecisionCard(
                                    record = record,
                                    intent = intents.firstOrNull {
                                        it.intentId == record.request.intentId && it.agentId == record.request.agentId
                                    },
                                    onAccept = {
                                        viewModel.decide(record, accept = true)
                                        finish()
                                    },
                                    onReject = {
                                        viewModel.decide(record, accept = false)
                                        finish()
                                    }
                                )
                            }
                        }
                    }
                }
            }
        }
    }

    companion object {
        const val EXTRA_REQUEST_ID = "request_id"
    }
}

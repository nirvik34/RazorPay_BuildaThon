package com.agentpay.guard.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.agentpay.guard.GuardGraph
import com.agentpay.guard.core.model.Agent
import com.agentpay.guard.core.model.AgentStatus
import com.agentpay.guard.core.model.IntentRecord
import com.agentpay.guard.core.model.PaymentRequest
import com.agentpay.guard.core.model.TransactionRecord
import com.agentpay.guard.data.repository.GuardRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class GuardViewModel(application: Application) : AndroidViewModel(application) {

    private val repository: GuardRepository = GuardGraph.repository(application)

    private val _history = MutableStateFlow<List<TransactionRecord>>(emptyList())
    val history: StateFlow<List<TransactionRecord>> = _history

    private val _agents = MutableStateFlow<List<Agent>>(emptyList())
    val agents: StateFlow<List<Agent>> = _agents

    private val _intents = MutableStateFlow<List<IntentRecord>>(emptyList())
    val intents: StateFlow<List<IntentRecord>> = _intents

    init {
        viewModelScope.launch {
            repository.seedIfEmpty()
            refresh()
        }
    }

    fun refresh() {
        viewModelScope.launch {
            _history.value = repository.history()
            _agents.value = repository.agents()
            _intents.value = repository.defaultIntents()
        }
    }

    val pending: List<TransactionRecord>
        get() = _history.value.filter { it.isPendingApproval }

    fun submit(request: PaymentRequest, onDone: (TransactionRecord?) -> Unit = {}) {
        viewModelScope.launch {
            repository.seedIfEmpty()
            repository.submitRequest(request)
            refresh()
            onDone(_history.value.firstOrNull { it.request.requestId == request.requestId })
        }
    }

    fun decide(record: TransactionRecord, accept: Boolean) {
        viewModelScope.launch {
            repository.decide(record.request, accept)
            com.agentpay.guard.sync.LiveSync.pushDecision(
                getApplication(),
                record.request.requestId,
                accept
            )
            refresh()
        }
    }

    fun setAgentStatus(agent: Agent, status: AgentStatus, note: String) {
        viewModelScope.launch {
            repository.setAgentStatus(agent.agentId, status, note)
            refresh()
        }
    }
}

package com.agentpay.guard.core.policy

import com.agentpay.guard.core.model.Agent
import com.agentpay.guard.core.model.AgentStatus
import com.agentpay.guard.core.model.PaymentRequest
import com.agentpay.guard.core.model.Policy
import com.agentpay.guard.core.model.TransactionRecord
import java.util.Calendar
import java.util.concurrent.TimeUnit

object PolicyEngine {
    const val VELOCITY_WINDOW_MS: Long = 10 * 60_000L
    const val CIRCUMVENTION_WINDOW_MS: Long = 5 * 60_000L
    fun knownMerchants(history: List<TransactionRecord>): Set<String> = history
        .filter { rec ->
            rec.decision.decision == com.agentpay.guard.core.model.DecisionType.ALLOW ||
                (rec.decision.decision == com.agentpay.guard.core.model.DecisionType.USER_APPROVAL && rec.userActionAtMs != null)
        }
        .map { it.request.merchant }
        .toSet()

    fun todayApprovedSpend(history: List<TransactionRecord>, agentId: String, nowMs: Long): Long =
        history.filter { rec ->
            val sameDay = Calendar.getInstance().apply { timeInMillis = rec.request.timestampMs }
            val today = Calendar.getInstance().apply { timeInMillis = nowMs }
            rec.request.agentId == agentId &&
                rec.outcome == TransactionRecord.Outcome.CAPTURED &&
                sameDay.get(Calendar.DAY_OF_YEAR) == today.get(Calendar.DAY_OF_YEAR) &&
                sameDay.get(Calendar.YEAR) == today.get(Calendar.YEAR)
        }.sumOf { it.request.amount }
    data class HardCheck(
        val passed: Boolean,
        val code: String,
        val label: String
    )

    fun evaluateHardChecks(request: PaymentRequest, agent: Agent, policy: Policy, history: List<TransactionRecord>, nowMs: Long): List<HardCheck> {
        val checks = mutableListOf<HardCheck>()
        checks += when (agent.status) {
            AgentStatus.REVOKED -> HardCheck(false, "AGENT_REVOKED", "Agent access has been revoked")
            AgentStatus.FROZEN -> HardCheck(false, "AGENT_FROZEN", "Agent is frozen on this device")
            AgentStatus.ACTIVE -> HardCheck(true, "AGENT_AUTHORIZED", "Agent authorized")
        }
        if (request.category in policy.blockedCategories) {
            checks += HardCheck(false, "CATEGORY_BLOCKED", "Category ${request.category} is disabled")
        } else {
            checks += HardCheck(true, "CATEGORY_ALLOWED", "Category ${request.category} allowed")
        }
        if (request.merchant in policy.blockedMerchants) {
            checks += HardCheck(false, "MERCHANT_BLOCKED", "Merchant ${request.merchant} is prohibited")
        }
        if (request.amount > policy.transactionLimit) {
            checks += HardCheck(false, "LIMIT_TRANSACTION_EXCEEDED", "₹${request.amount} exceeds ₹${policy.transactionLimit} transaction limit")
        } else {
            checks += HardCheck(true, "LIMIT_WITHIN", "Within transaction limit")
        }
        val spend = todayApprovedSpend(history, request.agentId, nowMs)
        if (spend + request.amount > policy.dailyLimit) {
            checks += HardCheck(false, "LIMIT_DAILY_EXCEEDED", "Daily exposure would exceed ₹${policy.dailyLimit}")
        }
        return checks
    }

    fun velocityCount(history: List<TransactionRecord>, agentId: String, nowMs: Long): Int =
        history.count {
            it.request.agentId == agentId &&
                nowMs - it.request.timestampMs in 0..VELOCITY_WINDOW_MS
        }
}

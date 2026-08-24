package com.agentpay.guard.core.risk

import com.agentpay.guard.core.model.DecisionType
import com.agentpay.guard.core.model.PaymentRequest
import com.agentpay.guard.core.model.Policy
import com.agentpay.guard.core.model.RiskLevel
import com.agentpay.guard.core.model.TransactionRecord
import com.agentpay.guard.core.policy.PolicyEngine
import java.util.Calendar

data class RiskAssessment(val score: Int, val level: RiskLevel, val signals: List<String>)

object RiskEngine {

    fun assess(
        request: PaymentRequest,
        policy: Policy,
        history: List<TransactionRecord>,
        knownMerchants: Set<String>,
        nowMs: Long
    ): RiskAssessment {
        val signals = mutableListOf<String>()
        var score = 0

        if (request.merchant !in knownMerchants) {
            score += 22
            signals += "Merchant not previously approved"
        }

        val amountFactor = (request.amount.toDouble() / policy.transactionLimit * 20).toInt().coerceAtMost(20)
        score += amountFactor
        if (amountFactor >= 10) signals += "Amount close to transaction limit"

        val hour = Calendar.getInstance().apply { timeInMillis = request.timestampMs }.get(Calendar.HOUR_OF_DAY)
        if (hour < 8 || hour >= 21) {
            score += 12
            signals += "Unusual spending time"
        }

        val velocity = history.count {
            it.request.agentId == request.agentId &&
                nowMs - it.request.timestampMs in 0..PolicyEngine.VELOCITY_WINDOW_MS
        }
        if (velocity + 1 >= 3) {
            score += 15
            signals += "High velocity: ${velocity + 1} requests in 10 minutes"
        }

        val usedCategories = history.filter { it.request.agentId == request.agentId }.map { it.request.category }.toSet()
        if (request.category !in usedCategories) {
            score += 12
            signals += "Unfamiliar category for this agent: ${request.category}"
        }

        fun sameDay(a: Long, b: Long): Boolean {
            val calA = Calendar.getInstance().apply { timeInMillis = a }
            val calB = Calendar.getInstance().apply { timeInMillis = b }
            return calA.get(Calendar.DAY_OF_YEAR) == calB.get(Calendar.DAY_OF_YEAR) &&
                calA.get(Calendar.YEAR) == calB.get(Calendar.YEAR)
        }

        val blockedToday = history.any {
            it.request.agentId == request.agentId &&
                it.decision.decision == DecisionType.BLOCK &&
                sameDay(it.request.timestampMs, nowMs)
        }
        if (blockedToday) {
            score += 14
            signals += "Agent had a blocked action today"
        }

        val finalScore = score.coerceIn(0, 100)
        val level = when {
            finalScore < 25 -> RiskLevel.LOW
            finalScore < 50 -> RiskLevel.MEDIUM
            finalScore < 75 -> RiskLevel.HIGH
            else -> RiskLevel.CRITICAL
        }
        if (signals.isEmpty()) signals += "Activity within baseline"
        return RiskAssessment(finalScore, level, signals)
    }
}

package com.agentpay.guard.core.circumvention

import com.agentpay.guard.core.model.PaymentRequest
import com.agentpay.guard.core.model.Policy
import com.agentpay.guard.core.model.TransactionRecord
import com.agentpay.guard.core.policy.PolicyEngine

data class CircumventionResult(
    val detected: Boolean,
    val score: Int,
    val aggregateAmount: Long,
    val windowCount: Int
)

object CircumventionDetector {

    fun detect(request: PaymentRequest, policy: Policy, history: List<TransactionRecord>): CircumventionResult {
        val prior = history.filter { rec ->
            rec.decision.decision != com.agentpay.guard.core.model.DecisionType.BLOCK &&
                rec.request.agentId == request.agentId &&
                rec.request.sessionId == request.sessionId &&
                request.timestampMs - rec.request.timestampMs in 0..PolicyEngine.CIRCUMVENTION_WINDOW_MS &&
                (similarAmount(rec.request.amount, request.amount) || sameContext(rec.request, request))
        }
        val aggregate = prior.sumOf { it.request.amount } + request.amount

        if (prior.size >= 2 && aggregate >= 0.9 * policy.transactionLimit) {
            return CircumventionResult(
                detected = true,
                score = (55 + 15 * prior.size).coerceAtMost(100),
                aggregateAmount = aggregate,
                windowCount = prior.size + 1
            )
        }
        return CircumventionResult(
            detected = false,
            score = if (prior.isNotEmpty()) (prior.size * 20).coerceAtMost(60) else 0,
            aggregateAmount = aggregate,
            windowCount = prior.size + 1
        )
    }

    private fun similarAmount(a: Long, b: Long): Boolean {
        if (a <= 0) return false
        val diff = kotlin.math.abs(a - b).toDouble() / a
        return diff <= 0.15
    }

    private fun sameContext(a: PaymentRequest, b: PaymentRequest): Boolean =
        a.merchant == b.merchant && a.category == b.category
}

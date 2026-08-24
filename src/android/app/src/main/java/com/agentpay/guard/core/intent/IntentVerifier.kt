package com.agentpay.guard.core.intent

import com.agentpay.guard.core.model.IntentRecord
import com.agentpay.guard.core.model.PaymentRequest

data class IntentAssessment(
    val score: Int,
    val severe: Boolean,
    val warn: Boolean,
    val label: String
)

object IntentVerifier {
    fun verify(request: PaymentRequest, intents: List<IntentRecord>): IntentAssessment {
        val intent = intents.firstOrNull { it.intentId == request.intentId && it.agentId == request.agentId }
            ?: return IntentAssessment(50, severe = false, warn = false, label = "No linked intent")

        if (request.category != intent.category) {
            return IntentAssessment(
                15, severe = true, warn = true,
                label = "Category mismatch: intent ${intent.category}, got ${request.category}"
            )
        }
        if (request.amount > intent.budget * 3 / 2) {
            return IntentAssessment(15, severe = true, warn = true, label = "Amount far exceeds intent budget ₹${intent.budget}")
        }
        if (request.amount > intent.budget * 11 / 10) {
            return IntentAssessment(55, severe = false, warn = true, label = "Amount exceeds intent budget ₹${intent.budget}")
        }
        val headroom = ((intent.budget - request.amount).toDouble() / intent.budget.coerceAtLeast(1) * 20).toInt()
        return IntentAssessment((90 + headroom).coerceIn(90, 100), severe = false, warn = false, label = "Matches user intent")
    }
}

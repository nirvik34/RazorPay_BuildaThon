package com.agentpay.guard.demo

import com.agentpay.guard.core.model.PaymentRequest
import java.util.UUID

object DemoScenarios {

    fun normal(agentId: String = "agent-01", intentId: String? = null): PaymentRequest = PaymentRequest(
        agentId = agentId,
        intentId = intentId,
        merchant = "amazon",
        product = "Sony WH-1000XM5",
        amount = 14499,
        category = "electronics",
        sessionId = "sess_demo_normal"
    )

    fun overLimit(agentId: String = "agent-01"): PaymentRequest = PaymentRequest(
        agentId = agentId,
        merchant = "techmart",
        product = "MacBook Pro 14",
        amount = 42000,
        category = "electronics",
        sessionId = "sess_demo_overlimit"
    )

    fun intentMismatch(agentId: String = "agent-01", intentId: String? = null): PaymentRequest = PaymentRequest(
        agentId = agentId,
        intentId = intentId,
        merchant = "flipkart",
        product = "Amazon Pay Gift Card ₹10,000",
        amount = 10000,
        category = "gift_cards",
        sessionId = "sess_demo_intent"
    )

    fun splitting(step: Int, agentId: String = "agent-01"): PaymentRequest {
        val items = listOf(
            "Logitech MX Master 3S" to 9800L,
            "Keychron K3 Keyboard" to 9700L,
            "Anker USB-C Hub" to 9900L
        )
        val item = items[step.coerceIn(0, items.lastIndex)]
        return PaymentRequest(
            agentId = agentId,
            merchant = "croma",
            product = item.first,
            amount = item.second,
            category = "electronics",
            sessionId = "sess_split_" + UUID.randomUUID().toString().take(6)
        )
    }

    fun compromisedBurst(index: Int, agentId: String = "agent-01"): PaymentRequest = PaymentRequest(
        agentId = agentId,
        merchant = "dealsite${index % 3}",
        product = "Flash deal item ${index + 1}",
        amount = 1500 + index * 900L,
        category = if (index % 2 == 0) "electronics" else "groceries",
        sessionId = "sess_burst_" + UUID.randomUUID().toString().take(6)
    )
}


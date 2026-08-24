package com.agentpay.guard.core.model

import java.util.UUID

enum class AgentStatus { ACTIVE, FROZEN, REVOKED }
enum class RiskLevel { LOW, MEDIUM, HIGH, CRITICAL }
enum class DecisionType { ALLOW, USER_APPROVAL, BLOCK }
enum class RiskState { NORMAL, ELEVATED, CRITICAL }

val CATEGORY_BLOCKED_DEFAULT = listOf("gift_cards", "gambling", "cryptocurrency")
val CATEGORIES = listOf(
    "electronics", "groceries", "office_supplies", "fashion",
    "travel", "gift_cards", "gambling", "cryptocurrency"
)

data class Policy(
    val policyId: String = "pol_default",
    val version: Int = 3,
    val transactionLimit: Long = 20000,
    val dailyLimit: Long = 75000,
    val monthlyLimit: Long = 200000,
    val blockedCategories: List<String> = CATEGORY_BLOCKED_DEFAULT,
    val blockedMerchants: List<String> = emptyList(),
    val newMerchantApproval: Boolean = true,
    val internationalApproval: Boolean = true,
    val amountAbove: Long = 10000,
    val highRiskApproval: Boolean = true
)

data class Agent(
    val agentId: String,
    val name: String,
    val ownerId: String = "user_001",
    val status: AgentStatus = AgentStatus.ACTIVE,
    val trustScore: Int = 90,
    val riskState: RiskState = RiskState.NORMAL,
    val policyId: String = "pol_default",
    val publicKey: String? = null
)

data class IntentRecord(
    val intentId: String,
    val agentId: String,
    val goal: String,
    val category: String,
    val budget: Long
)

data class PaymentRequest(
    val requestId: String = "req_" + UUID.randomUUID().toString().take(6),
    val agentId: String,
    val intentId: String? = null,
    val merchant: String,
    val product: String,
    val amount: Long,
    val currency: String = "INR",
    val category: String,
    val sessionId: String = "sess_" + UUID.randomUUID().toString().take(8),
    val timestampMs: Long = System.currentTimeMillis()
)

data class ReasonCode(val code: String, val label: String, val severity: Severity) {
    enum class Severity { OK, WARN, BLOCK }
}

data class GuardDecision(
    val requestId: String,
    val decision: DecisionType,
    val reasonCodes: List<ReasonCode>,
    val riskScore: Int,
    val intentScore: Int,
    val circumventionScore: Int,
    val policyVersion: Int,
    val authorizationId: String? = null,
    val timestampMs: Long = System.currentTimeMillis()
) {
    fun blockReason(): ReasonCode? = reasonCodes.firstOrNull { it.severity == ReasonCode.Severity.BLOCK }
    fun riskLevel(): RiskLevel = when {
        riskScore < 25 -> RiskLevel.LOW
        riskScore < 50 -> RiskLevel.MEDIUM
        riskScore < 75 -> RiskLevel.HIGH
        else -> RiskLevel.CRITICAL
    }
}

data class Authorization(
    val authorizationId: String,
    val requestId: String,
    val agentId: String,
    val merchant: String,
    val product: String,
    val amount: Long,
    val intentId: String?,
    val issuedAtMs: Long,
    val expiresAtMs: Long,
    val status: Status,
    val signature: String? = null
) {
    enum class Status { AUTHORIZED, USED, EXPIRED }
}

data class AuditEvent(
    val eventId: String = UUID.randomUUID().toString(),
    val requestId: String,
    val atMs: Long,
    val label: String,
    val detail: String? = null,
    val synced: Boolean = false
)

data class TransactionRecord(
    val request: PaymentRequest,
    val decision: GuardDecision,
    val outcome: Outcome,
    val decidedBy: DecidedBy,
    val userActionAtMs: Long? = null,
    val authorizationId: String? = null
) {
    enum class Outcome { CAPTURED, PROCESSING, FAILED, DENIED, NOT_ATTEMPTED }
    enum class DecidedBy { USER, POLICY }

    val isPendingApproval: Boolean
        get() = decision.decision == DecisionType.USER_APPROVAL && userActionAtMs == null
}

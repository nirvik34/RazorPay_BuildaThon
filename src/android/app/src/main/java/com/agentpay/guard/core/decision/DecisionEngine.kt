package com.agentpay.guard.core.decision

import com.agentpay.guard.core.circumvention.CircumventionDetector
import com.agentpay.guard.core.intent.IntentAssessment
import com.agentpay.guard.core.intent.IntentVerifier
import com.agentpay.guard.core.model.Agent
import com.agentpay.guard.core.model.DecisionType
import com.agentpay.guard.core.model.GuardDecision
import com.agentpay.guard.core.model.IntentRecord
import com.agentpay.guard.core.model.PaymentRequest
import com.agentpay.guard.core.model.Policy
import com.agentpay.guard.core.model.ReasonCode
import com.agentpay.guard.core.model.TransactionRecord
import com.agentpay.guard.core.risk.RiskEngine
import com.agentpay.guard.core.policy.PolicyEngine

data class Evaluation(
    val decision: GuardDecision,
    val riskSignals: List<String>,
    val circumventionAggregate: Long,
    val circumventionWindow: Int
)

object DecisionEngine {

    /**
     * Builds the ML feature vector (name → raw value) matching
     * src/ml FEATURE_COLUMNS order-independent by name. The exported model's
     * scaler + feature list handle ordering on the runtime side.
     */
    fun extractFeatureVector(
        request: PaymentRequest,
        policy: Policy,
        history: List<TransactionRecord>,
        knownMerchants: Set<String>,
        nowMs: Long
    ): Map<String, Float> {
        val merchantKnown = if (request.merchant in knownMerchants) 1f else 0f
        val categoryAllowed = if (request.category !in policy.blockedCategories) 1f else 0f
        val amountRatio = request.amount.toFloat() / policy.transactionLimit
        val hour = java.util.Calendar.getInstance().apply { timeInMillis = request.timestampMs }
            .get(java.util.Calendar.HOUR_OF_DAY)
        val velocity = PolicyEngine.velocityCount(history, request.agentId, nowMs)
        val usedCategories = history
            .filter { it.request.agentId == request.agentId }
            .map { it.request.category }
            .toSet()
        val categoryFamiliar = if (request.category in usedCategories) 1f else 0f
        val priorBlocks = history.count {
            it.request.agentId == request.agentId &&
                it.decision.decision == DecisionType.BLOCK &&
                sameDay(it.request.timestampMs, nowMs)
        }
        val night = if (hour < 8 || hour >= 21) 1f else 0f
        return mapOf(
            "merchant_known" to merchantKnown,
            "category_allowed" to categoryAllowed,
            "amount_ratio" to amountRatio,
            "hour" to hour.toFloat(),
            "velocity_10m" to velocity.toFloat(),
            "category_familiar" to categoryFamiliar,
            "prior_blocks_today" to priorBlocks.toFloat(),
            "night_hour" to night,
            "velocity_x_amount" to velocity * amountRatio,
            "novelty_pressure" to (1f - merchantKnown) * (1f - categoryFamiliar) * night
        )
    }

    private fun sameDay(a: Long, b: Long): Boolean {
        val calA = java.util.Calendar.getInstance().apply { timeInMillis = a }
        val calB = java.util.Calendar.getInstance().apply { timeInMillis = b }
        return calA.get(java.util.Calendar.DAY_OF_YEAR) == calB.get(java.util.Calendar.DAY_OF_YEAR) &&
            calA.get(java.util.Calendar.YEAR) == calB.get(java.util.Calendar.YEAR)
    }

    fun evaluate(
        request: PaymentRequest,
        agent: Agent,
        policy: Policy,
        history: List<TransactionRecord>,
        intents: List<IntentRecord>,
        nowMs: Long = System.currentTimeMillis(),
        mlScore: Float? = null
    ): Evaluation {
        val known = PolicyEngine.knownMerchants(history)
        val risk = RiskEngine.assess(request, policy, history, known, nowMs)
        val circumvention = CircumventionDetector.detect(request, policy, history)
        val intent = IntentVerifier.verify(request, intents)

        val reasons = mutableListOf<ReasonCode>()
        val hardChecks = PolicyEngine.evaluateHardChecks(request, agent, policy, history, nowMs)
        for (check in hardChecks) {
            when {
                check.code == "MERCHANT_BLOCKED" ->
                    reasons += ReasonCode(check.code, check.label, ReasonCode.Severity.BLOCK)
                !check.passed && check.code in BLOCK_CODES ->
                    reasons += ReasonCode(check.code, check.label, ReasonCode.Severity.BLOCK)
                check.code == "AGENT_AUTHORIZED" || check.code == "CATEGORY_ALLOWED" || check.code == "LIMIT_WITHIN" ->
                    reasons += ReasonCode(check.code, check.label, ReasonCode.Severity.OK)
            }
        }

        val merchantKnown = request.merchant in known
        if (!merchantKnown && agent.status == com.agentpay.guard.core.model.AgentStatus.ACTIVE) {
            reasons += ReasonCode("NEW_MERCHANT", "New merchant requires review", ReasonCode.Severity.WARN)
        } else if (merchantKnown) {
            reasons += ReasonCode("MERCHANT_KNOWN", "Known merchant", ReasonCode.Severity.OK)
        }
        reasons += when {
            intent.severe -> ReasonCode("INTENT_MISMATCH", intent.label, ReasonCode.Severity.BLOCK)
            intent.warn -> ReasonCode("BUDGET_WARN", intent.label, ReasonCode.Severity.WARN)
            else -> ReasonCode("BUDGET_VALID", intent.label, ReasonCode.Severity.OK)
        }
        if (circumvention.detected) {
            reasons += ReasonCode(
                "CIRCUMVENTION_DETECTED",
                "Split pattern: ${circumvention.windowCount} payments, aggregate ₹${circumvention.aggregateAmount} vs ₹${policy.transactionLimit} limit",
                ReasonCode.Severity.BLOCK
            )
        }

        var decision = DecisionType.ALLOW

        for (check in hardChecks) {
            if (!check.passed) {
                decision = DecisionType.BLOCK
                break
            }
        }
        if (decision == DecisionType.ALLOW && intent.severe) decision = DecisionType.BLOCK
        if (decision == DecisionType.ALLOW && circumvention.detected) decision = DecisionType.BLOCK

        if (decision == DecisionType.ALLOW) {
            when {
                !merchantKnown && policy.newMerchantApproval -> decision = DecisionType.USER_APPROVAL
                request.amount >= policy.amountAbove -> {
                    reasons += ReasonCode(
                        "AMOUNT_REQUIRES_APPROVAL",
                        "Amount at or above ₹${policy.amountAbove} approval threshold",
                        ReasonCode.Severity.WARN
                    )
                    decision = DecisionType.USER_APPROVAL
                }
                (risk.level == com.agentpay.guard.core.model.RiskLevel.HIGH || risk.level == com.agentpay.guard.core.model.RiskLevel.CRITICAL) && policy.highRiskApproval -> {
                    reasons += ReasonCode("HIGH_RISK", "Risk ${risk.level}", ReasonCode.Severity.WARN)
                    decision = DecisionType.USER_APPROVAL
                }
                else -> reasons += ReasonCode("POLICY_PASSED", "Policy checks passed", ReasonCode.Severity.OK)
            }
        }

        // Blend the on-device ML probability with the heuristic score 50/50
        // when a trained model bundle is present in assets.
        val blendedRisk = mlScore?.let { ml ->
            ((risk.score + ml * 100f) / 2f).toInt().coerceIn(0, 100)
        } ?: risk.score
        val signals = if (mlScore != null && mlScore >= 0) {
            risk.signals + "ML risk model: ${(mlScore * 100).toInt()}% probability"
        } else risk.signals

        return Evaluation(
            decision = GuardDecision(
                requestId = request.requestId,
                decision = decision,
                reasonCodes = reasons,
                riskScore = blendedRisk,
                intentScore = intent.score,
                circumventionScore = circumvention.score,
                policyVersion = policy.version,
                timestampMs = nowMs
            ),
            riskSignals = signals,
            circumventionAggregate = circumvention.aggregateAmount,
            circumventionWindow = circumvention.windowCount
        )
    }

    private val BLOCK_CODES = setOf(
        "AGENT_REVOKED", "AGENT_FROZEN", "CATEGORY_BLOCKED", "MERCHANT_BLOCKED",
        "LIMIT_TRANSACTION_EXCEEDED", "LIMIT_DAILY_EXCEEDED"
    )
}

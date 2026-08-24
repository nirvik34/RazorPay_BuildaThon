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
import com.agentpay.guard.core.risk.RiskEngine
import com.agentpay.guard.core.policy.PolicyEngine

data class Evaluation(
    val decision: GuardDecision,
    val riskSignals: List<String>,
    val circumventionAggregate: Long,
    val circumventionWindow: Int
)

object DecisionEngine {

    fun evaluate(
        request: PaymentRequest,
        agent: Agent,
        policy: Policy,
        history: List<TransactionRecord>,
        intents: List<IntentRecord>,
        nowMs: Long = System.currentTimeMillis()
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

        return Evaluation(
            decision = GuardDecision(
                requestId = request.requestId,
                decision = decision,
                reasonCodes = reasons,
                riskScore = risk.score,
                intentScore = intent.score,
                circumventionScore = circumvention.score,
                policyVersion = policy.version,
                timestampMs = nowMs
            ),
            riskSignals = risk.signals,
            circumventionAggregate = circumvention.aggregateAmount,
            circumventionWindow = circumvention.windowCount
        )
    }

    private val BLOCK_CODES = setOf(
        "AGENT_REVOKED", "AGENT_FROZEN", "CATEGORY_BLOCKED", "MERCHANT_BLOCKED",
        "LIMIT_TRANSACTION_EXCEEDED", "LIMIT_DAILY_EXCEEDED"
    )
}

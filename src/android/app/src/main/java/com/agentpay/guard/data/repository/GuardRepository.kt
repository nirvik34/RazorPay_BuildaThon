package com.agentpay.guard.data.repository

import android.content.Context
import com.agentpay.guard.core.model.Agent
import com.agentpay.guard.core.model.AgentStatus
import com.agentpay.guard.core.model.AuditEvent
import com.agentpay.guard.core.model.Authorization
import com.agentpay.guard.core.model.DecisionType
import com.agentpay.guard.core.model.GuardDecision
import com.agentpay.guard.core.model.IntentRecord
import com.agentpay.guard.core.model.PaymentRequest
import com.agentpay.guard.core.model.Policy
import com.agentpay.guard.core.model.TransactionRecord
import com.agentpay.guard.core.decision.DecisionEngine
import com.agentpay.guard.data.local.AgentsDao
import com.agentpay.guard.data.local.AuditDao
import com.agentpay.guard.data.local.AuditEventEntity
import com.agentpay.guard.data.local.DecisionEntity
import com.agentpay.guard.data.local.DecisionsDao
import com.agentpay.guard.data.local.GuardDatabase
import com.agentpay.guard.data.local.IntentEntity
import com.agentpay.guard.data.local.IntentsDao
import com.agentpay.guard.data.local.RequestEntity
import com.agentpay.guard.data.local.RequestsDao
import com.agentpay.guard.security.keystore.KeystoreManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class GuardRepository(
    private val agentsDao: AgentsDao,
    private val requestsDao: RequestsDao,
    private val decisionsDao: DecisionsDao,
    private val auditDao: AuditDao,
    private val intentsDao: IntentsDao
) {
    val keystore = KeystoreManager.get()

    fun defaultPolicy(): Policy = GuardDatabase.defaultPolicy()
    
    suspend fun intents(): List<IntentRecord> = withContext(Dispatchers.IO) {
        intentsDao.all().map { entity -> entity.toModel() }
    }

    suspend fun seedIfEmpty() {
        // Dynamic: Agents & intents are fetched via LiveSync or registered dynamically.
    }

    suspend fun agents(): List<Agent> = withContext(Dispatchers.IO) { agentsDao.all().map { entity -> entity.toModel() } }

    suspend fun upsertAgent(agent: Agent) = withContext(Dispatchers.IO) {
        agentsDao.upsert(com.agentpay.guard.data.local.AgentEntity.from(agent))
    }


    suspend fun upsertAgents(agents: List<Agent>) = withContext(Dispatchers.IO) {
        agents.forEach { item -> agentsDao.upsert(com.agentpay.guard.data.local.AgentEntity.from(item)) }
    }

    suspend fun upsertIntents(intentsList: List<IntentRecord>) = withContext(Dispatchers.IO) {
        intentsList.forEach { item -> intentsDao.upsert(IntentEntity.from(item)) }
    }


    suspend fun setAgentStatus(agentId: String, status: AgentStatus, note: String) {
        withContext(Dispatchers.IO) {
            agentsDao.setStatus(agentId, status.name)
            val events = listOf(
                AuditEvent(requestId = "system", atMs = System.currentTimeMillis(), label = note, detail = agentId)
            )
            auditDao.insertAll(events.map(AuditEventEntity::from))
        }
    }

    suspend fun history(nowMs: Long = System.currentTimeMillis()): List<TransactionRecord> =
        withContext(Dispatchers.IO) {
            val requests = requestsDao.all().associateBy { it.requestId }
            val decisions = decisionsDao.all().associateBy { it.requestId }

            requests.values.mapNotNull { req ->
                val entity = decisions[req.requestId] ?: return@mapNotNull null
                val decision = entity.toModel()
                val denied = entity.denied
                TransactionRecord(
                    request = req.toModel(),
                    decision = decision,
                    outcome = when {
                        decision.decision == DecisionType.BLOCK -> TransactionRecord.Outcome.NOT_ATTEMPTED
                        decision.decision == DecisionType.ALLOW -> TransactionRecord.Outcome.CAPTURED
                        denied -> TransactionRecord.Outcome.DENIED
                        entity.authorizationId != null -> TransactionRecord.Outcome.CAPTURED
                        else -> TransactionRecord.Outcome.NOT_ATTEMPTED
                    },
                    decidedBy = if (decision.decision == DecisionType.BLOCK) TransactionRecord.DecidedBy.POLICY else TransactionRecord.DecidedBy.USER,
                    userActionAtMs = entity.userActionAtMs
                )
            }
        }

    suspend fun submitRequest(request: PaymentRequest): EvaluationResult = withContext(Dispatchers.IO) {
        var agent = agentsDao.byId(request.agentId)?.toModel()
        if (agent == null) {
            val newAgent = Agent(
                agentId = request.agentId,
                name = request.agentId.replace("-", " ").replace("_", " ").capitalize(java.util.Locale.ROOT),
                trustScore = 85
            )
            agentsDao.upsert(com.agentpay.guard.data.local.AgentEntity.from(newAgent))
            agent = newAgent
        }
        val policy = defaultPolicy()
        val intentsList = intents()
        val history = history(request.timestampMs)

        val known = com.agentpay.guard.core.policy.PolicyEngine.knownMerchants(history)
        val featureVector = DecisionEngine.extractFeatureVector(
            request, policy, history, known, request.timestampMs
        )
        val mlScore = com.agentpay.guard.ml.MLRuntime.predict(featureVector)
            .takeIf { it >= 0f }
        val evaluation = DecisionEngine.evaluate(
            request, agent, policy, history, intentsList, request.timestampMs, mlScore
        )
        val decision = evaluation.decision

        requestsDao.insert(RequestEntity.from(request))
        decisionsDao.insert(DecisionEntity.from(decision))

        val baseEvents = mutableListOf<AuditEvent>()
        var at = request.timestampMs
        baseEvents += AuditEvent(requestId = request.requestId, atMs = at, label = "Payment request received", detail = request.product)
        baseEvents += AuditEvent(requestId = request.requestId, atMs = at, label = "Agent authenticated", detail = request.agentId)
        baseEvents += AuditEvent(requestId = request.requestId, atMs = at, label = "Policy evaluated", detail = "v${policy.version}")
        baseEvents += AuditEvent(requestId = request.requestId, atMs = at, label = "Risk assessed", detail = "${decision.riskLevel()} · ${decision.riskScore}/100")

        when (decision.decision) {
            DecisionType.BLOCK -> {
                baseEvents += AuditEvent(requestId = request.requestId, atMs = at, label = decision.blockReason()?.label ?: "Blocked by policy", detail = decision.blockReason()?.code)
                baseEvents += AuditEvent(requestId = request.requestId, atMs = at + 1000, label = "No approval requested", detail = "Hard policy violation")
                baseEvents += AuditEvent(requestId = request.requestId, atMs = at + 2000, label = "Agent informed", detail = "Structured denial returned")
            }
            DecisionType.USER_APPROVAL -> {
                baseEvents += AuditEvent(requestId = request.requestId, atMs = at + 1000, label = "User notified")
                baseEvents += AuditEvent(requestId = request.requestId, atMs = at + 2000, label = "Awaiting user decision")
            }
            DecisionType.ALLOW -> {
                baseEvents += AuditEvent(requestId = request.requestId, atMs = at, label = "Auto-authorized within policy")
            }
        }
        auditDao.insertAll(baseEvents.map(AuditEventEntity::from))
        return@withContext EvaluationResult(decision, evaluation.riskSignals)
    }

    data class EvaluationResult(val decision: GuardDecision?, val riskSignals: List<String>)

    suspend fun decide(request: PaymentRequest, accept: Boolean): Authorization? = withContext(Dispatchers.IO) {
        val now = System.currentTimeMillis()
        if (!accept) {
            decisionsDao.resolve(request.requestId, now, denied = true)
            auditDao.insertAll(listOf(
                AuditEventEntity.from(AuditEvent(requestId = request.requestId, atMs = now, label = "User rejected transaction")),
                AuditEventEntity.from(AuditEvent(requestId = request.requestId, atMs = now, label = "Authorization denied")),
                AuditEventEntity.from(AuditEvent(requestId = request.requestId, atMs = now + 1000, label = "Agent informed", detail = "Structured denial returned"))
            ))
            return@withContext null
        }
        val authorizationId = "auth_" + java.util.UUID.randomUUID().toString().replace("-", "").take(6)
        val payload = "$authorizationId|${request.requestId}|${request.merchant}|${request.amount}|$now"
        val authorization = Authorization(
            authorizationId = authorizationId,
            requestId = request.requestId,
            agentId = request.agentId,
            merchant = request.merchant,
            product = request.product,
            amount = request.amount,
            intentId = request.intentId,
            issuedAtMs = now,
            expiresAtMs = now + TTL_MS,
            status = Authorization.Status.AUTHORIZED,
            signature = keystore.sign(payload)
        )
        decisionsDao.setAuthorization(request.requestId, authorizationId)
        decisionsDao.resolve(request.requestId, now, denied = false)
        auditDao.insertAll(listOf(
            AuditEventEntity.from(AuditEvent(requestId = request.requestId, atMs = now, label = "User accepted")),
            AuditEventEntity.from(AuditEvent(requestId = request.requestId, atMs = now, label = "Authorization issued", detail = authorizationId)),
            AuditEventEntity.from(AuditEvent(requestId = request.requestId, atMs = now + 6000, label = "Payment initiated", detail = "Razorpay order created")),
            AuditEventEntity.from(AuditEvent(requestId = request.requestId, atMs = now + 9000, label = "Payment captured", detail = authorizationId))
        ))
        return@withContext authorization
    }

    suspend fun requestById(requestId: String): PaymentRequest? =
        withContext(Dispatchers.IO) { requestsDao.byId(requestId)?.toModel() }

    suspend fun hasRequest(requestId: String): Boolean =
        withContext(Dispatchers.IO) { requestsDao.byId(requestId) != null }

    suspend fun pendingRequests(history: List<TransactionRecord>): List<TransactionRecord> =
        history.filter { it.isPendingApproval }

    suspend fun auditFor(requestId: String): List<AuditEvent> =
        withContext(Dispatchers.IO) { auditDao.forRequest(requestId).map { it.toModel() } }

    suspend fun unsyncedAudit(): List<AuditEvent> =
        withContext(Dispatchers.IO) { auditDao.unsynced().map { it.toModel() } }

    suspend fun markSynced(events: List<AuditEvent>) =
        withContext(Dispatchers.IO) { auditDao.markSynced(events.map { it.eventId }) }

    companion object {
        const val TTL_MS = 5 * 60_000L

        @Volatile private var instance: GuardRepository? = null

        fun get(context: Context): GuardRepository {
            instance ?: synchronized(this) {
                val db = GuardDatabase.build(context.applicationContext)
                instance ?: GuardRepository(db.agentsDao(), db.requestsDao(), db.decisionsDao(), db.auditDao(), db.intentsDao()).also { instance = it }
            }
            return instance!!
        }
    }
}


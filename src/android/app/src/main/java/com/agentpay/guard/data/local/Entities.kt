package com.agentpay.guard.data.local

import androidx.room.Dao
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.Update
import com.agentpay.guard.core.model.Agent
import com.agentpay.guard.core.model.AgentStatus
import com.agentpay.guard.core.model.AuditEvent
import com.agentpay.guard.core.model.Authorization
import com.agentpay.guard.core.model.DecisionType
import com.agentpay.guard.core.model.GuardDecision
import com.agentpay.guard.core.model.IntentRecord
import com.agentpay.guard.core.model.PaymentRequest
import com.agentpay.guard.core.model.Policy
import com.agentpay.guard.core.model.ReasonCode
import com.agentpay.guard.core.model.RiskState
import com.agentpay.guard.core.model.TransactionRecord
import org.json.JSONArray

@Entity(tableName = "agents")
data class AgentEntity(
    @PrimaryKey val agentId: String,
    val name: String,
    val ownerId: String,
    val status: String,
    val trustScore: Int,
    val riskState: String,
    val policyId: String,
    val publicKeyEncrypted: String? = null
) {
    fun toModel(): Agent = Agent(
        agentId = agentId, name = name, ownerId = ownerId,
        status = AgentStatus.valueOf(status), trustScore = trustScore,
        riskState = RiskState.valueOf(riskState), policyId = policyId
    )

    companion object {
        fun from(model: Agent, encryptedKey: String? = null) = AgentEntity(
            model.agentId, model.name, model.ownerId, model.status.name,
            model.trustScore, model.riskState.name, model.policyId, encryptedKey
        )
    }
}

@Entity(tableName = "requests")
data class RequestEntity(
    @PrimaryKey val requestId: String,
    val agentId: String,
    val intentId: String?,
    val merchant: String,
    val product: String,
    val amount: Long,
    val currency: String,
    val category: String,
    val sessionId: String,
    val timestampMs: Long
) {
    fun toModel() = PaymentRequest(
        requestId, agentId, intentId, merchant, product, amount, currency, category, sessionId, timestampMs
    )

    companion object {
        fun from(m: PaymentRequest) = RequestEntity(
            m.requestId, m.agentId, m.intentId, m.merchant, m.product, m.amount, m.currency, m.category, m.sessionId, m.timestampMs
        )
    }
}

@Entity(tableName = "decisions")
data class DecisionEntity(
    @PrimaryKey val requestId: String,
    val decision: String,
    val reasonCodesJson: String,
    val riskScore: Int,
    val intentScore: Int,
    val circumventionScore: Int,
    val policyVersion: Int,
    val authorizationId: String?,
    val timestampMs: Long,
    val userActionAtMs: Long? = null,
    val denied: Boolean = false
) {
    fun toModel(): GuardDecision {
        val array = JSONArray(reasonCodesJson)
        val reasons = (0 until array.length()).map { i ->
            val obj = array.getJSONObject(i)
            ReasonCode(obj.getString("code"), obj.getString("label"), ReasonCode.Severity.valueOf(obj.getString("severity")))
        }
        return GuardDecision(requestId, DecisionType.valueOf(decision), reasons, riskScore, intentScore, circumventionScore, policyVersion, authorizationId, timestampMs)
    }

    companion object {
        fun from(m: GuardDecision, userActionAtMs: Long? = null, denied: Boolean = false): DecisionEntity {
            val array = JSONArray()
            for (r in m.reasonCodes) {
                array.put(org.json.JSONObject().put("code", r.code).put("label", r.label).put("severity", r.severity.name))
            }
            return DecisionEntity(
                m.requestId, m.decision.name, array.toString(), m.riskScore,
                m.intentScore, m.circumventionScore, m.policyVersion, m.authorizationId, m.timestampMs,
                userActionAtMs, denied
            )
        }
    }
}

@Entity(tableName = "audit_events")
data class AuditEventEntity(
    @PrimaryKey val eventId: String,
    val requestId: String,
    val atMs: Long,
    val label: String,
    val detail: String?,
    val synced: Boolean
) {
    fun toModel() = AuditEvent(eventId, requestId, atMs, label, detail, synced)

    companion object {
        fun from(m: AuditEvent) = AuditEventEntity(m.eventId, m.requestId, m.atMs, m.label, m.detail, m.synced)
    }
}

@Dao
interface AgentsDao {
    @Query("SELECT * FROM agents")
    suspend fun all(): List<AgentEntity>

    @Query("SELECT * FROM agents WHERE agentId = :id")
    suspend fun byId(id: String): AgentEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(agent: AgentEntity)

    @Query("UPDATE agents SET status = :status WHERE agentId = :agentId")
    suspend fun setStatus(agentId: String, status: String)

    @Query("SELECT COUNT(*) FROM agents")
    suspend fun count(): Int
}

@Dao
interface RequestsDao {
    @Query("SELECT * FROM requests ORDER BY timestampMs DESC")
    suspend fun all(): List<RequestEntity>

    @Query("SELECT * FROM requests WHERE requestId = :id")
    suspend fun byId(id: String): RequestEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(request: RequestEntity)
}

@Dao
interface DecisionsDao {
    @Query("SELECT * FROM decisions")
    suspend fun all(): List<DecisionEntity>

    @Query("SELECT * FROM decisions WHERE requestId = :id")
    suspend fun byRequestId(id: String): DecisionEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(decision: DecisionEntity)

    @Update
    suspend fun update(decision: DecisionEntity)

    @Query("UPDATE decisions SET authorizationId = :authId WHERE requestId = :requestId")
    suspend fun setAuthorization(requestId: String, authId: String?)

    @Query("UPDATE decisions SET userActionAtMs = :atMs, denied = :denied WHERE requestId = :requestId")
    suspend fun resolve(requestId: String, atMs: Long, denied: Boolean)

    @Query("SELECT * FROM decisions WHERE decision = 'USER_APPROVAL' AND userActionAtMs IS NULL")
    suspend fun pending(): List<DecisionEntity>
}

@Dao
interface AuditDao {
    @Query("SELECT * FROM audit_events WHERE requestId = :requestId ORDER BY atMs ASC")
    suspend fun forRequest(requestId: String): List<AuditEventEntity>

    @Query("SELECT * FROM audit_events WHERE synced = 0 LIMIT 200")
    suspend fun unsynced(): List<AuditEventEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(events: List<AuditEventEntity>)

    @Query("UPDATE audit_events SET synced = 1 WHERE eventId IN (:eventIds)")
    suspend fun markSynced(eventIds: List<String>)
}

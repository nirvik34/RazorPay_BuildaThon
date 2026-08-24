package com.agentpay.guard.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.agentpay.guard.core.model.Agent
import com.agentpay.guard.core.model.IntentRecord
import com.agentpay.guard.core.model.Policy

@Database(
    entities = [AgentEntity::class, RequestEntity::class, DecisionEntity::class, AuditEventEntity::class],
    version = 1,
    exportSchema = false
)
abstract class GuardDatabase : RoomDatabase() {
    abstract fun agentsDao(): AgentsDao
    abstract fun requestsDao(): RequestsDao
    abstract fun decisionsDao(): DecisionsDao
    abstract fun auditDao(): AuditDao

    companion object {
        fun build(context: Context): GuardDatabase =
            Room.databaseBuilder(context, GuardDatabase::class.java, "agentpay-guard.db")
                .fallbackToDestructiveMigration()
                .build()

        fun defaultPolicy(): Policy = Policy()

        fun defaultAgents(): List<Agent> = listOf(
            Agent("claude-shopping-01", "Claude Shopping Agent", trustScore = 94),
            Agent("gemini-shopping-02", "Gemini Shopping Agent", trustScore = 81),
            Agent("gpt-assistant-03", "ChatGPT Assistant", trustScore = 88)
        )

        fun defaultIntents(): List<IntentRecord> = listOf(
            IntentRecord(
                intentId = "intent_183",
                agentId = "claude-shopping-01",
                goal = "Find me noise-cancelling headphones under ₹15,000.",
                category = "electronics",
                budget = 15000
            )
        )
    }
}

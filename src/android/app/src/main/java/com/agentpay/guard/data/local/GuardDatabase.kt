package com.agentpay.guard.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.agentpay.guard.core.model.Agent
import com.agentpay.guard.core.model.IntentRecord
import com.agentpay.guard.core.model.Policy

@Database(
    entities = [AgentEntity::class, RequestEntity::class, DecisionEntity::class, AuditEventEntity::class, IntentEntity::class],
    version = 2,
    exportSchema = false
)
abstract class GuardDatabase : RoomDatabase() {
    abstract fun agentsDao(): AgentsDao
    abstract fun requestsDao(): RequestsDao
    abstract fun decisionsDao(): DecisionsDao
    abstract fun auditDao(): AuditDao
    abstract fun intentsDao(): IntentsDao

    companion object {
        fun build(context: Context): GuardDatabase =
            Room.databaseBuilder(context, GuardDatabase::class.java, "agentpay-guard.db")
                .fallbackToDestructiveMigration()
                .build()

        fun defaultPolicy(): Policy = Policy()

        fun defaultAgents(): List<Agent> = emptyList()

        fun defaultIntents(): List<IntentRecord> = emptyList()
    }
}


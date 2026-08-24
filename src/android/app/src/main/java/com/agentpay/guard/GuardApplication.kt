package com.agentpay.guard

import android.app.Application
import com.agentpay.guard.notifications.NotificationHelper
import com.agentpay.guard.sync.SyncWorker

class GuardApplication : Application() {

    override fun onCreate() {
        super.onCreate()
        NotificationHelper.ensureChannel(this)
        SyncWorker.schedule(this)
    }
}

package com.agentpay.guard.net

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.net.wifi.WifiManager
import com.agentpay.guard.GuardGraph
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.HttpURLConnection
import java.net.InetAddress
import java.net.NetworkInterface
import java.net.URL
import java.util.Collections
import kotlin.coroutines.resume

object ServerDiscovery {

    suspend fun discover(context: Context): String? = withContext(Dispatchers.IO) {
        // 1. Try current configured URL first (fastest if user already set it or previously discovered)
        val currentUrl = GuardGraph.backendBaseUrl
        if (verifyHealth(currentUrl)) {
            return@withContext currentUrl
        }

        // 1.5. Try public ntfy relay URL (works across different networks / ngrok tunnels)
        val ntfyResult = discoverViaNtfy()
        if (ntfyResult != null && verifyHealth(ntfyResult)) {
            GuardGraph.setBackendBaseUrl(context, ntfyResult)
            return@withContext ntfyResult
        }

        // 2. Try UDP discovery
        val udpResult = discoverViaUdp()
        if (udpResult != null && verifyHealth(udpResult)) {
            GuardGraph.setBackendBaseUrl(context, udpResult)
            return@withContext udpResult
        }

        // 3. Try mDNS / Zeroconf discovery via NsdManager
        val mdnsResult = discoverViaMdns(context)
        if (mdnsResult != null && verifyHealth(mdnsResult)) {
            GuardGraph.setBackendBaseUrl(context, mdnsResult)
            return@withContext mdnsResult
        }

        // 4. Try emulator host (http://10.0.2.2:8000)
        val emulatorUrl = "http://10.0.2.2:8000"
        if (verifyHealth(emulatorUrl)) {
            GuardGraph.setBackendBaseUrl(context, emulatorUrl)
            return@withContext emulatorUrl
        }

        // 5. Try local subnet scan
        val subnetResult = scanLocalSubnet(context)
        if (subnetResult != null) {
            GuardGraph.setBackendBaseUrl(context, subnetResult)
            return@withContext subnetResult
        }

        null
    }

    private fun discoverViaNtfy(): String? {
        return try {
            val url = URL("https://ntfy.sh/agentpay_guard_hub_relay/raw?poll=1")
            val conn = (url.openConnection() as HttpURLConnection).apply {
                connectTimeout = 3000
                readTimeout = 3000
                requestMethod = "GET"
            }
            if (conn.responseCode == 200) {
                val text = conn.inputStream.bufferedReader().use { it.readText() }
                conn.disconnect()
                val lines = text.lineSequence()
                    .map { it.trim() }
                    .filter { it.startsWith("http://") || it.startsWith("https://") }
                    .toList()
                lines.lastOrNull()
            } else {
                conn.disconnect()
                null
            }
        } catch (e: Exception) {
            null
        }
    }

    private fun discoverViaUdp(): String? {
        return try {
            val socket = DatagramSocket().apply {
                soTimeout = 800
                broadcast = true
            }
            val requestData = "AGENTPAY_GUARD_DISCOVER".toByteArray()
            val packet = DatagramPacket(
                requestData,
                requestData.size,
                InetAddress.getByName("255.255.255.255"),
                8001
            )
            socket.send(packet)

            val buffer = ByteArray(1024)
            val receivePacket = DatagramPacket(buffer, buffer.size)
            socket.receive(receivePacket)
            socket.close()

            val msg = String(receivePacket.data, 0, receivePacket.length).trim()
            if (msg.startsWith("AGENTPAY_GUARD_SERVER:")) {
                msg.removePrefix("AGENTPAY_GUARD_SERVER:")
            } else null
        } catch (e: Exception) {
            null
        }
    }

    private suspend fun discoverViaMdns(context: Context): String? = withContext(Dispatchers.IO) {
        try {
            val nsdManager = context.applicationContext.getSystemService(Context.NSD_SERVICE) as? NsdManager
                ?: return@withContext null

            suspendCancellableCoroutine<String?> { continuation ->
                var isResumed = false

                val resolveListener = object : NsdManager.ResolveListener {
                    override fun onResolveFailed(serviceInfo: NsdServiceInfo?, errorCode: Int) {
                        if (!isResumed) {
                            isResumed = true
                            if (continuation.isActive) continuation.resume(null)
                        }
                    }

                    override fun onServiceResolved(serviceInfo: NsdServiceInfo?) {
                        val host = serviceInfo?.host?.hostAddress
                        val port = serviceInfo?.port ?: 8000
                        val result = if (host != null) "http://$host:$port" else null
                        if (!isResumed) {
                            isResumed = true
                            if (continuation.isActive) continuation.resume(result)
                        }
                    }
                }

                val discoveryListener = object : NsdManager.DiscoveryListener {
                    override fun onStartDiscoveryFailed(serviceType: String?, errorCode: Int) {
                        try { nsdManager.stopServiceDiscovery(this) } catch (_: Exception) {}
                        if (!isResumed) {
                            isResumed = true
                            if (continuation.isActive) continuation.resume(null)
                        }
                    }

                    override fun onStopDiscoveryFailed(serviceType: String?, errorCode: Int) {
                        if (!isResumed) {
                            isResumed = true
                            if (continuation.isActive) continuation.resume(null)
                        }
                    }

                    override fun onDiscoveryStarted(regType: String?) {}
                    override fun onDiscoveryStopped(serviceType: String?) {}

                    override fun onServiceFound(serviceInfo: NsdServiceInfo?) {
                        if (serviceInfo?.serviceType?.contains("_friday-hub") == true) {
                            try {
                                nsdManager.resolveService(serviceInfo, resolveListener)
                            } catch (e: Exception) {
                                if (!isResumed) {
                                    isResumed = true
                                    if (continuation.isActive) continuation.resume(null)
                                }
                            }
                        }
                    }

                    override fun onServiceLost(serviceInfo: NsdServiceInfo?) {}
                }

                try {
                    nsdManager.discoverServices(
                        "_friday-hub._tcp.",
                        NsdManager.PROTOCOL_DNS_SD,
                        discoveryListener
                    )
                } catch (e: Exception) {
                    if (!isResumed) {
                        isResumed = true
                        continuation.resume(null)
                    }
                }

                val timer = java.util.Timer()
                timer.schedule(object : java.util.TimerTask() {
                    override fun run() {
                        try { nsdManager.stopServiceDiscovery(discoveryListener) } catch (_: Exception) {}
                        if (!isResumed) {
                            isResumed = true
                            if (continuation.isActive) continuation.resume(null)
                        }
                    }
                }, 1000)

                continuation.invokeOnCancellation {
                    try { nsdManager.stopServiceDiscovery(discoveryListener) } catch (_: Exception) {}
                    timer.cancel()
                }
            }
        } catch (e: Exception) {
            null
        }
    }

    private suspend fun scanLocalSubnet(context: Context): String? = withContext(Dispatchers.IO) {
        val localIp = getLocalIpAddress(context) ?: return@withContext null
        val prefix = localIp.substringBeforeLast(".") + "."

        val candidates = mutableListOf<String>()
        candidates.add("http://$localIp:8000")
        candidates.add("http://${prefix}1:8000")

        val range = (1..254).filter { "$prefix$it" != localIp && it != 1 }
        for (i in range) {
            candidates.add("http://$prefix$i:8000")
        }

        // Test candidates in parallel batches of 25 for quick execution
        for (chunk in candidates.chunked(25)) {
            val jobs = chunk.map { url ->
                async {
                    if (verifyHealth(url)) url else null
                }
            }
            val results = jobs.awaitAll()
            val found = results.firstOrNull { it != null }
            if (found != null) {
                return@withContext found
            }
        }

        null
    }

    fun verifyHealth(baseUrl: String): Boolean {
        return try {
            var normalized = baseUrl.trim().trimEnd('/')
            if (normalized.isNotEmpty() && !normalized.startsWith("http://") && !normalized.startsWith("https://")) {
                normalized = if (normalized.contains("ngrok")) "https://$normalized" else "http://$normalized"
            }
            val url = URL("$normalized/health")
            val conn = (url.openConnection() as HttpURLConnection).apply {
                connectTimeout = 3000
                readTimeout = 3000
                requestMethod = "GET"
                setRequestProperty("ngrok-skip-browser-warning", "true")
                setRequestProperty("User-Agent", "AgentPayGuard/1.0")
            }
            val code = conn.responseCode
            val isOk = code == 200
            conn.disconnect()
            isOk
        } catch (e: Exception) {
            false
        }
    }

    private fun getLocalIpAddress(context: Context): String? {
        try {
            val wifiManager = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
            val wifiInfo = wifiManager?.connectionInfo
            val ipAddress = wifiInfo?.ipAddress ?: 0
            if (ipAddress != 0) {
                return String.format(
                    "%d.%d.%d.%d",
                    ipAddress and 0xff,
                    ipAddress shr 8 and 0xff,
                    ipAddress shr 16 and 0xff,
                    ipAddress shr 24 and 0xff
                )
            }
        } catch (e: Exception) {
            // Ignore
        }

        try {
            val interfaces = Collections.list(NetworkInterface.getNetworkInterfaces())
            for (intf in interfaces) {
                val addrs = Collections.list(intf.inetAddresses)
                for (addr in addrs) {
                    if (!addr.isLoopbackAddress) {
                        val host = addr.hostAddress
                        if (host != null && host.indexOf(':') < 0 && !host.startsWith("127.")) {
                            return host
                        }
                    }
                }
            }
        } catch (e: Exception) {
            // Ignore
        }
        return null
    }
}

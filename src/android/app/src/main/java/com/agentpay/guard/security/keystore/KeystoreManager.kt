package com.agentpay.guard.security.keystore

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.Mac
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

class KeystoreManager private constructor() {

    private val keyStore: KeyStore? = try {
        KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
    } catch (e: Throwable) {
        null
    }

    private fun encodeBase64(bytes: ByteArray): String {
        return try {
            android.util.Base64.encodeToString(bytes, android.util.Base64.NO_WRAP)
        } catch (e: Throwable) {
            java.util.Base64.getEncoder().encodeToString(bytes)
        }
    }

    private fun decodeBase64(encoded: String): ByteArray {
        return try {
            android.util.Base64.decode(encoded, android.util.Base64.NO_WRAP)
        } catch (e: Throwable) {
            java.util.Base64.getDecoder().decode(encoded)
        }
    }

    private fun getOrCreateKey(alias: String, purpose: Int): SecretKey? {
        val ks = keyStore ?: return null
        return try {
            (ks.getEntry(alias, null) as? KeyStore.SecretKeyEntry)?.secretKey ?: run {
                val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
                generator.init(
                    KeyGenParameterSpec.Builder(alias, purpose)
                        .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                        .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                        .setKeySize(256)
                        .build()
                )
                generator.generateKey()
            }
        } catch (e: Throwable) {
            null
        }
    }

    fun encrypt(plaintext: String): String {
        return try {
            val key = getOrCreateKey(MASTER_KEY, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                ?: SecretKeySpec("AgentPayFallbackMasterKey256Bit!!".toByteArray(Charsets.UTF_8).take(32).toByteArray(), "AES")
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.ENCRYPT_MODE, key)
            val iv = cipher.iv
            val encrypted = cipher.doFinal(plaintext.toByteArray(Charsets.UTF_8))
            encodeBase64(iv + encrypted)
        } catch (e: Throwable) {
            encodeBase64(plaintext.toByteArray(Charsets.UTF_8))
        }
    }

    fun decrypt(encoded: String): String? {
        return try {
            val data = decodeBase64(encoded)
            val key = getOrCreateKey(MASTER_KEY, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                ?: SecretKeySpec("AgentPayFallbackMasterKey256Bit!!".toByteArray(Charsets.UTF_8).take(32).toByteArray(), "AES")
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(128, data.copyOfRange(0, 12)))
            String(cipher.doFinal(data.copyOfRange(12, data.size)), Charsets.UTF_8)
        } catch (e: Throwable) {
            try {
                String(decodeBase64(encoded), Charsets.UTF_8)
            } catch (_: Throwable) {
                null
            }
        }
    }

    fun sign(payload: String): String {
        return try {
            val macKey = getOrCreateMacKey()
            val mac = Mac.getInstance("HmacSHA256")
            mac.init(macKey)
            encodeBase64(mac.doFinal(payload.toByteArray(Charsets.UTF_8)))
        } catch (e: Throwable) {
            // Software fallback HMAC SHA-256
            val fallbackKey = SecretKeySpec("AgentPayFallbackSignKey256Bit!!!".toByteArray(Charsets.UTF_8), "HmacSHA256")
            val mac = Mac.getInstance("HmacSHA256")
            mac.init(fallbackKey)
            encodeBase64(mac.doFinal(payload.toByteArray(Charsets.UTF_8)))
        }
    }

    private fun getOrCreateMacKey(): SecretKey {
        val ks = keyStore
        if (ks != null) {
            try {
                (ks.getEntry(MAC_KEY, null) as? KeyStore.SecretKeyEntry)?.secretKey?.let { return it }
                val generator = KeyGenerator.getInstance("HmacSHA256", ANDROID_KEYSTORE)
                generator.init(
                    KeyGenParameterSpec.Builder(MAC_KEY, KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY)
                        .setKeySize(256)
                        .build()
                )
                return generator.generateKey()
            } catch (_: Throwable) {}
        }
        return SecretKeySpec("AgentPayFallbackSignKey256Bit!!!".toByteArray(Charsets.UTF_8), "HmacSHA256")
    }

    companion object {
        private const val ANDROID_KEYSTORE = "AndroidKeyStore"
        private const val MASTER_KEY = "agentpay_master_key"
        private const val MAC_KEY = "agentpay_auth_signing_key"
        private const val TRANSFORMATION = "AES/GCM/NoPadding"

        @Volatile
        private var instance: KeystoreManager? = null

        fun get(): KeystoreManager =
            instance ?: synchronized(this) { instance ?: KeystoreManager().also { instance = it } }
    }
}


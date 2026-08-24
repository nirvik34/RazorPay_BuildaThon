package com.agentpay.guard.security.keystore

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.Mac
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class KeystoreManager private constructor() {

    private val keyStore: KeyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }

    private fun getOrCreateKey(alias: String, purpose: Int): SecretKey {
        (keyStore.getEntry(alias, null) as? KeyStore.SecretKeyEntry)?.let { return it.secretKey }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        generator.init(
            KeyGenParameterSpec.Builder(alias, purpose)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build()
        )
        return generator.generateKey()
    }

    fun encrypt(plaintext: String): String {
        val key = getOrCreateKey(MASTER_KEY, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key)
        val iv = cipher.iv
        val encrypted = cipher.doFinal(plaintext.toByteArray(Charsets.UTF_8))
        return java.util.Base64.getEncoder().encodeToString(iv + encrypted)
    }

    fun decrypt(encoded: String): String? {
        return try {
            val data = java.util.Base64.getDecoder().decode(encoded)
            val key = getOrCreateKey(MASTER_KEY, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(128, data.copyOfRange(0, 12)))
            String(cipher.doFinal(data.copyOfRange(12, data.size)), Charsets.UTF_8)
        } catch (e: Exception) {
            null
        }
    }

    fun sign(payload: String): String {
        val macKey = getOrCreateMacKey()
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(macKey)
        return java.util.Base64.getEncoder().encodeToString(mac.doFinal(payload.toByteArray(Charsets.UTF_8)))
    }

    private fun getOrCreateMacKey(): SecretKey {
        (keyStore.getEntry(MAC_KEY, null) as? KeyStore.SecretKeyEntry)?.let { return it.secretKey }
        val generator = KeyGenerator.getInstance("HmacSHA256", ANDROID_KEYSTORE)
        generator.init(
            KeyGenParameterSpec.Builder(MAC_KEY, KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY)
                .setKeySize(256)
                .build()
        )
        return generator.generateKey()
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

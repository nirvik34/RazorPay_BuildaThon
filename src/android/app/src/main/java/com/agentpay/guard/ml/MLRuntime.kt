package com.agentpay.guard.ml

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.exp

/**
 * On-device risk model runtime — pure Kotlin, ZERO ML dependencies.
 *
 * Loads assets/ml/risk_model.json (exported by src/ml/export/export_android.py)
 * and runs a forward pass for:
 *   - "logistic_regression"  (weights + bias)
 *   - "mlp"                  (dense layers, ReLU hidden, sigmoid out)
 *   - "tree_ensemble"        (RF / GB trees, averaged or summed with lr)
 *
 * Inputs are standardised with the exported scaler, exactly matching training.
 * The model is ~10 KB and a single inference is microseconds — it runs inside
 * the Guard's decision path without any network or runtime library.
 */
object MLRuntime {

    @Volatile
    private var bundle: JSONObject? = null

    @Volatile
    private var featureNames: List<String> = emptyList()

    fun init(context: Context) {
        if (bundle != null) return
        try {
            val text = context.assets.open("ml/risk_model.json").bufferedReader().use { it.readText() }
            val parsed = JSONObject(text)
            featureNames = parsed.getJSONArray("features").let { arr ->
                (0 until arr.length()).map { arr.getString(it) }
            }
            bundle = parsed
        } catch (e: Exception) {
            bundle = null
        }
    }

    fun isLoaded(): Boolean = bundle != null

    fun modelType(): String? = bundle?.optString("model_type")

    /**
     * Raw feature map (name → value) → fraud/risk probability in [0, 1].
     * Missing features are treated as 0 after scaling. Returns -1f when no
     * model is loaded (caller falls back to the heuristic engine).
     */
    fun predict(rawFeatures: Map<String, Float>): Float {
        val b = bundle ?: return -1f
        val scaler = b.getJSONObject("scaler")
        val mean = scaler.getJSONArray("mean")
        val scale = scaler.getJSONArray("scale")
        val x = FloatArray(featureNames.size) { i ->
            val raw = rawFeatures[featureNames[i]] ?: 0f
            val m = mean.getDouble(i).toFloat()
            val s = scale.getDouble(i).toFloat().coerceAtLeast(1e-8f)
            (raw - m) / s
        }

        return when (b.optString("model_type")) {
            "logistic_regression" -> sigmoid(dot(b.getJSONArray("weights"), b.optDouble("bias", 0.0).toFloat(), x))
            "mlp" -> sigmoid(forwardMlp(b, x))
            "tree_ensemble" -> treeEnsemble(b, x)
            else -> -1f
        }
    }

    private fun forwardMlp(b: JSONObject, x: FloatArray): Float {
        var activation = x
        val layers = b.getJSONArray("layers")
        for (i in 0 until layers.length()) {
            val layer = layers.getJSONObject(i)
            val weights = layer.getJSONArray("weights")
            val biases = layer.getJSONArray("biases")
            val isLast = i == layers.length() - 1
            // sklearn coefs_ layout: weights[inputIndex][neuronIndex]
            val out = FloatArray(biases.length())
            for (k in activation.indices) {
                val wArr = weights.getJSONArray(k)
                for (j in 0 until biases.length()) {
                    out[j] += wArr.getDouble(j).toFloat() * activation[k]
                }
            }
            for (j in out.indices) {
                out[j] = if (isLast) out[j] + biases.getDouble(j).toFloat() else relu(out[j] + biases.getDouble(j).toFloat())
            }
            activation = out
        }
        return activation[0]
    }

    private fun treeEnsemble(b: JSONObject, x: FloatArray): Float {
        val trees = b.getJSONArray("trees")
        val lr = b.optDouble("learning_rate", -1.0)
        var sum = 0f
        for (t in 0 until trees.length()) {
            val p = walkTree(trees.getJSONObject(t), x)
            sum += if (lr > 0) (p * 2 - 1).toFloat() * lr.toFloat() else p
        }
        val raw = if (lr > 0) sigmoid(sum + b.optDouble("base_score", 0.0).toFloat()) else sum / trees.length()
        return raw
    }

    private fun walkTree(node: JSONObject, x: FloatArray): Float {
        val value = node.opt("value")
        if (value != null) return if (value is Double) value.toFloat() else value.toString().toFloat()
        val idx = featureNames.indexOf(node.getString("feature"))
        val threshold = node.getDouble("threshold").toFloat()
        val goLeft = idx >= 0 && x.getOrElse(idx) { 0f } <= threshold
        val next = node.getJSONObject(if (goLeft) "left" else "right")
        return walkTree(next, x)
    }

    private fun dot(weights: JSONArray, bias: Float, x: FloatArray): Float {
        var sum = bias
        for (i in 0 until weights.length()) sum += weights.getDouble(i).toFloat() * x[i]
        return sum
    }

    private fun relu(v: Float): Float = if (v > 0f) v else 0f

    private fun sigmoid(v: Float): Float =
        (1f / (1f + exp(-v.toDouble()))).toFloat()
}

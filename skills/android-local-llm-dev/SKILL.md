---
name: android-local-llm-dev
description: >-
  Specialized Android On-Device AI and Local LLM Development Skill covering ONNX Runtime Mobile,
  Google AI Edge LiteRT / LiteRT-LM, Gemini Nano via Google AICore, native SentencePiece C++ JNI,
  16 KB page memory alignment for Android 15+, multi-precision tensor buffers (FLOAT, FLOAT16, BFLOAT16),
  safe hardware bitmap preprocessing, and resilient model download workers. Use when implementing,
  debugging, or optimizing on-device neural networks, vision-language models, embeddings, or local LLMs on Android.
---

# Android On-Device AI & Local LLM Development Skill

This skill defines production-grade engineering standards for running local Large Language Models (LLMs), Small Language Models (SLMs), Vision-Language Models (VLMs), and zero-shot neural classifiers directly on Android devices without external network dependencies.

---

## [Architecture & Runtime Matrix]

Android on-device AI relies on three primary architectural paths depending on model type, hardware tier, and distribution channels:

### 1. System-Service Path (Google AICore + Gemini Nano)
- **Runtime**: `com.google.ai.edge.aicore` system service.
- **Characteristics**: Zero model binary overhead in the APK. Model weights (~1.5 GB - 3 GB) are managed and updated by Google Play system updates on supported hardware (Pixel 8+, Galaxy S24+).
- **Inference Client & Prompt Engineering**:
  ```kotlin
  import android.content.Context
  import android.util.Log

  class LocalGeminiNanoValidator(private val context: Context) {
      fun isAvailable(): Boolean {
          return try {
              val pm = context.packageManager
              pm.getPackageInfo("com.google.ai.edge.aicore", 0) != null
          } catch (_: Exception) {
              false
          }
      }

      fun buildPrompt(taskDescription: String, detectedLabels: List<String>): String {
          return """
              You are an on-device verification model. Determine whether the detected image content matches the task description.
              Task: "$taskDescription"
              Detected content: ${detectedLabels.joinToString(", ")}

              Output strict JSON only with no markdown formatting:
              {"valid": true|false, "reason": "brief explanation"}
          """.trimIndent()
      }

      fun parseNanoValidationResponse(rawResponse: String): Pair<Boolean, String> {
          // Clean markdown codeblocks if model wrapped output
          val cleaned = rawResponse
              .replace("```json", "")
              .replace("```", "")
              .trim()

          // Resilient regex extraction handling arbitrary key order
          val validRegex = "\"valid\"\\s*:\\s*(true|false)".toRegex()
          val reasonRegex = "\"reason\"\\s*:\\s*\"([^\"]+)\"".toRegex()

          val isValid = validRegex.find(cleaned)?.groupValues?.get(1)?.toBooleanStrictOrNull() ?: false
          val reason = reasonRegex.find(cleaned)?.groupValues?.get(1) ?: "No reasoning provided"

          return Pair(isValid, reason)
      }
  }
  ```
- **Calibrated Fallback Invariant**: AICore may be uninitialized, disabled by user settings, or unsupported on the device. The application MUST gracefully fall back to a local quantized vision model (e.g., SigLIP 2 zero-shot similarity) without throwing uncaught exceptions.
- **JSON Parsing Defense**: System LLMs may output reversed JSON keys (e.g. `{"reason": "...", "valid": true}` instead of `{"valid": true, "reason": "..."}`) or wrap output in markdown codeblocks (````json ... ````). Response parsers MUST clean fences, extract inner JSON, and handle arbitrary key order.

### 2. Local SLM / LLM Path (Google AI Edge LiteRT-LM / MediaPipe)
For local Small Language Models (Gemma 2B, Gemma 1B, Llama 3.2 1B/3B, Phi-3.5) running completely offline on GPU/NPU:
- **Dependency**: `com.google.ai.edge.litert:litert-lm` or MediaPipe LLM Inference Engine.
- **Streaming Token Generation & Options**:
  ```kotlin
  import android.content.Context
  import kotlinx.coroutines.channels.awaitClose
  import kotlinx.coroutines.flow.Flow
  import kotlinx.coroutines.flow.callbackFlow
  // MediaPipe / LiteRT-LM API integration pattern
  class LocalLlmEngine(private val context: Context, private val modelPath: String) {

      fun streamInference(prompt: String): Flow<String> = callbackFlow {
          // Configure options: temperature, topK, maxTokens, listener
          val optionsBuilder = com.google.mediapipe.tasks.genai.llminference.LlmInference.LlmInferenceOptions.builder()
              .setModelPath(modelPath)
              .setMaxTokens(512)
              .setResultListener { partialResult, done ->
                  if (partialResult != null) {
                      trySend(partialResult)
                  }
                  if (done) {
                      close()
                  }
              }
              .setErrorListener { error ->
                  close(IllegalStateException("LiteRT-LM inference failed: ${error.message}"))
              }

          val llmInference = com.google.mediapipe.tasks.genai.llminference.LlmInference.createFromOptions(
              context,
              optionsBuilder.build()
          )

          llmInference.generateResponseAsync(prompt)

          awaitClose {
              llmInference.close()
          }
      }
  }
  ```
- **Context Window Management**: Explicitly configure `setMaxTokens` and truncate multi-turn history to fit within available device RAM (typically 2048 tokens on 8 GB devices; 1024 tokens on 4 GB devices).

### 3. Vision & Classifier Runtime Path (ONNX Runtime Mobile & LiteRT)
When running zero-shot vision-language models, embeddings, or real-time frame classification:
- **ONNX Runtime Mobile (`ai.onnxruntime:onnxruntime-android`)**: Recommended for Vision-Language Models (SigLIP 2, CLIP, MobileNet) and zero-shot similarity verification. Supports multi-precision weights (`UINT8`, `INT8`, `Q4F16`, `FP16`, `FULL`).
- **Google AI Edge LiteRT (`org.tensorflow:tensorflow-lite` / `com.google.ai.edge.litert:litert`)**: Recommended for real-time video frame moderation (YOLO, MobileNet classifiers) with low latency.
- **Zero-Allocation Buffer Pattern (LiteRT)**:
  ```kotlin
  // Pre-allocate direct NIO buffers once to eliminate garbage collection churn during camera streams
  class FrameModerationEngine(modelBuffer: ByteBuffer) {
      private val interpreter = org.tensorflow.lite.Interpreter(modelBuffer)
      private val inputBuffer = ByteBuffer.allocateDirect(1 * 224 * 224 * 3)
          .order(ByteOrder.nativeOrder())
      private val outputArray = Array(1) { FloatArray(2) }

      @Synchronized
      fun classifyFrame(scaledBitmap: Bitmap): FloatArray {
          inputBuffer.rewind()
          // Fast bulk pixel normalization into pre-allocated direct buffer
          // ...
          interpreter.run(inputBuffer, outputArray)
          return outputArray[0]
      }

      fun close() {
          interpreter.close()
      }
  }
  ```
- **Memory-Mapped Model Loading**: Always map model files from disk via `FileInputStream.channel.map(FileChannel.MapMode.READ_ONLY, ...)` to avoid loading multi-hundred-megabyte byte arrays into the JVM heap.

---

## [Native C++ JNI Tokenization & NDK Standards]

Zero-shot vision-language models and local LLMs require text tokenization (SentencePiece, BPE) before feeding token IDs into model input tensors.

### 1. Native SentencePiece C++ JNI Architecture
Implement native tokenization via C++ JNI rather than pure Java regex to achieve sub-millisecond tokenization:
```cpp
#include <jni.h>
#include <string>
#include <vector>
#include <mutex>
#include "sentencepiece_processor.h"

static sentencepiece::SentencePieceProcessor g_processor;
static std::mutex g_mutex;
static std::string g_loaded_model_path;

extern "C" JNIEXPORT jint JNICALL
Java_com_alhaq_amniquest_ai_SentencePieceProcessor_load(
    JNIEnv* env, jobject thiz, jstring model_path) {
    const char* path = env->GetStringUTFChars(model_path, nullptr);
    std::lock_guard<std::mutex> lock(g_mutex);
    if (g_loaded_model_path == path) {
        env->ReleaseStringUTFChars(model_path, path);
        return 0; // Already loaded
    }
    const auto status = g_processor.Load(path);
    if (status.ok()) {
        g_loaded_model_path = path;
    }
    env->ReleaseStringUTFChars(model_path, path);
    return status.ok() ? 0 : -1;
}
```

### 2. Thread Safety & Path Caching
- **Mutex Synchronization**: Wrap model loading and tokenization in `std::mutex` to prevent memory corruption when multiple background coroutines or WorkManager threads tokenize simultaneously.
- **Model Path Caching**: Cache `g_loaded_model_path` in memory. Avoid re-reading and re-allocating the `.model` protobuf file from flash storage on every inference pass.

### 3. Android 15+ 16 KB Page Memory Alignment in CMake
Android 15 (API 35+) enforces 16 KB memory page alignment for native libraries. Default CMake linkers produce 4 KB aligned shared libraries (`Align 0x1000`), which fail to load on Android 15+ devices.
You MUST configure the linker flag in `CMakeLists.txt`:
```cmake
cmake_minimum_required(VERSION 3.18.1)
project("sentencepiece_jni")

# Link JNI wrapper
add_library(sentencepiece_jni SHARED sentencepiece_jni.cpp)

# Enforce 16 KB page alignment for Android 15+ (ELF LOAD segment alignment)
if(COMMAND target_link_options)
    target_link_options(sentencepiece_jni PRIVATE "-Wl,-z,max-page-size=16384")
else()
    set_target_properties(sentencepiece_jni PROPERTIES LINK_FLAGS "-Wl,-z,max-page-size=16384")
endif()
```

In the module's `build.gradle.kts`:
```kotlin
android {
    packaging {
        jniLibs {
            useLegacyPackaging = false
        }
    }
}
```

### 4. Gemma & Llama Tokenization Specifications
- **Token ID Constants**: For Gemma-based tokenizers (SigLIP 2, Gemma), configure `PAD = 0L`, `EOS = 1L`, and fixed sequence length (e.g. `maxLength = 64`).
- **Never Concatenate Raw EOS Strings**: Do NOT append literal `" </s>"` strings to input text prior to tokenization. This produces incorrect token IDs because SentencePiece treats appended text as literal characters rather than the special control token. Instead, tokenize raw text and insert `EOS` programmatically at the end of the token ID array before padding with `PAD`.

### 5. Pure-Kotlin SentencePiece Fallback (Zero-Native Resilience)
When the native shared library (`libsentencepiece_jni.so`) is unavailable (e.g. unsupported CPU architectures, ABI stripping, or dynamic link errors), fall back to a pure-Kotlin binary protobuf parser and Unigram Viterbi tokenizer:
- **Zero-Dependency Protobuf Parser**: Read SentencePiece `.model` binary protobuf directly by parsing varints and field tags (wire types 0, 2, 5) to extract piece strings and log-probability scores without requiring the full `protobuf-javalite` runtime.
- **Unigram Viterbi DP Segmentation**: Implement dynamic programming with memoization to find the optimal segment partitioning maximizing unigram log probabilities.
- **Automatic Fallback Wrapper**: `SentencePieceProcessor` attempts to load the native JNI library first; upon `UnsatisfiedLinkError` or JNI load failure, it transparently instantiates `KotlinSentencePieceModel` so tokenization always succeeds.

---

## [Direct NIO Buffers & Multi-Precision Tensor Extraction]

### 1. Direct NIO Buffer Rule
ONNX Runtime Java allocates direct NIO buffers in native memory.
- **CRITICAL FAILURE**: Calling `.array()` on an ONNX direct `FloatBuffer` throws:
  `java.lang.UnsupportedOperationException: Direct buffer has no array`
- **MANDATORY PATTERN**: Always duplicate the buffer and perform a bulk read into a newly allocated array:
  ```kotlin
  val floatBuffer = tensor.floatBuffer ?: return floatArrayOf()
  val copy = floatBuffer.duplicate()
  val array = FloatArray(copy.remaining())
  copy.get(array)
  ```

### 2. Multi-Precision Tensor Extraction (FLOAT, FLOAT16, BFLOAT16, DOUBLE)
Quantized (UINT8, INT8, Q4F16) and half-precision (FP16) models produce differing tensor types on their output heads.
- Calling `tensor.floatBuffer` on a `FLOAT16` or `BFLOAT16` tensor returns `null`.
- Inspect `tensor.info.type` and decode through the appropriate buffer channel:
  ```kotlin
  import ai.onnxruntime.OnnxJavaType
  import ai.onnxruntime.platform.Fp16Conversions
  import java.nio.DoubleBuffer
  import java.nio.FloatBuffer
  import java.nio.ShortBuffer

  fun extractLogitsFromBuffers(
      type: OnnxJavaType,
      floatBuffer: FloatBuffer?,
      shortBuffer: ShortBuffer?,
      doubleBuffer: DoubleBuffer? = null
  ): FloatArray {
      return when (type) {
          OnnxJavaType.FLOAT -> {
              val buf = floatBuffer ?: throw IllegalStateException("FloatBuffer is null for FLOAT tensor")
              val copy = buf.duplicate()
              FloatArray(copy.remaining()).also { copy.get(it) }
          }
          OnnxJavaType.FLOAT16 -> {
              val buf = shortBuffer ?: throw IllegalStateException("ShortBuffer is null for FLOAT16 tensor")
              val converted = Fp16Conversions.convertFp16BufferToFloatBuffer(buf.duplicate())
              FloatArray(converted.remaining()).also { converted.get(it) }
          }
          OnnxJavaType.BFLOAT16 -> {
              val buf = shortBuffer ?: throw IllegalStateException("ShortBuffer is null for BFLOAT16 tensor")
              val converted = Fp16Conversions.convertBf16BufferToFloatBuffer(buf.duplicate())
              FloatArray(converted.remaining()).also { converted.get(it) }
          }
          OnnxJavaType.DOUBLE -> {
              val buf = doubleBuffer ?: throw IllegalStateException("DoubleBuffer is null for DOUBLE tensor")
              val copy = buf.duplicate()
              FloatArray(copy.remaining()) { copy.get().toFloat() }
          }
    }
}
```

### 3. Calibrated SigLIP 2 Similarity & Negative Baseline Gating
SigLIP 2 zero-shot classification requires calibrated scoring and distractor rejection:
- **Calibrated Absolute Thresholds**:
  - Sigmoid over logits (`1 / (1 + exp(-x))`): `SIGLIP_SIGMOID_THRESHOLD = 0.05f`. Genuine matches score 0.05..0.95; unrelated text scores < 0.005.
  - Cosine similarity between L2-normalized image and text embeddings: `SIGLIP_COSINE_THRESHOLD = 0.16f`.
- **Negative Baseline Prompts**:
  Always evaluate positive prompts alongside standard negative baseline distractors:
  1. `"this is a blurry, dark, or irrelevant photo."`
  2. `"this is a photo of a blank wall, floor, or empty background."`
- **Negative Margin Gating**:
  Require positive prompt score to exceed the highest negative baseline score by a strict margin:
  - Logit Margin: `NEGATIVE_MARGIN_LOGIT = 0.25f`
  - Cosine Margin: `NEGATIVE_MARGIN_COSINE = 0.015f`
  This eliminates false positives on blank walls, covered camera lenses, or dark rooms.

---

## [Safe Hardware Bitmap Preprocessing]

CameraX captures and Gallery decoders frequently return bitmaps with `Bitmap.Config.HARDWARE`.
- **CRITICAL FAILURE**: Accessing hardware bitmap pixels directly via `bitmap.getPixels()` throws:
  `java.lang.IllegalArgumentException: unable to getPixels from a HardwareConfig bitmap`
- **MANDATORY PATTERN**:
  1. Guard and convert hardware bitmaps to `Bitmap.Config.ARGB_8888`.
  2. Scale to model dimensions (e.g. 224x224).
  3. Extract all pixels in a single bulk `getPixels(IntArray, ...)` call instead of pixel-by-pixel loops.
  4. Normalize color channels: `(pixelValue / 255.0f - mean) / std`.
  5. Allocate a direct `ByteBuffer` with native byte ordering (`ByteOrder.nativeOrder()`).
  6. Explicitly recycle intermediate copies in `try-finally` blocks:
  ```kotlin
  import android.graphics.Bitmap
  import androidx.core.graphics.scale
  import java.nio.ByteBuffer
  import java.nio.ByteOrder
  import java.nio.FloatBuffer

  fun preprocessBitmapToFloatBuffer(bitmap: Bitmap, targetWidth: Int = 224, targetHeight: Int = 224): FloatBuffer {
      val safeBitmap = if (bitmap.config == Bitmap.Config.HARDWARE) {
          bitmap.copy(Bitmap.Config.ARGB_8888, false)
              ?: throw IllegalStateException("Failed to convert HARDWARE bitmap to ARGB_8888")
      } else bitmap

      val resizedBitmap = if (safeBitmap.width == targetWidth && safeBitmap.height == targetHeight) {
          safeBitmap
      } else {
          safeBitmap.scale(targetWidth, targetHeight)
      }

      try {
          val channelSize = targetWidth * targetHeight
          val pixels = IntArray(channelSize)
          resizedBitmap.getPixels(pixels, 0, targetWidth, 0, 0, targetWidth, targetHeight)

          val floatValues = FloatArray(3 * channelSize)
          val mean = 0.5f
          val std = 0.5f

          for (i in 0 until channelSize) {
              val pixel = pixels[i]
              val r = ((pixel shr 16) and 0xFF) / 255f
              val g = ((pixel shr 8) and 0xFF) / 255f
              val b = (pixel and 0xFF) / 255f

              floatValues[i] = (r - mean) / std
              floatValues[channelSize + i] = (g - mean) / std
              floatValues[2 * channelSize + i] = (b - mean) / std
          }

          val byteBuffer = ByteBuffer.allocateDirect(3 * channelSize * 4)
              .order(ByteOrder.nativeOrder())
          val floatBuffer = byteBuffer.asFloatBuffer()
          floatBuffer.put(floatValues)
          floatBuffer.flip()
          return floatBuffer
      } finally {
          if (safeBitmap != bitmap) safeBitmap.recycle()
          if (resizedBitmap != bitmap && resizedBitmap != safeBitmap) resizedBitmap.recycle()
      }
  }
  ```

---

## [Native Tensor Lifecycle & C++ Memory Leak Prevention]

`OnnxTensor` and `OrtSession.Result` allocate unmanaged C++ memory off the JVM heap.
- The JVM Garbage Collector has no visibility into native off-heap allocations. In high-frequency operations (camera analysis, live token generation), unclosed tensors cause rapid out-of-memory crashes (`SIGSEGV` or `OutOfMemoryError`).
- **MANDATORY PATTERN**: Enclose every tensor creation and execution result in `.use { ... }` or explicit `try-finally` blocks:
  ```kotlin
  val imageTensor = OnnxTensor.createTensor(env, floatBuffer, shape)
  val textTensor = OnnxTensor.createTensor(env, LongBuffer.wrap(tokens), textShape)

  try {
      val inputs = mapOf("pixel_values" to imageTensor, "input_ids" to textTensor)
      val sessionResult = session.run(inputs)
      sessionResult.use { output ->
          val logitsTensor = output.get(0) as OnnxTensor
          extractLogitsFloatArray(logitsTensor)
      }
  } finally {
      imageTensor.close()
      textTensor.close()
  }
  ```

---

## [Hardware Acceleration & Automatic Runtime Fault Recovery]

### 1. NNAPI Session Configuration
Initialize sessions with NNAPI hardware acceleration enabled by default:
```kotlin
val sessionOptions = SessionOptions().apply {
    try {
        addNnapi()
    } catch (e: Throwable) {
        Log.w("OnDeviceAi", "NNAPI not supported on this device: ${e.message}")
    }
    setExecutionMode(SessionOptions.ExecutionMode.SEQUENTIAL)
    setOptimizationLevel(SessionOptions.OptLevel.ALL_OPT)
}
```

### 2. Automatic CPU Fallback Pattern
NNAPI drivers vary significantly across chipsets (Qualcomm Snapdragon, MediaTek Dimensity, Google Tensor, Samsung Exynos). If an NNAPI driver crashes during `session.run(inputs)` due to tensor shape mismatches or unsupported ops, catching the exception and falling back to CPU prevents user-facing failure:
```kotlin
val resultOutput = try {
    activeSession.run(inputs)
} catch (runError: Throwable) {
    if (isUsingNnapi) {
        Log.w("OnDeviceAi", "NNAPI inference failed at runtime, recreating CPU session: ${runError.message}")
        val cpuSession = recreateCpuOnlySession(env, modelFile)
        cpuSession.run(inputs)
    } else {
        throw runError
    }
}
```

### 3. Thread-Safe Model Session Caching
Creating an `OrtSession` for multi-hundred-megabyte models incurs significant disk I/O, native graph allocation, and memory overhead (500ms - 2s).
- **Session Caching Pattern**: Cache the loaded `OrtSession` and track its canonical path (`loadedModelFilePath == modelFile.canonicalPath`).
- **Mutex Guard**: Synchronize session initialization and inference using a mutex (`synchronized(sessionLock)`) to prevent concurrent coroutines from creating duplicate ONNX sessions or destroying an active session mid-inference.
- **Model Invalidation**: If the user switches models in settings, safely close the active session and instantiate the new model.

---

## [Resilient Large Model Download Engine]

Local AI models (~350 MB to 1.5+ GB) and tokenizer assets (~4 MB) require dedicated background download management.

### 1. WorkManager Non-Expedited Quota Invariant
Expedited work requests (`setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)`) have strict system quotas. When expedited quotas are exhausted, tasks without quota fallback are silently dropped by the Android OS.
- Always configure:
  ```kotlin
  val request = OneTimeWorkRequestBuilder<FileDownloadWorker>()
      .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
      .setConstraints(
          Constraints.Builder()
              .setRequiredNetworkType(NetworkType.CONNECTED)
              .build()
      )
      .build()
  ```

### 2. Resilient HTTP Range 200 vs 206 Handling
When resuming interrupted model downloads using HTTP `Range: bytes=downloadedBytes-`:
- If the server responds with `206 Partial Content`: Seek to the end of the existing file and append incoming bytes.
- If the server or CDN ignores the `Range` header and responds with `200 OK`: Truncate the file, reset `downloadedBytes = 0`, and stream from the beginning. Failing to check `response.code == 200` causes file corruption.

### 3. Queue Deduplication & State Reconciliation
- Use unique work names with `ExistingWorkPolicy.KEEP`:
  ```kotlin
  WorkManager.getInstance(context).enqueueUniqueWork(
      "download_model_${modelId}",
      ExistingWorkPolicy.KEEP,
      request
  )
  ```
- Reconcile stale SharedPreferences flags (e.g. `downloading = modelId`) against live `WorkManager.getWorkInfosForUniqueWorkLiveData` on application startup to prevent permanent UI lockouts.

### 4. HTTP Redirect Handling (301 / 302 / 307 / 308)
Model hosting mirrors and CDNs (such as Hugging Face and GitHub Releases) frequently issue 302 or 307 redirects to temporary presigned cloud storage URLs.
- Configure `OkHttpClient` with explicit redirect support:
  ```kotlin
  val client = OkHttpClient.Builder()
      .followRedirects(true)
      .followSslRedirects(true)
      .connectTimeout(30, TimeUnit.SECONDS)
      .readTimeout(60, TimeUnit.SECONDS)
      .build()
  ```

### 5. Concurrency Guard on Download Completion
When multiple download workers execute or finish in close proximity, a worker completing or failing must not clear the `"downloading"` flag of a different model.
- Always verify the active downloading model ID in SharedPreferences before clearing state:
  ```kotlin
  val currentDownloading = prefs.getString("downloading", null)
  if (currentDownloading == null || currentDownloading == modelId) {
      prefs.edit().remove("downloading").apply()
  }
  ```

### 6. Race-Safe Foreground Notification Initialization
If network data chunks arrive before the initial foreground notification builder finishes constructing, `updateProgressNotification()` may encounter an uninitialized notification builder.
- Ensure foreground notification builders lazily initialize or invoke `createForegroundInfo()` on first update to prevent null reference crashes.

---

## [Related Skills & Cross References]

- **`android-fullstack-dev`**: General Android Clean Architecture, Jetpack Compose, Material 3, Accessibility Services, Room DB, and store publishing.
- **`security-compliance`**: ECDSA NIST P-256 cryptographic license verification and zero-knowledge data auditing.
- **`huggingface-local-models`**: Model selection, GGUF quantization, and architecture sizing for local inference.

---
name: android-local-ai-onnx
description: >-
  Specialized Android On-Device AI & ONNX Runtime Mobile Skill covering zero-shot SigLIP 2 vision classification,
  native SentencePiece C++ JNI, 16 KB page memory alignment for Android 15+, multi-precision tensor extraction
  (FLOAT, FLOAT16, BFLOAT16, DOUBLE), safe hardware bitmap preprocessing, NNAPI fallback, and resilient WorkManager
  large model downloads. Use when implementing, debugging, or optimizing on-device neural networks on Android.
version: 1.0.0
---

# Android On-Device AI & ONNX Runtime Mobile Skill

This skill defines enterprise-grade standards for running on-device neural networks, Vision-Language Models (VLMs like SigLIP 2), and zero-shot neural classifiers directly on Android devices with 100% offline privacy and zero server dependencies.

---

## 1. On-Device Vision Verification Architecture (SigLIP 2)

SigLIP 2 computes joint embeddings between an input image and target text prompts directly on-device using ONNX Runtime Mobile (`ai.onnxruntime:onnxruntime-android`).

### Core Execution Flow
1. **Image Preprocessing**: Convert CameraX hardware bitmap to software `ARGB_8888`, scale to model input resolution (e.g. 224x224), normalize channels into a direct NIO `FloatBuffer`.
2. **Text Tokenization**: Pass prompt strings through native C++ SentencePiece JNI using Gemma token IDs (`PAD = 0L`, `EOS = 1L`, fixed length 64).
3. **Inference**: Pass image and text tensors into `OrtSession.run()`, extracting cosine similarity logits from multi-precision output heads.
4. **Calibrated Thresholds & Negative Baseline Gating**:
   - Compare positive prompt score against calibrated absolute thresholds:
     - Sigmoid Logit Threshold: `0.05f`
     - Cosine Similarity Threshold: `0.16f`
   - Evaluate against negative baseline distractors (`"this is a blurry, dark, or irrelevant photo."`, `"this is a photo of a blank wall, floor, or empty background."`).
   - Require positive prompt score to exceed the highest negative baseline score by a strict margin (`NEGATIVE_MARGIN_LOGIT = 0.25f` or `NEGATIVE_MARGIN_COSINE = 0.015f`) to eliminate false positives on dark, blurry, or blank camera captures.
5. **Verification**: If positive score clears both the absolute threshold and negative baseline margin, verify task completion; otherwise return descriptive feedback.

---

## 2. Native SentencePiece C++ JNI & NDK Standards

Zero-shot vision-language models require tokenizing text queries into token ID sequences before inference.

### 1. Native C++ JNI Implementation
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

extern "C" JNIEXPORT jlongArray JNICALL
Java_com_alhaq_amniquest_ai_SentencePieceProcessor_encode(
    JNIEnv* env, jobject thiz, jstring text, jint max_length) {
    const char* text_chars = env->GetStringUTFChars(text, nullptr);
    std::vector<int> pieces;
    {
        std::lock_guard<std::mutex> lock(g_mutex);
        g_processor.Encode(text_chars, &pieces);
    }
    env->ReleaseStringUTFChars(text, text_chars);

    // Gemma token IDs: PAD = 0L, EOS = 1L
    jlongArray result = env->NewLongArray(max_length);
    std::vector<jlong> buffer(max_length, 0L); // Default fill PAD

    int count = std::min(static_cast<int>(pieces.size()), max_length - 1);
    for (int i = 0; i < count; ++i) {
        buffer[i] = static_cast<jlong>(pieces[i]);
    }
    buffer[count] = 1L; // Append EOS control token

    env->SetLongArrayRegion(result, 0, max_length, buffer.data());
    return result;
}
```

### 2. Thread Safety & Path Caching
- **Mutex Synchronization**: Wrap model loading and encoding in `std::mutex` to prevent memory corruption when multiple background coroutines or WorkManager threads tokenize concurrently.
- **Model Path Caching**: Cache `g_loaded_model_path` in memory. Never re-read or re-allocate the `.model` protobuf file from flash storage on every inference pass.

### 3. Android 15+ 16 KB Page Memory Alignment in CMake
Android 15 (API 35+) strictly enforces 16 KB page memory alignment for native shared libraries. You MUST configure the linker flag in `CMakeLists.txt`:
```cmake
cmake_minimum_required(VERSION 3.18.1)
project("sentencepiece_jni")

add_library(sentencepiece_jni SHARED sentencepiece_jni.cpp)

# Enforce 16 KB page alignment for Android 15+
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

### 4. Gemma Tokenization Specifications
- **Token ID Constants**: Configure `PAD = 0L`, `EOS = 1L`, and fixed sequence length `maxLength = 64`.
- **Never Concatenate Raw EOS Strings**: Do NOT append literal `" </s>"` strings to input text prior to tokenization. SentencePiece treats appended text as literal characters rather than the special control token. Instead, tokenize raw text and insert `EOS` programmatically at the end of the token ID sequence before padding with `PAD`.

### 5. Pure-Kotlin SentencePiece Fallback (Zero-Native Resilience)
When the native shared library (`libsentencepiece_jni.so`) is unavailable (e.g. unsupported CPU architectures, ABI stripping, or dynamic link errors), fall back to a pure-Kotlin binary protobuf parser and Unigram Viterbi tokenizer:
- **Zero-Dependency Protobuf Parser**: Read SentencePiece `.model` binary protobuf directly by parsing varints and field tags (wire types 0, 2, 5) to extract piece strings and log-probability scores without requiring the full `protobuf-javalite` runtime.
- **Unigram Viterbi DP Segmentation**: Implement dynamic programming with memoization to find the optimal segment partitioning maximizing unigram log probabilities.
- **Automatic Fallback Wrapper**: `SentencePieceProcessor` attempts to load the native JNI library first; upon `UnsatisfiedLinkError` or JNI load failure, it transparently instantiates `KotlinSentencePieceModel` so tokenization always succeeds.

---

## 3. Direct NIO Buffers & Multi-Precision Tensor Extraction

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
          else -> throw IllegalStateException("Unsupported logits tensor type: $type")
      }
  }
  ```

---

## 4. Safe Hardware Bitmap Preprocessing

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

## 5. Native Tensor Lifecycle & C++ Memory Leak Prevention

`OnnxTensor` and `OrtSession.Result` allocate unmanaged C++ memory off the JVM heap.
- The JVM Garbage Collector has no visibility into native off-heap allocations. In high-frequency operations, unclosed tensors cause rapid out-of-memory crashes (`SIGSEGV` or `OutOfMemoryError`).
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

## 6. Hardware Acceleration & Automatic Runtime Fault Recovery

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
NNAPI drivers vary significantly across chipsets (Snapdragon, Dimensity, Tensor, Exynos). If an NNAPI driver crashes during `session.run(inputs)` due to tensor shape mismatches or unsupported ops, catching the exception and falling back to CPU prevents user-facing failure:
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
- **Mutex Guard**: Synchronize session initialization and inference using a coroutine `Mutex` (`sessionLock.withLock`) to prevent concurrent coroutines from creating duplicate ONNX sessions or destroying an active session mid-inference.
- **Model Invalidation**: If the user switches models in settings, safely close the active session and instantiate the new model.

---

## 7. Resilient Large Model Download Engine

Local AI models (~350 MB to 1.5+ GB) and tokenizer assets require dedicated background download management via WorkManager.

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
- Reconcile stale SharedPreferences flags against live `WorkManager.getWorkInfosForUniqueWorkLiveData` on application startup to prevent permanent UI lockouts.

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

## 8. Related Skills & Cross References

- **`android-fullstack-dev`**: Modern Android Clean Architecture, Jetpack Compose, Material 3, Accessibility Services, Room DB, and store publishing.
- **`security-compliance`**: ECDSA NIST P-256 cryptographic license verification and zero-knowledge data auditing.


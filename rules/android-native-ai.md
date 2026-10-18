---
trigger: glob
globs:
  - "**/*.kt"
  - "**/CMakeLists.txt"
  - "**/*.cpp"
  - "**/*.h"
---

# Android Native AI & On-Device Neural Network Standards

This scoped rule applies whenever modifying Kotlin AI/Vision code, ONNX Runtime Mobile, LiteRT, CMake configuration, or SentencePiece C++ JNI.

---

## 1. Direct NIO Buffer Rule
ONNX Runtime Java allocates direct NIO buffers in native C++ memory.
- CRITICAL FAILURE: Calling `.array()` on an ONNX direct `FloatBuffer` throws `UnsupportedOperationException: Direct buffer has no array`.
- MANDATORY PATTERN: Always duplicate the buffer and perform a bulk read:
  ```kotlin
  val floatBuffer = tensor.floatBuffer ?: return floatArrayOf()
  val copy = floatBuffer.duplicate()
  val array = FloatArray(copy.remaining())
  copy.get(array)
  ```

---

## 2. Multi-Precision Output Logits
Support `FLOAT`, `FLOAT16` (`Fp16Conversions.convertFp16BufferToFloatBuffer`), `BFLOAT16`, and `DOUBLE` output tensors.
Never assume output heads are `FLOAT32`. Always inspect `tensor.info.type` and route through appropriate decoding channels.

---

## 3. Safe Hardware Bitmap Preprocessing
CameraX and gallery pickers frequently return `Bitmap.Config.HARDWARE`.
- CRITICAL FAILURE: Accessing pixels via `bitmap.getPixels()` on a HARDWARE bitmap throws `IllegalArgumentException: unable to getPixels from a HardwareConfig bitmap`.
- MANDATORY PATTERN:
  1. Guard and convert hardware bitmaps to `Bitmap.Config.ARGB_8888`.
  2. Scale to model input dimensions (e.g., 224x224).
  3. Extract all pixels in a single bulk `getPixels(IntArray, ...)` call instead of pixel-by-pixel loops.
  4. Normalize color channels: `(pixelValue / 255.0f - mean) / std`.
  5. Allocate a direct `ByteBuffer` with native byte ordering (`ByteOrder.nativeOrder()`).
  6. Explicitly recycle intermediate copies in `try-finally` blocks.

---

## 4. Native Tensor Lifecycle & Leak Prevention
Wrap all `OnnxTensor` instances and `OrtSession.run()` results in `.use { ... }` or explicit `try-finally` blocks to prevent unmanaged C++ native memory leaks.

---

## 5. CMake 16 KB Page Memory Alignment (Android 15+)
Android 15 (API 35+) enforces 16 KB page memory alignment for native shared libraries.
In `CMakeLists.txt`:
```cmake
if(COMMAND target_link_options)
    target_link_options(<target> PRIVATE "-Wl,-z,max-page-size=16384")
else()
    set_target_properties(<target> PROPERTIES LINK_FLAGS "-Wl,-z,max-page-size=16384")
endif()
```
In module `build.gradle.kts`:
```kotlin
android {
    packaging {
        jniLibs {
            useLegacyPackaging = false
        }
    }
}
```

---

## 6. SentencePiece Tokenizer Standards
- Use Gemma token ID specifications: `PAD = 0L`, `EOS = 1L`, `maxLength = 64`.
- Never append literal `" </s>"` strings into raw input text prior to tokenization. Tokenize raw text and insert `EOS` programmatically at the end of the token ID array before padding with `PAD`.
- Synchronize JNI calls with `std::mutex` to prevent concurrent tokenization corruption across coroutines.
- Cache the loaded model path in memory to avoid repeated protobuf file reads from disk.

---

## 7. WorkManager Resilient Downloads
- Expedited requests must configure `OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST` to prevent silent OS drops when quota is exhausted.
- Range Resume Handling: When sending `Range: bytes=X-`, if server returns HTTP `200 OK` (ignoring Range), truncate existing file and restart from byte 0. If server returns HTTP `206 Partial Content`, seek to end and append.

---

## 8. Runtime Fault Recovery
If NNAPI hardware execution fails during `session.run(inputs)` due to unsupported ops or driver bugs, catch the exception, recreate a CPU-only `OrtSession`, and complete verification seamlessly.


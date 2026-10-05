# Unmatched JNI Declarations

This inventory documents the DEX `native` methods that were not matched to an
ELF `Java_*` export by the bridge generator. It closes a residual gap listed
in `05_PROTECTION_AND_GAPS.md`.

Source of truth:

```text
analysis/maps/jni_bridge_master.csv
analysis/maps/dex/dex_native_methods.csv
analysis/maps/native_library_map.json
```

## Counts

```text
rows total            2109
matched ("short")     1491
unmatched              618
```

The 618 unmatched rows are 206 unique declarations replicated across the
three ABIs (`206 * 3 = 618`).

## By Java Class

| Declarations per ABI | Class | Likely native provider | Resolution |
| --- | --- | --- | --- |
| 85 | `com.github.luben.zstd.Zstd` | `libzstd-jni-1.5.7-6.so` | static bridge |
| 23 | `com.google.androidgamesdk.GameActivity` | `libroblox.so` | partially exported / `RegisterNatives` |
| 14 | `com.github.luben.zstd.ZstdCompressCtx` | `libzstd-jni-1.5.7-6.so` | static bridge |
| 10 | `com.github.luben.zstd.ZstdDecompressCtx` | `libzstd-jni-1.5.7-6.so` | static bridge |
| 9 | `com.github.luben.zstd.ZstdDirectBufferCompressingStreamNoFinalizer` | `libzstd-jni-1.5.7-6.so` | static bridge |
| 8 | `androidx.camera.core.ImageProcessingUtil` | `libimage_processing_util_jni.so` | exported, overload lookup |
| 7 | `com.github.luben.zstd.ZstdOutputStreamNoFinalizer` | `libzstd-jni-1.5.7-6.so` | static bridge |
| 7 | `com.appsflyer.AppsFlyer2dXConversionCallback` | no bundled AppsFlyer ELF | optional callback surface |
| 6 | `com.github.luben.zstd.ZstdInputStreamNoFinalizer` | `libzstd-jni-1.5.7-6.so` | static bridge |
| 5 | `com.github.luben.zstd.ZstdBufferDecompressingStreamNoFinalizer` | `libzstd-jni-1.5.7-6.so` | static bridge |
| 5 | `com.github.luben.zstd.ZstdDirectBufferDecompressingStreamNoFinalizer` | `libzstd-jni-1.5.7-6.so` | static bridge |
| 3 | `il.j` | `libroblox.so` | obfuscated helper |
| 3 | `com.github.luben.zstd.ZstdDictDecompress` | `libzstd-jni-1.5.7-6.so` | static bridge |
| 3 | `com.github.luben.zstd.ZstdDictCompress` | `libzstd-jni-1.5.7-6.so` | static bridge |
| 3 | `backtraceio.library.nativeCalls.BacktraceCrashHandler` | `libbacktrace-native.so` | exported, overload lookup |
| 3 | `backtraceio.library.base.BacktraceBase` | `libbacktrace-native.so` | exported, overload lookup |
| 2 | `com.google.android.renderscript.Toolkit` | `librenderscript-toolkit.so` | exported, overload lookup |
| 2 | `backtraceio.library.BacktraceDatabase` | `libbacktrace-native.so` | exported, overload lookup |
| 2 | `com.roblox.universalapp.linking.JNILinkingProtocol` | `libroblox.so` | dynamic registration |
| 2 | `org.fmod.MediaCodec` | no bundled FMOD ELF | optional/media path |
| 1 | `com.roblox.engine.jni.NativeAppBridgeInterface` | `libroblox.so` | dynamic registration |
| 1 | `androidx.camera.core.impl.utils.SurfaceUtil` | `libsurface_util_jni.so` | exported |
| 1 | `org.webrtc.Logging` | no bundled WebRTC ELF | optional/media path |
| 1 | `org.webrtc.voiceengine.WebRtcAudioManager` | no bundled WebRTC ELF | optional/media path |

## Interpretation

- Most unmatched rows are third-party SDK JNI surfaces whose exports are
  present but whose names differ through overloads or static bridges.
- `GameActivity` is partially matched: `initializeNativeCode` resolves in
  `libroblox.so`; most other callback methods have no conventional ELF export
  and are likely registered at runtime with `RegisterNatives`.
- AppsFlyer, FMOD, and WebRTC declarations have no matching bundled ELF in
  this APK. They are optional or dynamically provided surfaces rather than
  unresolved Roblox engine code.
- The Roblox-specific unmatched rows (`il.j`, `JNILinkingProtocol`,
  `NativeAppBridgeInterface`) are dynamic registrations inside
  `libroblox.so`.

This does not indicate missing native implementations; it describes which
JNI names are not exported through the conventional `Java_*` symbol table.

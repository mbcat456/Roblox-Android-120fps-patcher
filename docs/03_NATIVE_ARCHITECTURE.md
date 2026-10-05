# Native Architecture

The engine is `libroblox.so`. The other ten libraries are third-party helpers
and thin JNI bridges. Per-library ELF inventories are under
`analysis/native/inventory/<abi>/`, and Ghidra exports are under
`analysis/native/<abi>/<library>/`.

## arm64 `libroblox.so`

From `analysis/maps/native/libroblox_arm64_profile.json`:

- ELF64 little-endian AArch64 shared object, no entry point (library)
- needed: OpenMAX AL, MediaNDK, Android, libm, OpenSL ES, GLESv2, EGL, log,
  dl, libc
- 542 imports, 4,123 dynamic exports, 530 `Java_*` exports
- 171,127 functions discovered by Ghidra; 167,526 lie in the executable first
  load segment and 3,601 are bogus zero-data labels created outside executable
  memory. Their cross-ABI breakdown is in
  `25_ZERO_DATA_NATIVE_LABELS.md`.
- 170,487 call-graph nodes and 695,065 call edges
- 142,166 defined strings

Function categories:

| Category | Count |
| --- | ---: |
| `FUN_` internal | 164,509 |
| `_INIT_` | 3,590 |
| thunks | 2,471 |
| JNI | 530 |
| data labels | 23 |

Most functions are 65-256 bytes (82,433), followed by 17-64 bytes (37,364)
and 257-1024 bytes (34,021). Only 76 functions exceed 16 KB.

## Sections

The executable `.text` section is approximately 72.6 MB, `.rodata` 12.3 MB,
`.eh_frame` 11.6 MB, `.bss` 11.6 MB, and `.data.rel.ro` 5.1 MB. Dynamic
relocations occupy 2.1 MB. Section addresses and sizes are preserved in the
profile JSON.

## Exports And Imports

`libroblox.so_symbols.json` lists 4,123 exports and 542 imports. The imports
are a narrow, audited surface: libc, pthreads, filesystem, Android asset APIs,
ANativeWindow, OpenSL ES, GLES/EGL, logging, dynamic loading, and Android
configuration. No raw socket/send/recv imports appear in the import table;
networking is internal.

## Strings And Indicators

`analysis/maps/native_string_index.json` contains 20,541 categorized string
matches across all native libraries. For arm64 `libroblox.so` alone:

- 2,310 URLs
- 2,252 Roblox endpoint references
- 640 cryptographic algorithm references
- 507 source paths
- 410 protection/debugging references
- 134 IPv4 literals
- 36 filesystem paths

The source paths and endpoint lists are useful anchors for renaming the
otherwise symbol-less `FUN_` functions.

`analysis/maps/native/native_build_identity.csv` records the GNU build ID and
Android NDK note for every native library. Roblox engine binaries are built
with NDK r28c; the helper libraries span r19, r25c, r27, r27-beta1, and r28c.
`analysis/maps/native/elf/` contains ABI-prefixed pyelftools JSON for each of
the 33 ELF files: header, program headers, sections, dynamic tags, 86,770
symbols, 82,544 relocations, and notes.

Across the three ABIs, `libroblox.so` consistently exposes 543 dynamic
defined symbols and 539 JNI exports, with 539-560 imports depending on ABI
(see `analysis/maps/native/libroblox_all_abi_dynamic_surface.csv`).

x86_64 full result: 111,094 functions emitted, 21 failed, 274.3 MB of C in 223
chunks; decompiler-derived call graph has 517,927 edges, and 48,837
function-to-string references were recovered. `libroblox_jni_annotated.c` is
generated for this ABI as well.

armeabi-v7a full result: 151,111 functions emitted, 50 failed, 322.1 MB of C
in 303 chunks; decompiler-derived call graph has 689,763 edges, and 126,947
function-to-string references were recovered.

Native DWARF-free strings retain 615 unique source paths. Roblox engine sources
are visible under
`/opt/teamcity-agent/work/App_Android_RobloxApp_Roblox_Google_ReleaseBuild/game-engine/Client`,
and the binary statically embeds Abseil, Boost, Djinni, OpenTelemetry C++,
protobuf, and a `webrtc-new` tree. The Android ident note records NDK `r28c`,
API 26, and build ID `2c6da207757c9f6ab48c7a3b30fe2f78e8f68eea`.
`analysis/maps/native/engine_source_subsystems.csv` classifies the 509
TeamCity engine paths: 406 dependency-tree paths, 88 third-party components,
and small Roblox-owned App/Rendering/WebRTC/Geometry/CrashReport groups.

## Decompiled Output

- quick no-analysis JNI pass: `libroblox.so_decompiled_quick/`
- full analyzed chunked pass: `libroblox.so_decompiled/` with indexed part
  files and `_index.csv`
- full arm64 result: 171,110 functions emitted, 17 failed, 343 C part files,
  338.5 MB of decompiled C; `libroblox_jni_annotated.c` contains the Java-
  annotated JNI bridge
- decompiler-derived maps: 1,063,554 function-to-symbol references and
  123,665 function-to-string-literal references across 30,252 functions
- functions/symbols/strings/calls JSON are the machine-readable maps

The JNI layer is named and directly readable. Internal functions retain
Ghidra addresses such as `FUN_01e96768`; cross-referencing them against the
call graph, strings, and source paths is how the remaining names are
recovered.

## Other Native Libraries

`libbacktrace-native.so` is the Backtrace crash handler, `libzstd-jni` is
Facebook Zstandard, `librenderscript-toolkit` is image processing, CameraX
supplies `libimage_processing_util_jni.so` and `libsurface_util_jni.so`,
Eigen supplies BLAS/LAPACK shims, and `libtrampoline.so` is a small Android
dynamic-loading trampoline. Each library has Ghidra function/string exports
under its ABI directory.

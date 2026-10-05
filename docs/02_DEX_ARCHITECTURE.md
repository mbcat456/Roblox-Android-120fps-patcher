# DEX / Java-Kotlin Architecture

## Size

- 13,374 JADX JSON class files, 21,457 indexed classes when inner classes are
  expanded
- recovered Java/Kotlin source: 13,373 files, 1,481,200 lines, 68 MB
- 124,902 call-graph methods and 223,305 resolved edges
- 703 native declarations
- 19,546 class renames, 63,323 method renames, 48,863 field renames, 632
package renames in the JADX JOBF map

An independent androguard parse in `analysis/maps/dex/hierarchy/` records
26,615 DEX class-definition entries, 139,646 encoded methods, 73,742 encoded
fields, 9,430,653 bytes of method bytecode, and 4,713,118 Dalvik instruction
units across `classes.dex`, `classes2.dex`, and `classes3.dex`. `classes.csv`
adds superclass, interfaces, source file, and access flags; `methods.csv` and
`fields.csv` carry per-member descriptors, flags, and bytecode sizes.
`analysis/maps/dex/deobfuscated_hierarchy.csv` joins that hierarchy with the
JOBF package/class maps so every minified class also shows its recovered name
and source path.

`analysis/maps/dex/dex_complexity_summary.json` and the adjacent
`top_*_by_*.csv` files size every method and class. There are 700 true native
methods, 6,914 abstract methods, and 34 methods over 4 KB of bytecode; the
largest methods are AppsFlyer and Google protobuf static initializers.

## Name Recovery

The application is R8/minified. JADX was run with deobfuscation and produced a
JOBF map at:

```text
com.roblox.client_2.738.1397-3092_minAPI26(arm64-v8a,armeabi-v7a,x86_64)(nodpi)_apkmirror.com.jobf
```

The human-readable inverse index is `analysis/maps/dex/deobfuscation_index.csv`.
For example, original package `xb` maps to source package `p544xb`, and many
short DEX names map to `C####` names. Kotlin classes also retain `@Metadata`;
`analysis/maps/dex/kotlin_module_index.csv` attributes 3,387 classes to 138
Kotlin modules.

## Package Composition

From `analysis/maps/dex/dex_package_counts.csv`:

- Roblox-owned Java/Kotlin: 626 classes
- Google Play services, ML Kit, billing, Firebase, measurement: 4,267 classes
- Persona identity verification SDK: 3,056 classes
- AndroidX/Jetpack: 1,200 classes
- AppsFlyer: 335 classes
- OkHttp family: 212 classes
- Kotlin stdlib/coroutines: 183 classes
- Backtrace crash reporting: 134 classes
- remaining: 11,351 classes, mostly minified/third-party

Top minified packages by class count are `xb` (263, Google measurement),
`ob` (137), `qu` (111), `n0` (107), and `pb` (71). The Kotlin module index
shows the largest recovered modules are kotlinx-coroutines, kotlin-stdlib,
Persona `ui-step-renderer`, OkHttp, Coil, Roblox `NativeShell`, WorkManager,
Persona inquiry internals, and Google credentials.

## Native Boundary

The corrected bridge is in `analysis/maps/jni_bridge_arm64.json`:

- 530 arm64 `Java_*` functions
- 703 DEX native declarations across all bundled libraries
- 497 declarations matched to `libroblox.so` (identical across all three ABIs)
- 42 native JNI exports have no matching Java declaration in the supplied
  DEX files; they are orphaned or forward-compatible symbols
- unmatched DEX declarations belong to other libraries, such as zstd-jni,
  CameraX image processing, Backtrace, AppsFlyer, GameActivity, and FMOD

`analysis/maps/dex/dex_load_library_sites.csv` records the explicit
`System.loadLibrary` calls for CameraX, SurfaceUtil, Backtrace, and
Renderscript. `libroblox.so` is loaded by Roblox startup code.

## Call Graph

The JADX call graph is in `analysis/dex/jadx_src/callgraph.json` and summarized
in `analysis/dex/callgraph_summary.json`. Highest-degree hubs are Google
measurement, Persona government-id workflow, and Roblox startup classes.
`ActivityNativeMain.onCreate` has 84 outgoing calls and
`startup.NativeHelper` is one of the largest Roblox-owned components.

## Decompilation Quality

JADX produced Java for 13,373 source files. `jadx_source_gaps.json` records
142 methods that exceeded region/type-inference limits, mostly deeply nested
Kotlin coroutine state machines in Persona, OkHttp, protobuf, and a few Roblox
workers. A fallback/raw-instruction pass is under `analysis/dex/fallback/` for
the affected classes, and a complete fallback-mode source tree covering all
14,102 emitted files (2,518,039 lines, 110 MB) is under
`analysis/dex/jadx_fallback/`. The corrected 71-method breakdown is in
`26_JADX_FALLBACK_METHODS.md`.

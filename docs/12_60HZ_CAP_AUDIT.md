# 60 Hz / FPS Cap Audit - Roblox Android 2.738.1397 (build 3092)

This report documents every 60 Hz / 60 FPS site found in the decrypted APK
artifacts in this workspace:

- Java/Kotlin DEX: `analysis/dex/jadx_src/sources`
- Native engine: `analysis/native/{arm64-v8a,armeabi-v7a,x86_64}/libroblox`
- RBXM/Luau frontend: `apk_extracted/assets` and
  `analysis/recovery/modulescripts`
- APK resources and bundled flag cache: `apktool_clean` and
  `apk_extracted/assets`

Method: static analysis of JADX sources/smali, Ghidra 12.1.2 decompilations of
the three `libroblox.so` ABIs, Capstone disassembly at verified file offsets,
RBXM property decoding, and Luau v7 bytecode decoding of all 34,878
ModuleScript payloads. No runtime device was used, so the report describes
what the code does rather than a measured device trace.

## 1. Java / Android Surface Layer

There is no stock Java hardcoded 60 Hz cap.

- `nl/C8594a.java`
  - `m35285a(Display)` is just `Display.getRefreshRate()`.
  - `m35295k(Display)` is just `Display.getSupportedRefreshRates()`.
- `fi/SurfaceHolderCallbackC5291r0.java`
  - line 222 passes the supported rate array to
    `NativeGLInterface.nativePassSupportedRefreshRates(...)`.
  - line 265 passes the current rate to
    `NativeGLInterface.nativePassCurrentDisplayRefreshRate(...)`.
- `com/roblox/engine/jni/NativeGLInterface.java`
  - line 108 declares `nativePassCurrentDisplayRefreshRate(float)`.
  - line 112 declares `nativePassSupportedRefreshRates(float[])`.
- Stock `MainGameActivity` and `ActivityNativeMain` contain no
  `preferredDisplayModeId`, `Surface.setFrameRate`, display-mode selection, or
  refresh-rate override. Those calls exist only in the local mod builds under
  `mod/`, not in `apktool_clean` / `apk_extracted`.

The Java layer therefore reports the actual Android display rate to native.
The 60 FPS behavior is imposed after that handoff, in the native engine.

## 2. Native Task Scheduler Target FPS

`TaskSchedulerTargetFps` is initialized to `0` on all ABIs. The getter treats
zero as "use the default", and that default is exactly `0x3c` (60). The upper
bound is `0xf0` (240), so the scheduler itself is not a 240 cap; it is a
default-60 target until the flag or display rate supplies another value.

| ABI | flag init | getter with 60 fallback | interval consumer |
| --- | --- | --- | --- |
| arm64-v8a | `_INIT_3538`, `part_0018.c:7531-7538`; `DAT_0736a418 = 0` | `FUN_024c82b8`, `part_0028.c:31281-31304`; `iVar1 = 0x3c` when flag is zero | `FUN_062c9578` / `FUN_062c95dc`, `part_0335.c:20187-20348` |
| x86_64 | `_INIT_3543`, `part_0015.c:23609-23610`; `DAT_07c82698 = 0` | `FUN_025d3e54`, `part_0023.c:13406-13432`; `iVar1 = 0x3c` when flag is zero | `FUN_06bc8f7c` / `FUN_06bc8fda`, `part_0217.c:17701-17723` |
| armeabi-v7a | `_INIT_3536`, `part_0144.c:47563-47566`; `DAT_050f769c = 0` | `FUN_02b5f644`, `part_0155.c:7476-7498`; `iVar1 = 0x3c` when flag is zero | `FUN_0442c358` / `FUN_0442c3c0`, `part_0295.c:25642-25674` |

The interval formula in all three ABIs is:

```text
requested_ms = 1000 / target_fps
```

With no user cap and the stock flag value of zero, this is `1000 / 60 =
16.666... ms`. `FUN_062c95dc` and its siblings then choose
`max(requested_ms, 1000 / display_cap)` and send the resulting interval to the
scheduler. The existing local mod replaces the `60` return with `120`; stock
code does not.

## 3. Display Refresh Rate Path and 60 Floor

The JNI setter does not cap at 60. It stores the reported rate and only logs
an error when the rate is below 15 Hz.

- arm64: `Java_com_roblox_engine_jni_NativeGLInterface_nativePassCurrentDisplayRefreshRate`,
  `part_0026.c:10559-10600`; `DAT_06e35a80 = (double)param_1`.
- x86_64: `part_0021.c:11335-11376`.
- armeabi-v7a: `part_0153.c:11024-11065`.

The hardcoded 60 appears one step later, in display setup, as a floor rather
than a ceiling:

| ABI | function | behavior |
| --- | --- | --- |
| arm64-v8a | `FUN_024c81d4`, `part_0028.c:31226-31276` | `if (iVar4 < 0x3d) iVar4 = 0x3c;` then stores `iVar4` at `+0x30` |
| x86_64 | `FUN_025d3d2e`, `part_0023.c:13359-13401` | `iVar2 = 0x3c; if (0x3c < (int)__x) iVar2 = (int)__x;` |
| armeabi-v7a | `FUN_03d712f0`, `part_0263.c:15571` and `15757-15761` | `if (iVar9 < 0x3d) iVar9 = 0x3c;` |

Effect: if Android reports 59 Hz or lower, Roblox substitutes 60. A 120 Hz
display remains 120 at this site, so this is not the general "120 display is
forced to 60" cap; it is an explicit 60 minimum used when the display input
is missing, invalid, or below 60.

The supported-rate path copies the Java `float[]` into a native vector without
rewriting values. arm64 implementation: `part_0026.c:10604-10706`.

## 4. Frame Rate Manager / `gfx/frm/frameRateCap`

This is the main renderer-side 60 default. The fast flag
`GraphicsOptimizationModeFRMFrameRateTarget` is initialized to 60 on every
ABI, and the renderer copies that value into the
`gfx/frm/frameRateCap` CVar.

| ABI | default-60 global | getter | renderer copy site |
| --- | --- | --- | --- |
| arm64-v8a | `DAT_06b75448 = 0x3c`, `part_0003.c:29052-29053` | `FUN_02ed0d7c` | `FUN_0268e900` calls getter at file offset `0x026926f0`, then sets the CVar at `0x02692704` |
| x86_64 | `DAT_0748e5c0 = 0x3c`, `part_0003.c:28913-28914` | inline consumer `FUN_032dec60`, `part_0063.c:21436` reads the same FRM target global | the CVar string is present at file offset `0x2fa57a`, but the x86_64 decompiler did not attach it to a named setter function |
| armeabi-v7a | `DAT_04a58a30 = 0x3c`, `part_0131.c:646-648` | `FUN_0161c010`, `part_0034.c:12333-12338` | `FUN_02d5324c`, `part_0166.c:37594-37595` |

Verified arm64 machine code:

```text
01e06be0  mov w8, #0x3c
01e06be4  adrp x9, #0x6a75000
01e06be8  add  x9, x9, #0x448
01e06bec  str  w8, [x9]          ; DAT_06a75448 = 60

02ed0d7c  adrp x8, #0x6a75000
02ed0d80  ldr  w0, [x8, #0x448] ; returns DAT_06a75448
02ed0d84  ret

026926f0  bl   0x2ed0d7c
02692704  adrp x1, #0x30f000
02692708  add  x1, x1, #0x770 ; "gfx/frm/frameRateCap"
0269270c  mov  x0, x8
02692710  blr  x9             ; CVar int setter
```

The string `gfx/frm/frameRateCap` is at:

- arm64-v8a file offset `0x30f770`
- x86_64 file offset `0x2fa57a`
- armeabi-v7a file offset `0x2bb39e`

Related reflection and settings entries:

- `FramerateCap` property registration: arm64 `part_0009.c:40948`, getter
  `FUN_0437951c`, setter `FUN_04379524`; the property storage field is
  `+0x14c`. Local mod patch offsets for reference: arm64 `0x437951c`,
  `0x4379544`, `0x4379550`; armeabi-v7a getter `0x160c010`.
- `GameBasicSettingsFramerateCap` fast-flag registration: arm64
  `part_0003.c:4806`, callback `LAB_02eaca1c`.
- `GetDefaultFramerateCap` reflection registration: arm64
  `part_0009.c:39339`; the disabled fast path is `FUN_045a2738`,
  `part_0193.c:17759-17766`.

The settings property itself did not yield a direct numeric-60 initialization
in decompiled code; the hard 60 comes from the
`GraphicsOptimizationModeFRMFrameRateTarget` mirror documented above.

## 5. Physics Step Limit

`PhysicsStepLimitMaxFPS` is another explicit native default-60:

| ABI | default site | consumer |
| --- | --- | --- |
| arm64-v8a | `DAT_06d3f228 = 0x3c`, `part_0011.c:25828-25829`, in `_INIT_2111` | `FUN_0277ca8c`, `part_0042.c:20050-20057` uses `1.0 / DAT_06d3f228` as the minimum step interval |
| x86_64 | `_DAT_076577e0 = 0x3c`, `part_0010.c:24603-24604`, in `_INIT_2108` | same flag via the generic fast-flag table |
| armeabi-v7a | `DAT_04b9c9bc = 0x3c`, `part_0138.c:24383-24384`, in `_INIT_2109` | `part_0166.c:25883` and `part_0177.c:28363` |

The arm64 consumer computes `1.0f / 60.0f` and uses the larger of that value
and the measured average step duration. In stock builds this means physics
does not step more often than 60 Hz unless this flag is overridden.

## 6. Physics Simulation Rate Enum

The reflection enum `PhysicsSimulationRate` hardcodes a 60 Hz choice:

- arm64 `FUN_041ec04c`, `part_0174.c:6885-6889`:
  - `Fixed240Hz` = 0
  - `Fixed120Hz` = 1
  - `Fixed60Hz` = 2
- armeabi-v7a `part_0117.c:2425-2429` contains the same three entries.
- x86_64 contains the `Fixed60Hz` string in its rodata (`libroblox.so_strings.json`),
  although the small enum constructor did not produce a separate C function
  in the exported x86_64 decompilation.

This enum makes 60 Hz an available simulation-rate choice; the default value
is stored in reflection metadata rather than in a visible assignment in the
decompiled constructors.

## 7. Simulation 60 Hz Feature Flags

These names hardcode a 60 Hz mode in the adaptive simulation system:

| flag | stock native default | bundled remote default | behavior |
| --- | --- | --- | --- |
| `AuroraLimit60HzRenderSim` | `0` / false | not present in bundled dict | no active consumer found in arm64 decompilation; appears experimental/dead |
| `SimAdaptiveEnable60HzParts` | `0` / false | `True` | when enabled raises selected adaptive step from 2 to 4 in `part_0237.c` |
| `DebugSimAdaptiveEnable60HzHumanoids` | `0` / false | not present in bundled dict | debug override controlling humanoid adaptive stepping |
| `DFFlagSimAdaptiveAllow60HzControllerManager` | not declared in native strings | `True` | remote-only controller-manager companion flag |

Arm64 init sites: `part_0015.c:4242-4243`, `4361-4366`. Consumers:
`part_0237.c:6200-6210`, `6488-6539`, `6606-6686`.

These flags enable 60 Hz simulation paths; they do not by themselves convert
an arbitrary display rate to 60.

## 8. VSync, Swap Interval, and Refresh Bounds

These are adjacent to the 60 question but are not unconditional 60 caps:

- `EnableAndroidVsync`
  - native default `0` on all ABIs
  - bundled remote `applicationSettings` value `True`
  - when false, EGL swap interval is 0; when true, interval is normally 1.
- `GLES3CustomSwapInterval`
  - native default `0` / false
- `GLES3CustomSwapIntervalValue`
  - native default `2`
  - only used when `GLES3CustomSwapInterval` is also true. A swap interval of 2
    on a 120 Hz panel would present every other refresh, effectively 60 FPS,
    but the stock flag defaults keep this path disabled.
- `DebugExperimentalVSyncFramePacing` and
  `DebugExperimentalVSyncFramePacingForce`
  - native defaults `0` / false on all ABIs.
- `RefreshRateLowerBound`
  - native default `0x48` (72), not 60.
- `QuestDisplayRefreshRate`
  - Quest/Meta-specific property; Android does not use it and no fixed 60
    default was found in the Android path.

Arm64 init references: `part_0017.c:3613-3624`, `part_0012.c:2587-2588`,
`part_0010.c:1457`, `part_0005.c:641-647`.

## 9. Homepage / Frontend Luau Defaults

The bundled Lua frontend has three genuine 60 values:

### 9.1 React scheduler desired frame rate = 60

Both bundled copies of `SchedulerHostConfig.default` contain:

```text
analysis/recovery/modulescripts/model_022/.../Scheduler/forks/SchedulerHostConfig.default.luauasm:646
analysis/recovery/modulescripts/model_024/.../Scheduler/forks/SchedulerHostConfig.default.luauasm:646

  33 L 19 LOADN A=18 B=60 C=0
```

The preceding `LOADK` is constant `ReactSchedulerDesiredFrameRate`. Thus the
homepage React scheduler is registered as:

```text
ReactSchedulerDesiredFrameRate = DefineFastInt(..., 60)
ReactSchedulerMinFrameRate    = DefineFastInt(..., 30)
```

This makes 60 the default desired frame rate for the UniversalApp React /
homepage scheduling loop.

### 9.2 Scrolling performance tracker target FPS = 60

`LuauForgeChunks/bundled.luauasm` proto 54187:

```text
line 2314636: LOADN A=6 B=60 C=0
line 2314755: K6 "ScrollingPerfTrackerTargetFPS"
```

This is `DefineFastInt("ScrollingPerfTrackerTargetFPS", 60)`. It is a
telemetry/performance-target constant, not the renderer cap, but it is a
hardcoded 60 in the homepage frontend.

### 9.3 FramerateCap choices include 60

`InGameMenu/Resources/Constants.luauasm` builds the settings list:

```text
lines 186-193:
  LOADN 60, 120, 144, 160, 165, 180, 200, 240
  key = FramerateCaps

lines 196-200:
  LOADN 60, 120, 144, 240
  key = FramerateCaps
```

The two branches are behind `MoreFramerateOptions`. 60 is the first/default
entry in both lists and is shown as the default frame-rate option by the
in-game settings UI.

### 9.4 Scheduler flags that default to -1, not 60

`GetSchedulerFlagOverrides.luauasm` defines these with default `-1`:

- `LuaAppSchedulerYieldInterval`
- `LuaAppSchedulerDeferredWork`
- `LuaAppSchedulerHeartbeatFrameMarker`
- `LuaAppSchedulerTargetMsByHeartbeatDelta`
- `LuaAppSchedulerNumberOfLookbackFrames`
- `LuaAppSchedulerLookbackUseRingBuffer`
- `LuaAppSchedulerDesiredFrameRate`
- `LuaAppSchedulerMinimumFrameRate`
- the same `LuaInExpScheduler*` set

When those are absent, the runtime falls back to the native scheduler defaults
described in section 2.

## 10. Assets, RBXM Properties, and Android Resources

- RBXM `Source` blobs for the 34,878 recovered frontend ModuleScripts were
  scanned. Apart from the Lua values above, there is no Lua hardcoded 60 Hz
  cap. `content/avatar/character.rbxm` trips the generic LZ4 chunk decoder,
  but a direct byte-pattern scan of that 26,887-byte model finds no
  frame-rate, FPS, refresh-rate, VSync, or `60 Hz/FPS` terms.
- The only frame-related RBXM property names found are
  `ParticleEmitter.FlipbookFramerate` in `Maquettes.rbxl` and `Mobile.rbxl`.
  Their decoded values are `1.0`, not 60.
- `rofiler.js` contains 60 only as time conversion (`1, 60, 60*60, ...`) and
  UI offsets; it does not cap the renderer.
- Android `res/` XML files contain no refresh-rate, VSync, or FPS cap. The
  many `60` matches are Material color swatches, dp dimensions, and vector
  path coordinates.
- The bundled flag dictionary contains no numeric 60 override for
  `TaskSchedulerTargetFps`, `GraphicsOptimizationModeFRMFrameRateTarget`, or
  `PhysicsStepLimitMaxFPS`, so their native defaults in sections 2, 4, and 5
  are the active stock values.

Relevant bundled remote booleans:

```text
FFlagEnableAndroidVsync                          = True
FFlagEnableRefreshRateGuard                      = True
DFFlagSimAdaptiveEnable60HzParts                 = True
DFFlagSimAdaptiveAllow60HzControllerManager      = True
FFlagGameBasicSettingsFramerateCap5              = True
FFlagMoreFramerateOptions                        = True
FFlagTaskSchedulerLimitTargetFpsTo2402           = True
FFlagPerformanceControlGetDisplayRefreshRate     = True
FFlagPerformanceControlRespectUserFpsOverridden  = True
FFlagCaptureEngineManagesFrameRate2              = True
```

## 11. Canonical Hardcoded 60 Checklist

These are the sites that actually impose or expose a 60 Hz / 60 FPS value in
the stock APK:

1. `TaskSchedulerTargetFps` zero-value fallback = 60.
   - arm64 `FUN_024c82b8`, x86_64 `FUN_025d3e54`, armeabi-v7a `FUN_02b5f644`.
   - The `TaskScheduler` constructor also stores `1.0 / 60.0` seconds at
     object offset `+0xb8`; see
     `13_SCHEDULER_DEFAULT_AND_FRM_INIT_PATCH.md`.
2. Display-rate floor = 60 when reported rate is below 61.
   - arm64 `FUN_024c81d4`, x86_64 `FUN_025d3d2e`, armeabi-v7a `FUN_03d712f0`.
3. `GraphicsOptimizationModeFRMFrameRateTarget` default = 60, copied into
   `gfx/frm/frameRateCap`.
   - arm64 getter `FUN_02ed0d7c`, armeabi-v7a getter `FUN_0161c010`.
4. `PhysicsStepLimitMaxFPS` default = 60.
   - all three ABIs.
5. `PhysicsSimulationRate.Fixed60Hz` enum value = 2.
   - all three ABIs.
6. `ReactSchedulerDesiredFrameRate` Luau default = 60.
   - UniversalApp `SchedulerHostConfig.default`.
7. `ScrollingPerfTrackerTargetFPS` Luau default = 60.
   - UniversalApp bundled Luau chunk.
8. `FramerateCaps` settings list starts with 60 in both
   `MoreFramerateOptions` branches.
   - InGameMenu Constants Luau module.

## 12. False Positives and Non-Cap 60 Values

These contain the number 60 but do not cap the renderer at 60 Hz:

- DEX `androidx/recyclerview/widget/RecyclerView.java:6941-6945` and
  `apktool_clean/smali/androidx/recyclerview/widget/RecyclerView.smali:9767`:
  60.0f is the smooth-scroll frame-interval fallback used by the RecyclerView
  library.
- DEX `p146g8/C5691k.java:2263` / `apktool_clean/smali/g8/k.smali:3696`:
  60.0f is an angle-to-degrees conversion.
- Native `NetClientFramesUnder60Fps`, `AveragePauseTimeFramesWithJDIOUnder60Fps`,
  and `body_60fps_cnt`: telemetry counters/reporting labels.
- Native `ScreenTimeImplPollingIntervalSeconds`, performance-control report
  intervals, and similar values set to 60 are seconds, not Hz.
- Lua `GameSettingsConstants` proto 1, `luauasm:167`: `LOADN 60` is assigned
  to `DeviceFrameInput` (audio device frame count), with `DeviceFrameOutput`
  next at 61. It is not a display FPS cap.
- `RefreshRateLowerBound` is 72, not 60.
- `CaptureVideoMaxFrameRate` is 30, not 60.
- `FrameRateMSToReduceTouchEvents` is 33 ms, not 60.
- `Is30FpsThrottleEnabled` is a 30 FPS feature, not 60.

## 13. Generated Scan Artifacts

The following reproducible scanner outputs are stored under
`analysis/docs/artifacts/`:

- `rbxm_60fps_raw_scan.tsv` - raw RBXM Source blob and property scan.
- `luau_numeric_60_scan.tsv` - all numeric/instruction-60 Luau constants with
  frame-rate context.
- `json_60fps_scan.tsv` - JSON/flag-dictionary key and value scan.
- `native_60_relevant_strings.tsv` - frame/refresh/vsync-related strings from
  all three native ABIs.
- `native_c_60_defaults.tsv` - native fast-flag declarations whose default is
  exactly 60.
- `native_c_60_near.tsv` - all native `0x3c` defaults near frame-rate strings,
  used to separate real caps from unrelated 60 values.

Tools used:

- `tools/audit_60fps_rbxm.py`
- `tools/audit_luau_60.py`
- `tools/audit_json_60fps.py`
- `tools/audit_native_strings_60.py`
- `tools/audit_native_c_60.py`
- `tools/audit_native_c_60_near.py`
- `tools/disasm_range.py`
- `tools/scan_arm64_calls.py`
- `tools/scan_arm64_adrp_target.py`

Static-analysis limitation: these conclusions follow the shipped code paths.
They do not include device-specific ROM voting, MIUI secure settings, display
driver behavior, or runtime flag values fetched after installation. The local
mod README documents the separate MIUI `miui_refresh_rate` vote observed on
the test device.

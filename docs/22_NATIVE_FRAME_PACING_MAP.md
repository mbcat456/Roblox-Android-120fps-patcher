# Native Frame Pacing Map

This document maps the arm64 render/pace control path from the Android
refresh-rate JNI handoff down to the task-scheduler interval and the Frame
Rate Manager. It complements the 60 Hz inventory in
`12_60HZ_CAP_AUDIT.md` and the latest patch evidence in
`13_SCHEDULER_DEFAULT_AND_FRM_INIT_PATCH.md`.

All Ghidra addresses are for arm64 `libroblox.so`. File offsets in the ELF are
`Ghidra address - 0x100000` for the identity-mapped first load segment.

## 1. Display Rate Into Native

```text
fi/r0.smali (SurfaceHolder callback)
  -> Lnl/a;->a(Display)F                 // mod returns 120.0f
  -> NativeGLInterface.nativePassCurrentDisplayRefreshRate(F)

Java_com_roblox_engine_jni_NativeGLInterface_nativePassCurrentDisplayRefreshRate
  @ 02432d58, part_0026.c:10559
  DAT_06e35a80 = (double)param_1

Java_com_roblox_engine_jni_NativeGLInterface_nativePassSupportedRefreshRates
  @ 02432e30, part_0026.c:10604
```

The JNI setter only rejects values below 15 Hz. It does not force 60.

## 2. Display/Scheduler Setup

```text
FUN_024c8448 @ 024c8448, part_0028.c:31345
  returns DAT_06e35a80                  // current display refresh rate

FUN_024c81d4 @ 024c81d4, part_0028.c:31226
  builds the initial scheduler target
  - policy off: 1000 / FUN_024c82b8()
  - policy on:  FUN_062c9c9c()
  - writes display cap through FUN_062c9950()
  - if display rate < 61, substitutes 60

FUN_024c82b8 @ 024c82b8, part_0028.c:31281
  reads DAT_0736a418 (TaskSchedulerTargetFps)
  clamps high value to 240
  returns 60 when the flag is zero       // patched to 120
```

## 3. TaskScheduler Object Constructor

`FUN_0234f810` at Ghidra `0234f810` allocates and initializes the scheduler.
The render interval is a double at object offset `+0xb8`:

```text
stock:
  mov  x8, #0x1111111111111111
  movk x8, #0x3f91, lsl #48       ; 1/60 s
  stur x8, [x23, #-0x38]          ; +0xb8

patched:
  movk x8, #0x3f81, lsl #48       ; 1/120 s
```

This is the authoritative fallback interval. The policy functions below can
overwrite it later, but skipping their initialization no longer leaves the
scheduler at 60.

## 4. ApplicationFrameRate Policy

The policy object and log category are initialized in `_INIT_3498` at
`062c9d48`, `part_0335.c:20614`.

```text
FUN_062c9500 @ 062c9500       policy singleton, "ApplicationFrameRate"
FUN_062c9830 @ 062c9830       policy-enabled predicate

FUN_062c9578 @ 062c9578       requested interval:
                              user cap != 0 ? 1000/user : 1000/default
FUN_062c95dc @ 062c95dc       resolve effective interval:
                              max(requested_ms, 1000/display_cap)
                              log "[FLog::ApplicationFrameRate] ..."
                              -> FUN_0630df7c(ms * 0.001)

FUN_062c984c @ 062c984c       set user cap at +0x8
FUN_062c9950 @ 062c9950       set display cap at +0xc
FUN_062c99e4 @ 062c99e4       set requested target ms at +0x10
FUN_062c9ab4 @ 062c9ab4       set presentation-pacing flag at +0x18
FUN_062c9b4c @ 062c9b4c       set VR active/throttling at +0x19/+0x1a
FUN_062c9c04 @ 062c9c04       set forced pacing flag at +0x1b
FUN_062c9c9c @ 062c9c9c       resolve final interval
```

The interval writer is `FUN_0630df7c` at `0630df7c`, `part_0337.c:5576`. It
stores seconds at scheduler offset `+0xb8` (`+200` when the field at `+0xc1`
is set). `FUN_0630de98` at `0630de98` stores the pacing-mode flag at `+0xc0`.

## 5. FramerateCap / Settings Bridge

```text
FUN_0268e900 @ 0268e900, part_0038.c:24084
  renderer/platform setup
  at 026926f0 calls FUN_02ed0d7c()
  at 02692704 sets CVar "gfx/frm/frameRateCap" to that value

FUN_02ed0d7c @ 02ed0d7c, part_0088.c:7363
  returns DAT_06b75448                // patched to 120

FUN_0437951c @ 0437951c               FramerateCap property getter
FUN_04379524 @ 04379524               FramerateCap property setter
                                      // patched compare/store 120

FUN_02eae53c @ 02eae53c, part_0081.c:9064
  non-policy startup path
  reads FramerateCap getter
  calls FUN_0630df7c(1.0 / cap)
  calls FUN_0630de98(cap != -1)
```

The `FramerateCap` reflection registration is at `part_0009.c:40948`.

## 6. Frame Rate Manager / Dynamic Resolution

The `Engine.Rendering.FrameRateManager` category is registered at
`part_0007.c:16578`. Its primary frame submission routine is
`FUN_02fce63c @ 02fce63c`, `part_0088.c:5720`, with the telemetry logger
`FrameRateManager::submitCurrentFrame`.

Target frame time for the quality controller is computed by
`FUN_02fce4cc @ 02fce4cc`, `part_0088.c:5631`:

```text
FUN_02fd0d88 @ 02fd0d88       quality bias / scale input
FUN_02fd0cc0 @ 02fd0cc0       quality scale / frame-time input
FUN_02fce4cc                  target frame time in milliseconds
FUN_02fce2a0 @ 02fce2a0       apply target to the DRS controller
FUN_02fce63c                  submitCurrentFrame statistics/quality update
```

`DAT_06b75448` is `GraphicsOptimizationModeFRMFrameRateTarget`. Its arm64
initializer has been changed from `0x3c` to `0x78`.

Related FRM values registered in `_INIT_381` at `01f06324`,
`part_0003.c:28861`:

```text
DAT_06b75418 = 0x13  GraphicsOptimizationModeMinFrameTimeTargetMs
DAT_06b75430 = 0x50  GraphicsOptimizationModeMaxFrameTimeTargetMs
DAT_06b75448 = 0x3c  GraphicsOptimizationModeFRMFrameRateTarget  (patched)
```

## 7. Non-Render 60 Hz Sites

These are documented because they contain 60 but are intentionally not part
of the render FPS patch:

```text
PhysicsStepLimitMaxFPS                 DAT_06d3f228 = 0x3c
RunService fixed interval              part_0030.c:13377, 1/60 s
PhysicsSimulationRate.Fixed60Hz        reflection enum
```

Changing the RunService/physics defaults would alter simulation rate and
gameplay, not just presentation rate, so the mod leaves them stock.

## 8. Patch And Verification

All arm64 render-path patches are applied by
`tools/patch_native_fps_cap.py`. The signed scheduler4 artifact is documented
in `mod/README.md`.

## 9. Cross-ABI Correspondence

| Role | arm64-v8a | x86_64 | armeabi-v7a |
| --- | --- | --- | --- |
| Scheduler constructor | `FUN_0234f810` | `FUN_0243f372` | `FUN_02a57840` |
| Constructor interval store | file `0x0224f8c0` | file `0x0233f433` | file `0x02a478f6` |
| Constructor value patched | `0x3f81...` | `0x3f81...` | `0x3f81...` |
| Target-FPS zero fallback | `FUN_024c82b8` | `FUN_025d3e54` | `FUN_02b5f644` |
| Display setup | `FUN_024c81d4` | `FUN_025d3d2e` | `FUN_03d712f0` |
| FRM target global | `DAT_06b75448` | `DAT_0748e5c0` | `DAT_04a58a30` |
| FRM direct consumer | `FUN_02fce4cc` | `FUN_032dec60` | `FUN_01619b78` |
| FRM getter patched | `FUN_02ed0d7c` | not isolated | `FUN_0161c010` |

The scheduler constructor default is patched on all three ABIs. The arm64
FRM global initializer is also patched; the arm32 getter is patched instead,
and control-flow traversal shows the x86_64 `_INIT_378` constructor contains
no reachable immediate `0x3c` store. That FRM value is data-driven in the
x86_64 build rather than a single patchable immediate.

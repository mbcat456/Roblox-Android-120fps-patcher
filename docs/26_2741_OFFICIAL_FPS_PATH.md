# Roblox 2.741.1061 Official Framerate-Cap Path

This document maps the 2.741.1061 arm64 code that decides whether the
settings UI shows Roblox's official Maximum Framerate row and whether the
renderer uses the ApplicationFrameRate policy. The previous 2.738 port forced
several downstream constants to 120, but did not open these gates, so the
engine could still stay on its 60 FPS startup policy.

All addresses in this document are file offsets and virtual addresses in the
new arm64 split library `lib/arm64-v8a/libroblox.so`. The first load segment
has `p_vaddr == p_offset`, so the two are interchangeable.

## 1. Luau Gate

`GameSettings.luau` contains:

```luau
local var97 = game:GetEngineFeature("GameBasicSettingsFramerateCap")
...
if var97 then
   var0.framerate_cap = tostring(var13.FramerateCap)
end
```

The dropdown construction is also under `var97`. The engine feature value is
the byte at `0x6c10b90`:

```text
0x2e06e50  adrp x8, #0x6c10000
0x2e06e54  ldrb w0, [x8, #0xb90]
0x2e06e58  ret
```

This callback is registered with the string
`GameBasicSettingsFramerateCap` at `0x1e47f6c`. The byte is in `.bss`, is
initially zero, and is written back to zero by the flag-table initializer at
`0x2055b64`, so the value itself cannot be changed by a file patch.

The mod therefore changes the callback itself:

```text
0x2e06e50  48f001d000416e39 -> 20008052c0035fd6
           adrp/ldrb       -> mov w0, #1 / ret
```

## 2. Native Startup Gate

The big renderer/platform setup routine at `0x22c7cfc` has the same flag
check. With the flag false it skips an entire block that obtains the settings
singleton (`0x44bf55c`) and applies the requested frame-rate target.

```text
0x22c7cfc  adrp x8, #0x6c10000
0x22c7d00  ldrb w8, [x8, #0xb90]
0x22c7d04  cbz  w8, #0x22c7db0
0x22c7d08  bl   #0x44bf55c
```

The check is forced enabled so this setup block always runs:

```text
0x22c7d00  08416e39 -> 28008052
           ldrb    -> mov w8, #1
```

## 3. GetDefaultFramerateCap

The reflection wrapper for `GetDefaultFramerateCap()` reads the same flag and
raises `GetDefaultFramerateCap() is not enabled.` when it is false. The
message string is at `0x43de4e`.

```text
0x4609b04  adrp x8, #0x6c10000
0x4609b08  ldrb w8, [x8, #0xb90]
0x4609b0c  tbz  w8, #0, #0x4609b14
0x4609b10  b    #0x24203bc
0x4609b14  ... fatal error path
```

The wrapper now returns 120 directly:

```text
0x4609b04  283001f008416e3948000036
        -> 000f8052c0035fd61f2003d5
           mov w0, #120 / ret / nop
```

`0x24203bc` is the TaskSchedulerTargetFps resolver. Its zero-value fallback
is already patched to return 120 at `0x24203ec`.

## 4. ApplicationFrameRatePolicy

The policy flag is the byte at `0x6dbb810`. Its engine-feature reader is:

```text
0x6383d68  adrp x8, #0x6dbb000
0x6383d6c  adrp x9, #0x7083000
0x6383d70  ldrb w8, [x8, #0x810]
0x6383d74  ldrb w9, [x9, #0x2bc]
0x6383d78  cmp  w8, #0
0x6383d7c  csel w0, wzr, w9, eq
0x6383d80  ret
```

The reader is forced to return true:

```text
0x6383d68  c851009009680090 -> 20008052c0035fd6
           adrp/adrp       -> mov w0, #1 / ret
```

The registration side is at `0x6384294`, where the string
`ApplicationFrameRatePolicy` (`0x2d4e3c`) is paired with the byte at
`0x6dbb810` and callback `0x638397c`.

## 5. Existing Downstream 120 Patches

These are retained in `tools/patch_native_fps_cap_2741.py`:

```text
0x283122c  native-resolution scale selection -> 1.0
0x24203ec  TaskSchedulerTargetFps fallback   -> 120
0x22b2bec  scheduler constructor interval    -> 1/120
0x1e6ff5c  FRMFrameRateTarget initializer    -> 120
0x2f3cbe4  FRM getter                        -> 120
0x44577d8  FramerateCap property getter      -> 120
0x44c31e8  FramerateCap setter compare       -> 120
0x44c31f4  FramerateCap setter store         -> 120
```

The `FramerateCap` reflection registration is at `0x1ff78d4`; the getter and
setter trampolines are `0x41c2768` and `0x41c2770`.

## 6. Resulting Effective Flow

With all four gates open:

1. Luau sees `GameBasicSettingsFramerateCap == true` and renders the Maximum
   Framerate dropdown.
2. `FramerateCap` getter returns 120 and its setter stores 120.
3. `GetDefaultFramerateCap()` returns 120 instead of failing.
4. `ApplicationFrameRatePolicy` reads as enabled.
5. The startup setup block is no longer skipped, so it applies the 120 FPS
   target through the scheduler rather than leaving the 60 FPS fallback in
   force.

## 7. Build Artifact

The signed arm64 split containing these changes is:

```text
new_build/release/split_arm64_signed3.apk
```

Its embedded `lib/arm64-v8a/libroblox.so` SHA-256 is
`a7a147ec10ae888dd1443b811501c1455f1aaebc93ce8a9644e714fa6a1157ff`.

## 8. x86_64 Correspondence

The x86_64 feature byte is `0x732db78`. Its getter is:

```text
0x28941f3  mov al, byte ptr [rip + 0x4a9997f]
0x28941f9  ret
```

Patched to `mov al, 1 / ret / nop fill`. The native flag path selector at
`0x2370103` compares that byte and uses `cmove` to choose a fallback path.
The `cmove` at `0x2370118` is replaced with a NOP so the primary path is
always selected. The signed x86_64 split is
`new_build/release/split_x86_64_signed3.apk`.

The armeabi-v7a build keeps the original downstream 120 patches, but its
feature-gate callback was not directly addressable by the same string xref
pattern and remains on the unresolved cross-ABI list.

## 9. Stock Flag Dictionary

The 2.741 base APK embeds its flag cache in
`assets/android/shared_compression_dictionaries/*.dict`. Relevant stock
entries are:

```text
FFlagGameBasicSettingsFramerateCap5 = True
FFlagMoreFramerateOptions          = True
FFlagTaskSchedulerLimitTargetFpsTo2402 = True
FFlagPerformanceControlRespectUserFpsOverridden = True
DFFlagExposeFrameRateCapToPerfData = True
```

The Luau `MoreFramerateOptions` path and the `...FramerateCap5` FFlag are
therefore already true, which provides the 120/144/160/... choices. The
engine feature queried by the settings page is the native
`GameBasicSettingsFramerateCap` byte at `0x6c10b90`, which is not the same
as the Luau `...Cap5` FFlag and still starts false. That byte is the gate
that section 1 opens. The dictionary has no `ApplicationFrameRatePolicy`
entry, so that policy also starts false; section 4 opens it.

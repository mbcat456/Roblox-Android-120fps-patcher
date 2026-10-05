# Scheduler Default Interval And FRM Initializer Patch

This document records the second-generation native patch that addresses the
remaining 60 FPS behavior after the earlier getter/CVar patches were applied.
It is specific to Roblox Android `2.738.1397` build `3092`.

## Finding

`FUN_062c95dc` is the policy-driven path that eventually writes
`1000 / effective_fps` milliseconds into the task scheduler. The earlier
patches made that calculation return 120, but they only take effect when the
policy path is entered. The `TaskScheduler` object itself is constructed with
a hardcoded `1.0 / 60.0` second interval, and the policy path is conditional
on `ApplicationFrameRatePolicy` and `GameBasicSettingsFramerateCap`. If that
path is skipped during startup, the constructor value remains the effective
render scheduler interval.

The constructor field is therefore the authoritative fallback that still
explains a 60 FPS render loop when the display, Java refresh-rate input,
PowerKeeper vote, and cap getters all report 120.

## Evidence

### arm64-v8a

`FUN_0234f810` is the task scheduler constructor. Ghidra VA `0x0234f810`
maps to file offset `0x0224f810`.

```text
0224f8b8  mov  x8, #0x1111111111111111
0224f8c0  movk x8, #0x3f91, lsl #48      ; 1/60 second
0224f8c4  str  xzr, [x23, #0xf0]!
0224f8c8  stur x8, [x23, #-0x38]         ; object offset +0xb8
```

Patch:

```text
0x0224f8c0  28 f2 e7 f2 -> 28 f0 e7 f2
            0x3f91       -> 0x3f81
```

`0x3f81111111111111` is the IEEE-754 double for `1.0 / 120.0`.

### x86_64

`FUN_0243f372` maps to file offset `0x0233f372`.

```text
0233f433  movabs rax, 0x3f91111111111111
0233f43d  mov    qword ptr [r13 + 0xb8], rax
```

Patch:

```text
0x0233f433  48 b8 11 11 11 11 11 11 91 3f
          -> 48 b8 11 11 11 11 11 11 81 3f
```

### armeabi-v7a

`FUN_02a57840` maps to file offset `0x02a47840`.

```text
02a478f2  movw r0, #0x1111
02a478f6  movt r0, #0x3f91
02a478fa  mov.w r1, #0x11111111
02a478fe  strd r1, r0, [r2, #-0x28]
```

Patch:

```text
0x02a478f6  c3 f6 91 70 -> c3 f6 81 70
            0x3f91       -> 0x3f81
```

## FRM Target Initializer

`GraphicsOptimizationModeFRMFrameRateTarget` is initialized to `0x3c` on all
three ABIs. The arm64 store is in `_INIT_381` at file offset `0x01e06be0`:

```text
01e06be0  mov w8, #0x3c
01e06be4  adrp x9, #0x6a75000
01e06be8  add  x9, x9, #0x448
01e06bec  str  w8, [x9]
```

Patch:

```text
0x01e06be0  88 07 80 52 -> 08 0f 80 52
            0x3c        -> 0x78
```

This closes the direct-global-read path in `FUN_02fce4cc` even though the
renderer getter `FUN_02ed0d7c` was already forced to 120.

## Remaining Cross-ABI Note

The arm64 device path is fully patched. On armeabi-v7a the FRM getter
`FUN_0161c010` is already forced to 120, and on x86_64 the same global is read
inline in `FUN_032dec60`. The x86_64 initializer store has not yet been
located at machine-code level in this workspace; it remains documented in
`analysis/docs/12_60HZ_CAP_AUDIT.md` as `DAT_0748e5c0 = 0x3c`.

Control-flow traversal of `_INIT_378` (`FUN_01ef9498` in the x86_64 image)
shows no reachable immediate `mov ..., 0x3c` instruction in that constructor.
The decompiler assignment therefore comes from a data-table/helper
initialization pattern rather than a single patchable instruction, so the
x86_64 FRM initializer is intentionally documented as data-driven rather than
patched with an unverified immediate replacement.

## Verification Commands

The patch script is idempotent:

```powershell
$env:PYTHONPATH='tools\pylibs'
python.exe tools/patch_native_fps_cap.py apktool_out/lib/arm64-v8a/libroblox.so
python.exe tools/patch_native_fps_cap.py apktool_out/lib/armeabi-v7a/libroblox.so
python.exe tools/patch_native_fps_cap.py apktool_out/lib/x86_64/libroblox.so
```

Signed artifact:

```text
mod/signed_miui_scheduler4/Roblox_2.738.1397_120fps_miui_scheduler4-aligned-signed.apk
SHA-256 9D922D0CA357CC98C9F32B5C9176230AF080573C30E9AC9F5C28C996B0244F7A
```

The signed APK contains the patched `libroblox.so` files byte-for-byte:

```text
lib/arm64-v8a/libroblox.so   SHA-256 11D0862CCEEFFD9240AE5807B5D3FAE7D349BB511EDAF519B4DCACB43E3912DF
lib/armeabi-v7a/libroblox.so SHA-256 78CC533B74A76C175D478C42B0BC34A37B84A9ADBAC925EE661D6CE4FC53181D
lib/x86_64/libroblox.so      SHA-256 0EAF1C2120F4EA18798FED1DF854F69304D6E1C7227C53B2399D2B5958D1EF7B
```

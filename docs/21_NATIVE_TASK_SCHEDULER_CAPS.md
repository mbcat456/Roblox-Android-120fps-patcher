# Native Task-Scheduler 60 FPS Defaults

The display and MIUI layers can both be at 120 Hz while the engine still
presents at 60 because the native `TaskScheduler` initializes from a second,
independent refresh-rate getter.

## Arm64 Evidence

Ghidra function `FUN_024c82b8` in
`analysis/native/arm64-v8a/libroblox/libroblox.so_decompiled/libroblox.so_part_0028.c:31281`
reads `DAT_0736a418`, clamps the value to 240, and returns 60 when it is zero:

```text
iVar2 = DAT_0736a418;
if (0xef < iVar2) iVar2 = 0xf0;
iVar1 = 0x3c;
if (DAT_0736a418 != 0) iVar1 = iVar2;
return iVar1;
```

`FUN_024c81d4` uses that result as `1000 / fps` while building the scheduler
frame-time target table. Patching the earlier display-rate function did not
change this path because it calls `FUN_024c82b8` directly.

The ELF image base is `0x100000`, so Ghidra address `024c82b8` maps to file
offset `023c82b8`.

## Patch Sites

```text
arm64-v8a
  0x023c82e8
  1f010071880780520001891a -> 000f80521f2003d51f2003d5
  cmp w8,#0 / mov w8,#0x3c / csel w0,w8,w9,eq
  -> mov w0,#0x78 / nop / nop

x86_64
  0x024d3e77
  b83c0000000f45c1 -> b878000000909090
  mov eax,0x3c / cmovne eax,ecx -> mov eax,0x78 / nop / nop / nop

armeabi-v7a
  0x02b4f668
  002908bf3c20 -> 782000bf00bf
  cmp r1,#0 / it eq / moveq r0,#0x3c
  -> movs r0,#0x78 / nop / nop
```

The arm64 display-rate path and FrameRateManager cap patches remain
unchanged. See `mod/README.md` for the complete current patch inventory.

In addition to the zero-flag fallback above, the `TaskScheduler` constructor
`FUN_0234f810` stores its default interval directly as `1.0 / 60.0` seconds at
object offset `+0xb8`. The current mod changes that constructor value to
`1.0 / 120.0` on all three ABIs. See
[`13_SCHEDULER_DEFAULT_AND_FRM_INIT_PATCH.md`](13_SCHEDULER_DEFAULT_AND_FRM_INIT_PATCH.md)
and
[`22_NATIVE_FRAME_PACING_MAP.md`](22_NATIVE_FRAME_PACING_MAP.md).

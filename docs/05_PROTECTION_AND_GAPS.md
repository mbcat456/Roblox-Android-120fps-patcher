# Protection Assessment And Recovery Gaps

## What Was Found

- Android package-level protection is standard R8/minification plus Android
  Gradle plugin code shrinking. No full DEX virtualization or packer is
  present; the DEX classes are directly decodable by JADX.
- Native binaries are stripped and symbol-minimized but not packed or
  encrypted. ELF load segments, relocation tables, exception tables, and
  dynamic symbols are intact.
- The JNI export table is deliberately tiny and serves as the application's
  real ABI surface. Internal C++ symbols were stripped.
- String-index hits for Frida/Xposed/Magisk/integrity/debugger are SDK/runtime
  telemetry, Play Integrity/Play Protect strings, and Persona/Appdome threat
  telemetry rather than evidence of a custom Roblox code-protection layer.
  Persona ships `appdome-threatevents_release` with a named threat-event model
  (root, debugger, emulator, Magisk, Frida, KernelSU, Zygisk, hook framework,
  custom ROM, unlocked bootloader). Roblox also performs its own lightweight
  root/emulator checks. The indicators are catalogued in
  `analysis/dex/indicators/` and `analysis/maps/native_string_index.json`.
- The native engine contains direct enforcement strings such as
  `Roblox cannot be used in a rooted environment`, `DisconnectAndroidRootedKick`,
  and `AndroidEmulatorKick`, plus `IntegrityCheckedProcessor` and
  `GridSerializationIntegrityCheck` logic for server/client remote-event
  integrity. These are application policy controls, not code packing.
- No custom encrypted string blob or import-hash resolver was identified in
  the import table or relocation surface.

## Decoder Notes

`libroblox.so` is large enough that a naive full-auto Ghidra pass repeatedly
exhausted heap before exporting. The successful pipeline:

1. disable GCC exception analyzer during import;
2. let Ghidra auto-analysis discover 171,127 functions;
3. export functions, strings, symbols, and call graph incrementally;
4. decompile in fixed-size chunks so progress survives any single failure.

The decompiler occasionally reports `VarnodeContext: out of address spaces`
on the largest generated functions. Those cases remain address-accurate but
may need manual recovery.

## Remaining Gaps

- JADX emitted fallback output for 71 unique DEX methods; they are coroutine
  state machines and high-region SDK methods, classified in
  `26_JADX_FALLBACK_METHODS.md`.
- The bridge CSV has 618 unmatched JNI rows (206 declarations across three
  ABIs); the grouped inventory is in `23_UNMATCHED_JNI_INVENTORY.md`.
- Ghidra symbol export was capped at 10,000 symbols; dynamic symbols are
  separately complete from readelf inventories.
- Decompiled internal names are address-based until xref/string-based renaming
  is applied.
- No dynamic execution was performed, per the static-only constraint.
- The `6dff800d` and `42726577` APK signing block records have no recognized
  scheme; their bytes are retained and hashed for follow-up.

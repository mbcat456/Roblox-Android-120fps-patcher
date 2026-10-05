# Methodology And Verification

## Tools

- ZIP extraction and Android decode: PowerShell, apktool 3.0.3
- Java/Kotlin: JADX 1.5.6 in normal JSON/Java modes and fallback mode
- DEX/ARSC: androguard, pyelftools, custom Python parsers
- Native: GNU readelf/objdump, Ghidra 12.1.2 headless, custom Ghidra scripts
- Signing: cryptography X.509 and a custom APK signing-block parser
- Static-only policy: no device, emulator, or debugger was used

## Pipeline

1. Inventory and hash every APK member.
2. Decode `AndroidManifest.xml`, `resources.arsc`, XML, and META-INF metadata.
3. Decompile all DEX with JADX; emit JSON instruction trees and Java; rerun in
   fallback mode for 142 hard methods.
4. Independently parse all DEX class/method/field definitions with androguard
   and cross-check counts against JADX.
5. Build the JOBF obfuscation inverse map and pair every Java native
   declaration with `Java_*` ELF symbols in all three ABIs.
6. Inventory every ELF with readelf, then dump all sections, dynamic tags,
   symbols, relocations, and notes with pyelftools.
7. Run Ghidra auto-analysis on the engine with the GCC exception analyzer
   disabled, export function/string/symbol/call metadata, then stream
   decompilation in fixed-size chunks.
8. Parse Roblox model files (binary RBXM, compressed chunks, and legacy XML)
   into referents, instances, properties, and parent links.
9. Deduplicate and categorize strings across DEX and native surfaces.
10. Cross-reference every result into the `analysis/maps/` index.

## Verification

- APK v2/v3/v3.1 signature records are cryptographically verified.
- The 9,368 public resource IDs and 50,948 resolved values are re-derived
  independently from `resources.arsc`.
- The 139,646 DEX methods and 73,742 fields are enumerated independently by
  JADX and androguard.
- 539 `Java_*` exports appear in every ABI; 497 pair cleanly with Java
  declarations and 42 are orphaned.
- 171,127 arm64 function objects (167,526 in executable memory), 695,065
  call edges, 142,166 defined strings, 4,123 exports, and 542 imports are
  exported from the analyzed Ghidra database.
- Decompiled native output is chunked so each part can be validated
  independently.

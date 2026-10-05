# Roblox Android Client Reverse Engineering Index

Target:

```text
com.roblox.client_2.738.1397-3092_minAPI26(arm64-v8a,armeabi-v7a,x86_64)(nodpi)_apkmirror.com.apk
```

Version `2.738.1397`, build `3092`, minSdk `26`, targetSdk `35`, compiled against SDK `36`.

## Documentation

- `01_CONTAINER.md` - APK/zip inventory, certificates, signature schemes, extraction layout
- `02_DEX_ARCHITECTURE.md` - classes, methods, call graph, obfuscation maps, JNI declarations
- `03_NATIVE_ARCHITECTURE.md` - ELF layout, functions, symbols, strings, calls, decompilation
- `04_STARTUP_AND_PROTOCOLS.md` - application startup, feature flags, platform bridges
- `05_PROTECTION_AND_GAPS.md` - protection assessment and remaining recovery gaps
- `06_ASSETS_AND_RESOURCES.md` - assets, RBXM/Lua content, resources, network/configuration files
- `07_METHODOLOGY.md` - toolchain, pipeline, and verification evidence
- `08_NATIVE_RECOVERY.md` - conventions and workflow for reading/renaming the
  decompiled native code
- `09_COVERAGE.md` - live coverage matrix and residual gaps
- `10_FALSE_POSITIVE_AUDIT.md` - false-positive surface audit for the modified
  APK and the minimal packaging fix
- `11_DETECTION_AND_TELEMETRY_AUDIT.md` - Roblox client checks, outbound
  values, and remaining signature/telemetry risk
- `12_60HZ_CAP_AUDIT.md` - every 60 Hz / 60 FPS site in the stock Roblox APK
- `13_SYSTEM_60HZ_CAP_AUDIT.md` - unified Roblox + MIUI 60 Hz inventory,
  PowerKeeper vote chain, settings, properties, and escape path
- `13_SCHEDULER_DEFAULT_AND_FRM_INIT_PATCH.md` - scheduler constructor and
  FRM initializer patch evidence across the three native ABIs
- `20_MIUI_REFRESH_OVERRIDE.md` - observed MIUI 60 vote and the 120 override
- `21_NATIVE_TASK_SCHEDULER_CAPS.md` - native task scheduler cap details
- `22_NATIVE_FRAME_PACING_MAP.md` - display JNI, scheduler, policy, settings,
  and Frame Rate Manager function graph for the arm64 engine
- `23_UNMATCHED_JNI_INVENTORY.md` - unmatched DEX-native JNI declarations by
  class, native library, and resolution mechanism
- `24_UNRESOLVED_ARSC_COLORS.md` - classification of the ARSC resource IDs
  without static resolved values
- `25_ZERO_DATA_NATIVE_LABELS.md` - classification of Ghidra labels outside
  the executable native load segment
- `26_JADX_FALLBACK_METHODS.md` - corrected count and classification of the
  DEX methods that required JADX fallback output

## Primary Artifacts

| Surface | Location |
| --- | --- |
| APK raw | `com.roblox.client_2.738.1397-3092_minAPI26(arm64-v8a,armeabi-v7a,x86_64)(nodpi)_apkmirror.com.apk` |
| Unzipped APK | `apk_extracted/` |
| apktool decode | `apktool_out/` |
| JADX Java | `com.roblox.client_2.738.1397-3092_minAPI26(arm64-v8a,armeabi-v7a,x86_64)(nodpi)_apkmirror.com/sources/` |
| JADX JSON | `analysis/dex/jadx_json/sources/` |
| Ghidra native | `analysis/native/<abi>/<library>/` |
| Machine maps | `analysis/maps/` |
| Native projects | `analysis/native/projects/` |

## Map Inventory

- `maps/zip/apk_entries.csv` and `apk_entries_summary.json` - all 2,382 ZIP members
- `maps/manifest.json` - decoded manifest, components, permissions, SDK and version metadata
- `maps/android_component_map.csv` - all 73 exported/declared Android components
- `maps/android_component_source_map.csv` - those components joined to their
  recovered Java source paths
- `maps/meta_inf_surface.json` - META-INF, version files, Kotlin module metadata
- `maps/dependency_inventory.csv` - 87 identifiable SDK/artifact versions
- `maps/dex/dex_class_index.csv` - 21,457 classes including inner classes
- `maps/dex/dex_native_methods.csv` - every DEX `native` declaration
- `maps/dex/dex_load_library_sites.csv` - native library load sites
- `maps/dex/deobfuscation_index.csv` - original package/class to JADX rename mapping
- `maps/dex/hierarchy/` - independent androguard class/method/field hierarchy
  and bytecode-size dump
- `maps/dex/deobfuscated_hierarchy.csv` - hierarchy joined with recovered
  package/class names and source paths
- `maps/dex/dex_complexity_summary.json` and `top_*_by_*.csv` - method and
  class bytecode-size/complexity rankings
- `maps/dex/jobf_packages.csv`, `jobf_classes.csv`, `jobf_methods.csv`, `jobf_fields.csv`
- `maps/dex/kotlin_module_index.csv` - class to Kotlin module attribution
- `maps/dex/jadx_source_gaps.json` - 142 methods JADX could not restructure
- `maps/jni_bridge_arm64.json` and `.csv` - Java native declarations paired with ELF JNI symbols
- `maps/jni_bridge_arm64v8a.*`, `jni_bridge_armeabiv7a.*`, `jni_bridge_x86_64.*`
- `maps/jni_bridge_master.csv` - all three ABI bridge rows in one file
- `maps/jni_subsystem_counts.csv` - JNI surface grouped by Roblox subsystem
- `maps/native_library_map.json` - all 33 native libraries across the three ABIs
- `maps/native/libroblox_arm64_profile.json` - full arm64 function/section/call/string profile
- `maps/native/libroblox_x86_64_profile.json` - x86_64 function/size/chunk profile
- `maps/native/libroblox_x86_64_decompiled_calls.csv` - x86_64 decompiler call graph
- `maps/native/libroblox_armeabi-v7a_profile.json` - arm32 function/size/chunk profile
- `maps/native/libroblox_armeabi-v7a_decompiled_calls.csv` - arm32 decompiler call graph
- `maps/native/native_symbols.json` - dynamic symbol imports/exports for every library
- `maps/native_string_index.json` - categorized native string evidence
- `maps/native/native_*.csv` - crypto/source-path/protection/filesystem/network
  native string evidence
- `maps/native/native_build_identity.csv` - build ID and NDK identity for all
  33 native libraries
- `maps/native/elf/` - pyelftools JSON dump of all sections, segments, dynamic
  tags, symbols, relocations, and notes for all 33 ELF files
- `maps/native/all_elf_profiles.json` - one-line per-file ELF profile summary
- `maps/native/libroblox_arm64_full_function_index.csv` and
  `libroblox_arm64_semantic_index.csv` - per-function call/name indexes
- `maps/native/decompiled_reference_map.csv` and
  `decompiled_string_xrefs.csv` - function-to-symbol/string maps from the
  decompiled C
- `maps/network_urls.csv` and `maps/network_hosts.csv` - combined DEX/native
  network surface
- `maps/network_owner_map.csv` - host-to-owner classification
- `maps/assets/`, `maps/resources/` - complete asset/resource inventories and parsed surfaces
- `maps/arsc/` - full `resources.arsc` public-ID, locale, and resolved-value dump

## Reproducibility

The helper scripts are in `tools/`:

- `build_maps.py` - ZIP/manifest/native/DEX/JNI index generation
- `dex_map.py` - call graph, JOBF database, source inventory
- `jni_bridge_arm64.ps1` - exact JNI Java-to-ELF bridge
- `jobf_full_index.ps1` - package/class/method/field deobfuscation index
- `kotlin_module_index.ps1` - Kotlin module attribution
- `native_profile_arm64.ps1` - native profile generation
- `disasm_cfg_x64.py` - control-flow-aware x86_64 disassembly over a function
  entry point, used to avoid linear-sweep desynchronization
- `rbxm_parser.py` - Roblox binary model/property parser
- `apk_signature.py` - APK signing block and certificate verification
- `ghidra_scripts/` and `ghidra-run-*.bat` - headless Ghidra extraction/decompilation

All paths in this documentation set are relative to the workspace root
`<workspace>`.

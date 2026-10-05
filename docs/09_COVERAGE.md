# Coverage Matrix

## Container

- ZIP members: 2,382 / 2,382 indexed
- signing schemes: v2, v3, v3.1 verified
- manifest components: 73 / 73 mapped

## DEX / JVM

- class definitions: 26,615 / 26,615
- methods: 139,646 / 139,646
- fields: 73,742 / 73,742
- native declarations: 700 / 700
- JADX structured Java: 13,373 files
- fallback Java for hard methods: 14,102 files
- call graph: 124,902 methods / 223,305 edges

## Native

- ELF files: 33 / 33 fully parsed
- small helper libraries: 100% Ghidra function/string/decompile exports
- `libroblox.so` dynamic symbols: all three ABIs complete
- JNI bridge: 497 matched + 42 orphaned exports per ABI
- arm64 function database: 171,127 function objects / 695,065 call edges
- arm64 full decompilation: 171,110 / 171,127 emitted, 17 failed
- x86_64 full decompilation: 111,094 / 111,115 emitted, 21 failed
- armeabi-v7a full decompilation: 151,111 / 151,161 emitted, 50 failed

## Resources And Assets

- `resources.arsc`: 9,368 public IDs / 50,948 resolved values
- resource files: 1,505 / 1,505
- assets: 594 / 594
- Roblox models: 28 / 28 parsed

## Known Residual Gaps

- 42 orphan native JNI exports with no DEX declaration
- 71 unique DEX methods required JADX fallback output, classified in
  `26_JADX_FALLBACK_METHODS.md`
- 264 public resource-ID rows without a static value: 207 unique Material
  dynamic/theme colors, classified in `24_UNRESOLVED_ARSC_COLORS.md`
- 3,601 arm64 zero-data native labels outside executable memory, classified
  in `25_ZERO_DATA_NATIVE_LABELS.md`
- no dynamic execution, by constraint

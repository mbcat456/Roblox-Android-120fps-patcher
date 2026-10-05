# Assets, Resources, And Bundled Content

## Resources

`analysis/maps/resources/resources_summary.json`: 1,505 files, 7,530,949
bytes. XML resources are 6.7 MB, JSON/Lottie 316 KB, PNG/WebP roughly 494 KB,
plus billing protobuf data.

`analysis/maps/resources/xml_surface.json` contains the decoded XML for
backup/data-extraction rules, file providers, network security config, search,
splits, NFC filters, widgets, and billing phenotype registration.

The resource table itself is fully decoded with androguard into
`analysis/maps/arsc/`: 9,368 public resource IDs across two packages,
50,948 resolved configuration/value rows, 20 resource types, and 89 locales.
`public_resources.csv` and `resolved_values.csv` provide ID, type, name,
configuration, and value; the 207 unresolved public colors are classified in
`24_UNRESOLVED_ARSC_COLORS.md`.
configuration, and value for every resolved entry; raw string/color/dimen/
integer/bool tables are also preserved as XML.

## Assets

`analysis/maps/assets/assets_summary.json`: 594 files, 81,209,148 bytes.
Notable groups:

- Roblox model files: 25.4 MB `.rbxm` / 330 KB `.rbxl`
- shader packs: 18.7 MB `.pack`
- fonts: 13.4 MB TTF/OTF
- textures: 5.7 MB DDS + 5.2 MB `.tex` + 1.3 MB KTX
- CA bundle: 228 KB PEM
- JS/Lua/config and translations: 2.7 MB

The `rbxm_parser.py` decoded all 28 bundled `.rbxm`/`.rbxl` models into
`analysis/maps/assets/rbxm_parsed.json` (264 MB of parsed instances,
properties, referents, and parent links). The parser handles the Roblox
signature, META/SSTR/INST/PROP/PRNT/END chunks, LZ4/Zstd compression, the
interleaved integer/float encodings used by modern Roblox model files, and
the legacy XML `<roblox>` format used by `content/avatar/character.rbxm`.
The parsed corpus contains 34,905 `ModuleScript` instances plus the full
avatar, lighting, material, sound, and UI hierarchy.

`analysis/maps/assets/json_surface.json` indexes JSON configuration, locale,
Lottie, and Lua package metadata assets.

## META-INF And SDK Metadata

`analysis/maps/meta_inf_surface.json` captures version files, NOTICE/LICENSE
files, service registrations, and Kotlin module protobuf metadata. This is
used alongside `kotlin_module_index.csv` to attribute minified classes to
their source modules.

# Container And Signature

## ZIP Surface

From `analysis/maps/zip/apk_entries_summary.json`:

| Kind | Entries | Uncompressed bytes |
| --- | ---: | ---: |
| native library | 33 | 322,699,876 |
| asset | 594 | 81,209,148 |
| DEX | 3 | 22,249,060 |
| resource table | 1 | 4,068,236 |
| resource | 1,511 | 2,938,559 |
| root/META-INF | 239 | 157,919 |
| manifest | 1 | 56,240 |
| Total | 2,382 | 433,379,038 |

Compressed container size is 229,037,710 bytes. The three DEX files are
`classes.dex`, `classes2.dex`, and `classes3.dex`.

## Native Library Matrix

The APK carries `libroblox.so` plus ten supporting libraries for `arm64-v8a`,
`armeabi-v7a`, and `x86_64`.

| Library | arm64 bytes | arm32 bytes | x86_64 bytes |
| --- | ---: | ---: | ---: |
| `libroblox.so` | 109,193,800 | 75,576,380 | 118,732,400 |
| `libbacktrace-native.so` | 5,339,704 | 4,306,848 | 5,896,832 |
| `libzstd-jni-1.5.7-6.so` | 603,960 | 478,512 | 726,088 |
| `librenderscript-toolkit.so` | 394,112 | 247,064 | 384,952 |
| `libeigen_blas.so` | 251,784 | 146,356 | 249,184 |
| others | 79,976 | 38,076 | 69,184 |

## Signature And Certificates

See `analysis/signature/apk_signature.json`. The signing block contains:

- APK Signature Scheme v2, verified valid, SHA-256 digest
- APK Signature Scheme v3, verified valid, sdk 24-32
- APK Signature Scheme v3.1, verified valid, sdk 33+
- two additional signing-block records (`6dff800d`, `42726577`) without a
  public scheme decoder; their hashes are recorded

Certificates:

- legacy key: CN=Matt Critelli, OU=Mobile, O=Roblox Corporation, serial
  `539b32ae`, valid 2014-2039
- current key: CN=Roblox Corporation, OU=GameEngine, O=Roblox Corporation,
  serial `c3357f212f3f174a`, valid 2026-2126

`apktool.yml` records minSdk 26, targetSdk 35, versionCode 3092, versionName
`2.738.1397`, package ID 127, and the full do-not-compress list.

`analysis/maps/dependency_inventory.csv` identifies 87 versioned SDK artifacts,
including AndroidX Camera 1.5.2, AndroidX Core 1.17.0, Room/DataStore 1.1.7,
Credentials 1.6.0-beta03, AppCompat 1.7.1, and Activity 1.12.1.

## Extraction Layout

- `apk_extracted/` is a plain ZIP extraction.
- `apktool_out/` contains `smali/`, `smali_classes2/`, `smali_classes3/`,
  decoded resources, the decoded `AndroidManifest.xml`, and `apktool.yml`.
- JADX output is split into `sources/` and `resources/`.

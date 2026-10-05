# JADX Fallback Methods

The earlier coverage note said “142 methods required JADX fallback output”.
That number comes from `analysis/maps/dex/jadx_source_gaps.json`, which stores
both normal-mode and fallback-mode errors for the same methods.

## Corrected Count

```text
error records               142
unique method signatures     71
duplicate fallback records   71
```

All 71 methods have recoverable fallback output under
`analysis/dex/jadx_fallback/`.

## Failure Categories

| Failure | Unique methods |
| --- | ---: |
| region stack-size limit | 30 |
| `JadxRuntimeException` | 13 |
| method code generation | 10 |
| region count limit | 8 |
| type inference limit | 7 |
| `StackOverflowError` | 1 |
| types-fix failure | 1 |
| unsupported operation | 1 |

## Ownership

| Family | Unique methods |
| --- | ---: |
| Kotlin coroutines / minified SDK | 27 |
| other third-party code | 25 |
| Roblox-owned | 7 |
| Persona SDK | 5 |
| AppsFlyer | 3 |
| Google Play Services | 2 |
| Material Components | 1 |
| OkHttp | 1 |

Roblox-owned fallback methods are coroutine state machines in:

```text
LoggingProtocol
FlagCacheUtils
OtaPollingWorker
RecentlyPlayedWidgetProvider
RecentlyPlayedWidgetUpdateWorker
OSSearchSingleResultFetchWorker
widgets.a
```

This is a decompiler-limit issue, not missing DEX data. No additional
deobfuscation is required for those methods; their bytecode and fallback
source are already emitted.

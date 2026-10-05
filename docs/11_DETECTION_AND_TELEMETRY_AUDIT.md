# Detection And Telemetry Audit

This document maps every local check and outbound value found in
`com.roblox.client` 2.738.1397 that could let Roblox, Google, or an AV engine
recognize the modified APK. The scope includes enforcement controls,
telemetry, crash reporting, and packaging.

## Summary

The mod changes only these observable values:

```text
Display.getRefreshRate()      -> 120.0f
Native render-target scale    -> 1.0f
```

The current minimal build deliberately leaves
`Display.getSupportedRefreshRates()` unchanged. The native engine uses the
current refresh rate for the display cap; the supported-rate vector is used
for VRR detection and telemetry. Preserving it removes one telemetry
anomaly without changing the mod behavior.

The DPI handoff code is also stock. The native patch changes only the final
render-target halving decision, so Android UI density and `ScreenDpiScale`
telemetry stay normal.

No local APK self-hash, package-signature whitelist, or DEX checksum check
was found. The remaining signature risk comes from server-side attestation
and Google Play services, not from code inside the APK.

## Enforcement Surface

### APK signature and package identity

| Item | Evidence | Outcome |
| --- | --- | --- |
| APK Signature Scheme | signing block | Stock uses v2/v3/v3.1; mod uses valid v2/v3 |
| Signing certificate | signing block | Changed by requirement; no way to reuse stock key |
| Package name / version | manifest | Unchanged |
| `classes.dex`, `classes3.dex` | zip hashes | Unchanged |
| `resources.arsc` | zip hash | Unchanged |
| `libroblox.so` all ABIs | zip hashes | Unchanged |

No Java or native code was found that reads the APK signature and compares it
with a Roblox certificate hash. Signature checks found in DEX are Play Store
package validation used by billing code.

### Play Integrity / account device integrity

`p583yl.C13503i` is a Play Integrity token provider. It is initialized from:

- `com/roblox/client/startup/NativeHelper.java`
- `p212jk/C6711k0.java`

The MessageBus methods are:

```text
getIntegrityToken
deviceIntegrityAvailable
```

Native `AccountProtocolCore` registers:

```text
GetDeviceIntegrityToken
GetDeviceIntegrityTokenYield
DeviceIntegrityAvailable
GetDeviceAccessToken
GetCredentialsHeaders
```

The token provider is prepared at startup. A token is only returned when the
native account protocol asks for `getIntegrityToken` over the MessageBus.
Static analysis cannot prove whether the server requests this on every login
or only for specific account actions.

Impact:

- Play Integrity can fail because the signing certificate differs from the
  Play Store copy.
- This is a server/GMS control. Patching the local token request would only
  break account flows and would itself be an integrity bypass.

### Persona / Appdome threat events

`appdome-threatevents_release` is part of the Persona identity-verification
SDK. Its event names include:

```text
RootedDevice
DebuggerThreatDetected
AppIsDebuggable
AppIntegrityError
EmulatorFound
GoogleEmulatorDetected
MagiskManagerDetected
FridaDetected
FridaCustomDetected
DetectUnlockedBootloader
KernelSUDetected
HookFrameworkDetected
OsRemountDetected
FridaAttachDetected
FridaSpawnDetected
ZygiskDetected
DetectCustomRom
```

These events are uploaded during a Persona inquiry, not during ordinary
gameplay. The mod does not alter this code and does not need to.

### Root, emulator, and debugger policy

Native strings include:

```text
Roblox cannot be used in a rooted environment. Please run Roblox on a supported device.
DisconnectAndroidRootedKick
AndroidRootedKick
DisconnectAndroidEmulatorKick
AndroidEmulatorKick
```

These checks inspect the device and environment, not the APK. The stock and
modified APKs behave identically here. They were deliberately not patched.

### In-experience remote-event integrity

`IntegrityCheckedProcessor` and `GridSerializationIntegrityCheck` validate
client/server remote events in the game engine. The mod changes no game
script, input, replication, or physics code, so these checks see the same
event stream as stock.

### Anti-cheat product

No Hyperion or Byfron client was identified in this Android build. The
protection assessment in `05_PROTECTION_AND_GAPS.md` found standard R8,
stripped native code, and policy checks rather than a packed anti-cheat
module.

## Refresh Rate Surface

Java path:

```text
fi/SurfaceHolderCallbackC5291r0.java
  m25169h() -> nl.a.k(display) -> nativePassSupportedRefreshRates
  m25173n() -> nl.a.a(display) -> nativePassCurrentDisplayRefreshRate
```

Native storage and cap path:

```text
nativePassCurrentDisplayRefreshRate
  DAT_06e35a80 = 120.0
FUN_024c8448 / thunk_FUN_024c8448
  returns DAT_06e35a80 as primary display rate
FUN_024c81d4
  FUN_062c9950(display-cap-config, 120)
FUN_062c95dc
  resolved interval = max(requested_ms, 1000 / display_cap)
```

Outbound/observable fields:

| Field | Owner | Mod impact |
| --- | --- | --- |
| `MaxDisplayRefreshRateHz` | PerformanceControl telemetry | Becomes 120 |
| `max_display_refresh_rate_hz` | PerformanceControl perturbation telemetry | Becomes 120 |
| `raw_display_refresh_rate_hz` | PerformanceControl perturbation telemetry | Renderer raw VSync, may remain device rate |
| `RenderVSyncRawDisplayRefreshRateHz` | Rendering telemetry counter | Renderer measured value |
| `PerformanceControlDisplaySupportedRefreshRates` | PerformanceControl telemetry | Preserved stock in current build |

`nativePassCurrentDisplayRefreshRate` only stores the value and logs
`PerformanceControlDisplayRefreshRate`. The telemetry fields above are
registered in the `PerformanceControlV2`/`PerformanceControlV3` providers.

Current mitigation:

- Preserve the real supported-rate vector.
- Keep native libraries untouched.
- On a 60 Hz device, the only remaining refresh mismatch is the forced
  primary/max rate versus renderer raw VSync. That is telemetry, not a local
  kick condition.

## DPI And Resolution Surface

The Java `PlatformParams.dpiScale` handoffs are stock. The native patch is:

```text
FUN_028ec4e4 render-target selection
  arm64-v8a      1 byte  at 0x027ec695
  armeabi-v7a    1 byte  at 0x02e49faa
  x86_64         38 bytes at 0x0295b4e3
```

Outbound/observable fields:

| Field | Path | Mod impact |
| --- | --- | --- |
| `ScreenDpiScale` | engine info dump | Stock |
| `renderViewDpiScale` | `RealtimeMediaTelemetry::emitPeriodicStats` | Stock |
| `videoDpiScale` | `RealtimeMediaTelemetry::emitPeriodicStats` | Stock |
| `dpiScale` in Stratus `setResolution` | Stratus control message | Stock |
| Render target width/height | renderer and realtime media telemetry | Becomes full surface size |

The density helper `nl/a.e(Context)F` is intentionally left stock. It is used
for touch/viewport work, while only renderer handoff values are changed.

The render-target dimensions increase. There is no local resolution policy
check. Server-side resolution negotiation exists only in the
Stratus/realtime-media subsystem, and its `dpiScale` field remains stock.

## Device And Build Identity

`DeviceParams` supplies these fields to native code:

```text
appBuildVariant
appVersion
country
cpu64Bit
deviceName
deviceSku
deviceTotalMemoryMB
displayPhysicalHeightPixels
displayPhysicalWidthPixels
displayResolution
isChrome
isLowRamDevice
largeMemoryClass
lowMemoryKillerBackgroundAppThreshold
lowMemoryKillerForegroundAppThreshold
manufacturer
memoryClass
networkType
osVersion
socModel
testDeviceName
```

None are modified by this mod. They are available to performance and session
telemetry and can be used as baseline context if a server-side anomaly rule
compares forced refresh/render scale with device capabilities.

## Crash And Backtrace Surface

Backtrace attributes include:

```text
screen.width
screen.height
screen.dpi
```

These use Android `DisplayMetrics` directly and are not changed by the mod.

## Packaging And AV Surface

Already minimized:

- `classes2.dex` is byte-patched, not reassembled.
- Every other ZIP entry is preserved.
- v1 JAR signature is absent.
- v2/v3 signatures are valid.
- Signing certificate uses a neutral subject.
- `libroblox.so` and all other native libraries are identical to stock.

Cannot be reproduced locally:

- Google Play source stamp.
- The stock signing certificate.

See `10_FALSE_POSITIVE_AUDIT.md` for measurements.

## Values Not Affected

The following identity and telemetry values remain stock:

```text
Package name, versionCode, versionName
Android SDK version and build variant
Device model, manufacturer, SOC, SKU, network type
Physical display size and DisplayMetrics density
Supported refresh-rate vector
Native library hashes
resources.arsc, classes.dex, classes3.dex
```

## Patch Decisions

Patched:

1. `nl/a.a(Display)F` returns `120.0f` to force the engine display cap.
2. The native render-target selection is forced to `1.0f` in all ABIs.
3. Packaging is minimal and v2/v3-only with a neutral certificate.

Not patched:

1. `nl/a.k(Display)[F` remains stock.
2. Root/emulator/debugger/Appdome checks remain stock.
3. Play Integrity and account integrity remain stock.
4. Native `libroblox.so` remains stock.
5. Server-side attestation and anomaly rules are not touched.

## Residual Risk

Static analysis cannot rule out a future or server-side rule that combines
forced 120 Hz with a 60 Hz raw VSync reading. No local kick condition uses
that combination today.

Play Integrity can identify a modified APK whenever the server requests a
token. The local Play Integrity SDK is prepared at startup, so an
unauthenticated or authenticated integrity check could report a different
certificate. Bypassing this is not part of this modification.

## Verification

```text
final APK:
  mod/Roblox_2.738.1397_120fps_native_res_ui_fixed.minimal.apk
  SHA-256 D65E07CBE24229A50B62143E13CB73E83D7022A61F15F95C5445C3A4B0B4E571

signature: v2 true, v3 true, v1 false
alignment: 4-byte verification successful
manifest: identical SHA-256 to stock
classes.dex/classes3.dex/resources.arsc: identical to stock
libroblox.so all ABIs: 1/1/38 intentional bytes changed
```

Decoded final behavior:

```text
nl/a.a(Display)                  returns 120.0f
nl/a.k(Display)                  returns Display.getSupportedRefreshRates()
PlatformParams.dpiScale handoffs stock
Native render-target scale       1.0f
```

## Still Unverified At Runtime

The static pass cannot prove a server-side no-ban guarantee. Required live
checks:

1. Launch the final APK on both a 60 Hz and a 120 Hz device.
2. Observe whether `getIntegrityToken` is requested at login or only for a
   protected account action.
3. Capture the Roblox telemetry events listed above and compare
   `MaxDisplayRefreshRateHz`, `raw_display_refresh_rate_hz`, and the
   supported-rate vector.
4. Exercise voice/video or Stratus long enough to see whether
   `renderViewDpiScale` and `dpiScale` remain stock as intended.

No device or emulator is currently available in this workspace.

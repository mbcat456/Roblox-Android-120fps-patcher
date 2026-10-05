# False Positive Audit

This audit covers every plausible way the modified APK could be classified
as suspicious by an antivirus product, Play Protect, or Roblox itself.

## Conclusion

No Roblox-side package signature or APK self-integrity check was found. The
highest risk of a false positive came from how the first build was packaged:
it rebuilt most of the resource table, rewrote most of `classes2.dex`, added
an unnecessary JAR signature, and carried a self-identifying signing
certificate. The minimal build removes those signals.

The remaining items that cannot be patched are the unavoidable signature
certificate change and the removed Google Play source stamp. Neither should
make the APK look like malware, but a server-side Play Integrity policy or a
heuristic engine that distrusts all modified copies of popular apps can still
say "unknown" or "modified."

## Deliverable

```text
mod/Roblox_2.738.1397_120fps_native_res_ui_fixed.minimal.apk
SHA-256 D65E07CBE24229A50B62143E13CB73E83D7022A61F15F95C5445C3A4B0B4E571
```

## Findings

### 1. Broad repack fingerprint

The first `ui_fixed` build decoded and rebuilt the whole APK with Apktool.
Compared with the stock `classes2.dex`:

- 5,652,263 of 6,166,076 bytes differed.
- `resources.arsc` shrank from 4,068,236 to 4,018,884 bytes.
- Hundreds of XML and resource entries changed compressed bytes even though
  their logical content was unchanged.
- `classes.dex` and `classes3.dex` also changed size.

That pattern is the classic signal used by repacker and malware heuristics:
the file looks like a newly assembled binary rather than a minimal patch.

Patch:

- `tools/patch_dex_minimal.py` parses the stock DEX, appends one new
  `code_item`, and repoints only `nl/a.a`.
- `tools/build_minimal_native_apk.py` replaces only `classes2.dex` and the
  three patched `libroblox.so` entries in place, padding each compressed
  slot to its original size.
- Every other ZIP entry, timestamp, compression mode, and CRC is preserved.

Result:

```text
stock classes2.dex       6,166,076 bytes
minimal classes2.dex     6,166,098 bytes
in-place changed bytes   31
appended code bytes      22

stock arm64 libroblox.so diff        1 byte
stock armeabi-v7a libroblox.so diff 1 byte
stock x86_64 libroblox.so diff      38 bytes
```

The old build differed in 5.65 million DEX bytes and rebuilt hundreds of
resource entries. The minimal build changes 53 DEX bytes plus 40 native
bytes total.

### 2. Extra JAR signature

The stock APK uses APK Signature Scheme v2, v3, and v3.1 and has no v1 JAR
signature. The broad `ui_fixed` build added:

```text
META-INF/MANIFEST.MF
META-INF/MODKEY.RSA
META-INF/MODKEY.SF
```

Patch:

- The final APK is signed with v2 and v3 only.
- `tools/SignMinimalApk.java` explicitly disables v1 and v4.
- Verification reports `v1=false v2=true v3=true`.

### 3. Self-identifying signing certificate

The original signing certificate has this subject:

```text
CN=Roblox Mod,OU=Rev,O=Local,L=Home,ST=Local,C=IT
```

The subject does not change cryptographic verification, but it is an
unnecessary human-readable marker in the signing block.

Patch:

- `mod/keys/mod_release_neutral.jks` contains a fresh RSA key with the
  subject `CN=Local Build, OU=Development, O=Rev`.
- The final APK is signed with that neutral certificate.
- The old key remains in `mod/keys/mod_release.jks` for anyone who already
  installed the first build.

### 4. Removed Google Play source stamp

Stock carries a source stamp block and the entry `stamp-cert-sha256`.
Resigning necessarily removes the stamp because it is signed by Google and
is not reproducible locally.

Impact:

- Local Android installation does not require a source stamp.
- v2/v3 verification does not require a source stamp.
- Play distribution or a strict server policy may classify the APK as
  "unknown source" or "modified." This is an attestation result, not a
  malware classification.

There is no local patch for this item without Google's stamping key.

## Roblox Client Checks

### No package signature check

Every DEX usage of package signatures was traced:

- `ge/C5737w.java` and `sb/C10615r.java` validate the Google Play Store
  package, not the Roblox package.
- AppsFlyer's `validate-android-signature` endpoint belongs to SDK service
  configuration, not a runtime Roblox package check.
- No expected Roblox certificate hash was found in Java or native code.

### Play Integrity and Appdome

`appdome-threatevents_release` is used by the Persona identity-verification
SDK. Separately, `p583yl.C13503i` is a Roblox account device-integrity
provider prepared during normal startup. Native `AccountProtocolCore` can
request `getIntegrityToken` over the MessageBus. The mod does not patch that
path; see `11_DETECTION_AND_TELEMETRY_AUDIT.md`.

### Device attestation is a debug path

`NativeMetaInterface.getDeviceAttestationToken` resolves in native code to a
Maquettes debug message and returns without producing a token.

### RBXM signature checks are data-file checks

The many native "signature" strings belong to Roblox RBXM/data-model file
verification. They are not APK self-integrity checks.

### Native code has three intentional patches

`classes.dex`, `classes3.dex`, and `resources.arsc` are identical to stock.
The final APK intentionally changes only the documented render-target
selection instruction in each ABI:

```text
arm64-v8a      1 byte  at 0x027ec695
armeabi-v7a    1 byte  at 0x02e49faa
x86_64         38 bytes at 0x0295b4e3
```

No self-hash or ELF-integrity check of these libraries was found in Java or
native code.

## Remaining False-Positive Vectors

These are present but cannot be removed without defeating a security control:

1. Play Integrity can fail for any app whose signing certificate differs
   from the Play Store copy. Roblox's account device-integrity provider is
   prepared at startup, so this is the strongest remaining signature-bound
   check.
2. Roblox's rooted-device, emulator, Frida, Magisk, Zygisk, and custom-ROM
   checks can flag a device. The mod does not add or trigger these, and the
   stock client behaves identically. These checks were deliberately left
   untouched.
3. A server with an account-level integrity policy can reject any modified
   build. The local provider is initialized at startup, and a token is
   requested only when the account protocol asks for it. Static analysis
   cannot prove the request cadence without dynamic testing.
4. Reporting 120 Hz on a 60 Hz panel changes the locally observed primary
   display rate. The supported-rate vector is preserved, but telemetry
   includes `MaxDisplayRefreshRateHz` and a renderer raw VSync field. This
   is an analytics anomaly surface, not a found local kick condition.

## Scanner Check

The local Windows Defender installation reports that the product/feature is
disabled, so `MpCmdRun` cannot perform a custom scan. The final and stock
hashes were also searched online and had no prior public verdicts.

For an external multi-engine check, upload the final SHA-256 to a scanner
service that accepts APKs. No code change can pre-answer every third-party
heuristic; the minimal packaging here is the reduction that is under local
control.

## Verification

```text
APK signature           v2 verified, v3 verified, v1 absent
Zip alignment           4-byte verification successful
Manifest SHA-256        identical to stock
classes.dex/classes3    identical to stock
resources.arsc          identical to stock
libroblox.so all ABIs   1/1/38 intentional bytes changed
```

Decoded final methods:

```text
nl/a.a(Display)                       returns 120.0f
nl/a.k(Display)                       returns stock supported-rate list
all PlatformParams.dpiScale handoffs  stock
arm64/armv7/x86 render-scale select   forced to 1.0f
```

The DPI handoff methods remain stock, so `ScreenDpiScale` telemetry and
Stratus resolution negotiation see the normal density. Only the final native
render-target selection is changed.

## Rebuild Commands

```powershell
python tools/patch_dex_minimal.py stock.apk old_mod.apk classes2.ui_fixed.minimal.dex
python tools/build_minimal_native_apk.py stock.apk ui_fixed_reference.apk `
  classes2.ui_fixed.minimal.dex unsigned.apk

javac -cp apksig.jar -d build tools/SignMinimalApk.java
java -cp "apksig.jar;build" SignMinimalApk unsigned.apk signed.apk `
  mod/keys/mod_release_neutral.jks modpass123 modkey modpass123

java -cp "apksig.jar;build" VerifyMinimalApk signed.apk
zipalign -c -v 4 signed.apk
```

Do not run the writing form of `zipalign` after signing. The unsigned APK is
already aligned because the patched DEX slot keeps its original compressed
size, and the bundled zipalign strips the v2/v3 signing block when it rewrites
the file.

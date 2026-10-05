# Roblox Android 120fps patcher

An unofficial, display-only patch for the Roblox Android client that opens the
official Maximum Framerate settings path and keeps every render/display
refresh boundary at 120 Hz.

This project does not touch authentication, anti-cheat, protection code, or
gameplay simulation. The native changes are limited to frame pacing, the
framebuffer resolution selector, and the engine feature gates described in
`docs/26_2741_OFFICIAL_FPS_PATH.md`.

## Warnings

- This is not affiliated with or endorsed by Roblox.
- Modified clients can violate Roblox's Terms of Use and may be detected by
  Roblox's own client/server integrity checks.
- Build and install only from an APK that you own or are authorized to modify.
- Do not use this as a basis for anti-cheat detection or evasion.

## Current release

Version `2.741.1061`, versionCode `3212`.

- `release/Roblox_2.741.1061_120fps_mod.apkm` - APKMirror Installer bundle
- `release/Roblox_2.741.1061_120fps_mod.apks` - SAI bundle
- `release/Roblox_2.741.1061_120fps_universal.apk` - single universal install
- `release/split_config.*.apk` - raw split pieces for advanced manual installs

The `.apkm` and `.apks` files are large and are intended for the GitHub
Release attachment rather than the Git repository.

## Install on the phone

Install the universal APK directly, or use `APKMirror Installer` / `SAI` to
open the `.apkm` / `.apks` bundle. The raw `split_config.*.apk` files are only
needed for advanced split installation.

## Patch a new Roblox version

For versionCode `3212`, the exact audited patch table is applied:

```powershell
python.exe patcher\patch_roblox.py input.apkm `
  --output patched_output `
  --apksigner C:\path\to\build-tools\36.0.0\apksigner.bat
```

For an unknown future version, the wrapper automatically:

1. Locates `GameBasicSettingsFramerateCap` and
   `ApplicationFrameRatePolicy` in the new `libroblox.so`.
2. Patches those native gates with instruction-level patterns.
3. Rewrites the `(Landroid/view/Display;)F` DEX helper to return `120.0f`.
4. Rebuilds and signs the base and split APKs.
5. Emits an `.apks` bundle.

Ambiguous native constant matches are deliberately not changed. The script
prints every candidate so they can be audited against
`docs/22_NATIVE_FRAME_PACING_MAP.md` and added to the version table if needed.

Run the verification script after patching:

```powershell
python.exe patcher\verify_2741_patches.py `
  patched_output\split_config.arm64_v8a_mod_signed.apk `
  patched_output\split_config.x86_64_mod_signed.apk
```

## What is patched

- `cl/a.a(Display)F` returns `120.0f` to
  `nativePassCurrentDisplayRefreshRate`.
- `GameBasicSettingsFramerateCap` returns `true`.
- `ApplicationFrameRatePolicy` returns `true`.
- `GetDefaultFramerateCap()` returns `120`.
- Native setup no longer skips the frame-rate policy block.
- TaskScheduler fallback, constructor interval, FRM target, and
  `FramerateCap` property return/store 120.
- High-DPI render target keeps the full surface instead of halving it.
- MIUI Joyose receives a 120 Hz override vote.

See `docs/` for the full reverse-engineering map.

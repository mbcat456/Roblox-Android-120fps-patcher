# 60 Hz / 60 FPS Hardcode Audit - Roblox APK + Stock MIUI Stack

This is the unified, exhaustive static audit. It combines:

- the Roblox APK inventory in
  [`12_60HZ_CAP_AUDIT.md`](12_60HZ_CAP_AUDIT.md)
- the MIUI PowerKeeper / Joyose / MISettings findings from the decompiled ROM
  packages under `mod/`
- the live-screen evidence in
  [`20_MIUI_REFRESH_OVERRIDE.md`](20_MIUI_REFRESH_OVERRIDE.md)

## Scope

Roblox artifact:

```text
com.roblox.client_2.738.1397-3092_minAPI26(arm64-v8a,armeabi-v7a,x86_64)(nodpi)_apkmirror.com.apk
```

Roblox surfaces examined:

- Java/Kotlin DEX (`analysis/dex/jadx_src/sources`)
- native engine on all three ABIs (`analysis/native/`)
- RBXM and Luau frontend (`apk_extracted/assets`,
  `analysis/recovery/modulescripts`)
- APK resources and bundled flag cache (`apktool_clean`, `apk_extracted`)

MIUI artifacts:

- `mod/PowerKeeper.apk` -> `mod/powerkeeper_jadx/sources`
- `mod/Joyose.apk` -> `mod/joyose_jadx/sources`
- `mod/MISettings.apk` -> `mod/misettings_jadx/sources`
- Joyose bundled JSON assets, enumerated by
  [`tools/audit_joyose_cloud.py`](../../tools/audit_joyose_cloud.py)
- `mod/device_window.xml` (captured MIUI refresh-rate settings screen)

This is a static code/data audit. It does not claim to have traced a live
device, and the runtime MIUI cloud/ODM JSON and live Settings values were not
available in this session.

## TL;DR

The Roblox APK itself has native renderer/scheduler default-60 sites, but the
stock Java surface does not request 60. On the inspected stock MIUI build the
actual per-package 60 Hz vote comes from PowerKeeper:

```text
Joyose assets/top_game_list.json contains com.roblox.client
    -> Joyose broadcasts intent.action.TOP_GAME_LIST
    -> PowerKeeper stores the list in SimpleSettings key_top_names
    -> PowerKeeper materializes mDefaultGameApp
    -> foreground dispatch calls setScreenEffect("com.roblox.client", 60, 254)
    -> Secure setting miui_refresh_rate is written to 60
```

The escape is a higher-priority explicit vote:

```text
com.xiaomi.joyose.OVERRIDE_GAME_FRESHRATE
    override_pkg_name=com.roblox.client
    override_freshrate=120
    -> PowerKeeper message 12 stores com.roblox.client=120 in mPrivGames
    -> mPrivGames is checked before mDefaultGameApp
    -> setScreenEffect("com.roblox.client", 120, 254)
```

## 1. Roblox APK - Complete 60 Inventory

Every genuine 60 site found in the shipped APK:

| # | Surface | Site | Stock behavior |
| --- | --- | --- | --- |
| 1 | Native scheduler, all ABIs | `TaskSchedulerTargetFps` initialized to 0 | getter treats 0 as 60 (`0x3c`); interval is `1000 / target_fps` |
| 2 | Native display setup, all ABIs | rate normalization | any reported rate below 61 is raised to 60; 120 remains 120 |
| 3 | Native renderer, all ABIs | `GraphicsOptimizationModeFRMFrameRateTarget = 60` | copied into `gfx/frm/frameRateCap` |
| 4 | Native physics, all ABIs | `PhysicsStepLimitMaxFPS = 60` | `1.0 / 60.0` becomes the minimum physics step |
| 5 | Native reflection enum | `PhysicsSimulationRate.Fixed60Hz` | 60 Hz is an available simulation choice |
| 6 | Frontend Luau | `ReactSchedulerDesiredFrameRate = 60` | default desired rate for the UniversalApp React scheduler |
| 7 | Frontend Luau | `ScrollingPerfTrackerTargetFPS = 60` | telemetry/performance target |
| 8 | Frontend Luau settings | `FramerateCaps` lists start with 60 | 60 is the first/default in-game choice |
| 9 | Native settings metadata | `FramerateCap` property | storage field registered; the numeric 60 default comes from item 3, not a visible assignment |

The Java layer is not a cap source:

- `nl/C8594a.java` only calls `Display.getRefreshRate()` and
  `Display.getSupportedRefreshRates()`.
- `fi/SurfaceHolderCallbackC5291r0.java` passes the real display rate and
  supported-rate array into `NativeGLInterface`.
- stock `MainGameActivity` / `ActivityNativeMain` contain no
  `preferredDisplayModeId`, `Surface.setFrameRate`, display-mode selection, or
  refresh override. Those calls exist only in the local `mod/` builds.
- Android resources contain no refresh-rate/VSync/FPS cap.
- `ParticleEmitter.FlipbookFramerate` RBXM values are `1.0`, not 60.
- `GameSettingsConstants` `DeviceFrameInput = 60` is an audio frame count.

ABI-level function names, file offsets, machine-code verification, false
positives, and VSync/feature-flag details are in
[`12_60HZ_CAP_AUDIT.md`](12_60HZ_CAP_AUDIT.md). This report does not repeat
the three-ABI table here.

## 2. MIUI End-To-End 60 Vote

This is the path that matters for the reported device.

### 2.1 Joyose ships Roblox in its top game list

`mod/Joyose.apk` contains `assets/top_game_list.json`:

```json
{
  "top_game_list": [
    "...",
    "com.roblox.client",
    "..."
  ]
}
```

Joyose loads it in
`mod/joyose_jadx/sources/p047f0/C0789e.java`:

- `m3965m` reads `top_game_list.json` at lines 164-175.
- `m3968p` converts the list to comma-separated chunks and broadcasts
  `intent.action.TOP_GAME_LIST` with extras `gameList` and `isAppend` at lines
  199-220.
- `C0788d0.m3933w6` sends the same `TOP_GAME_LIST` append broadcast at lines
  3150-3154.

### 2.2 Joyose exposes the list to MIUI Settings

`mod/joyose_jadx/sources/com/xiaomi/joyose/smartop/provider/GameInfoProvider.java`:

- `call()` dispatches method `getGameList` to `m1765b` at line 191.
- `m1765b` serializes the package list into a JSON `gameList` array at lines
  168-185.

MISettings reads that provider:

- `mod/misettings_jadx/sources/p009a8/C0057h.java`
  - `m182f` queries
    `content://com.xiaomi.Joyose.provider/game_list` with method
    `getGameList` at lines 274-294.
  - constructor registers the URI at line 330.
- `HighRefreshOptionsFragment.m3499y` appends the returned games under the
  `follow_apps_settings` header at lines 197-208.
- `mod/device_window.xml` confirms the result: Roblox appears with summary
  "In base alle impostazioni dell'app".

This settings screen is presentational. It explains why Roblox is listed as
"follow app settings"; the enforcement happens in PowerKeeper.

### 2.3 PowerKeeper receives and stores the list

`mod/powerkeeper_jadx/sources/com/miui/powerkeeper/statemachine/DisplayFrameSetting.java`:

- receiver handles `intent.action.TOP_GAME_LIST` at lines 713-718 and calls
  `handleTopGameList` (lines 1508-1517).
- message 1 writes the full list to `SimpleSettings.Misc` key
  `key_top_names`, clears `mDefaultGameApp`, and calls
  `fillDefaultGameApp` at lines 5572-5579.
- message 2 appends and re-fills at lines 5581-5590.
- `fillDefaultGameApp` adds installed packages to `mDefaultGameApp` at lines
  1124-1140.
- initialization and package-added paths repeat this at lines 2520-2524,
  2651-2655, 2730-2733, 2785, 3607-3615.

### 2.4 PowerKeeper emits the literal 60 vote

Foreground dispatch in `onForegroundChanged`:

```text
6381  Integer num2 = this.mPrivGames.get(pkg);
6382  if (num2 != null) {
6383      // optional smart-game override
6384      ...
6385      setScreenEffect(pkg, num2.intValue(), 254);
6386      return;
6387  }
...
6393  if (this.mDefaultGameApp.contains(pkg)) {
6394      setScreenEffect(pkg, 60, 254);
6395      return;
6396  }
...
6456  if (this.mIsEnterGameScene) {
6457      setScreenEffect(pkg, 60, 254);
6458      return;
6459  }
```

This is a literal integer 60 passed as the FPS argument, with game cookie 254.
The public dump labels the state directly at lines 5325-5326:

```text
fpsconfig mDefaultGameApp(60):{com.roblox.client, ...}
```

The main `setScreenEffect` then:

- clamps requested values above the user-selected rate at lines 6645-6650;
- writes Secure setting `miui_refresh_rate` at lines 6660-6661 when
  `FPS_SWITCH_DEFAULT` is true;
- calls `DisplayFeatureManager.setScreenEffect(24, fps, cookie)` at line 6663
  or 6672.

`FPS_SWITCH_DEFAULT` is read from `ro.vendor.fps.switch.default` at line 619.

## 3. PowerKeeper Literal 60 Inventory

Primary file:
`mod/powerkeeper_jadx/sources/com/miui/powerkeeper/statemachine/DisplayFrameSetting.java`.

### 3.1 Direct display-rate votes

These sites pass literal 60 into `setScreenEffect` or an equivalent display
path:

| Lines | Trigger | Cookie | Meaning |
| --- | --- | --- | --- |
| 785 | `SET_ACTIVITY_FPS` enters an activity | message 15 | conditional activity-entry 60 |
| 5657 | foreground package is in the camera-activity list | 252 | camera-entry 60 |
| 6222 | package is in `input_list60` and input state is active | 249 | input-list 60 |
| 6235 | package is in `audio_list60` and audio-record state is active | 249 | audio-list 60 |
| 6248 | blacklist low-FPS activity is not scrolling | 249 | low-FPS activity fallback |
| 6254 | foreground activity is in VR blacklist | 249 | VR-activity 60 |
| 6273 | foreground package is in extreme-video list | 249 | extreme-video 60 |
| 6283 | blacklist applet activity, fullscreen, applets switch on | 249 | applet-scene 60 |
| 6368 | package is in `mVideoApps` | 248 | video 60 |
| 6394 | package is in `mDefaultGameApp` | 254 | **Roblox's stock vote** |
| 6457 | `mIsEnterGameScene` is true and no earlier match | 254 | generic game-scene 60 |

Thermal Manager adds three conditional 60 display controls:

| File / lines | Trigger | Path |
| --- | --- | --- |
| `feedbackcontrol/ThermalManager.java:584` | 90 FPS thermal-limit settings observer fires | `displayControl(60)` |
| `feedbackcontrol/ThermalManager.java:2863` | thermal display-control code 5 on `popsicle` / `pudding` / `pandora` / `nezha` | `displayControl(60)` |
| `feedbackcontrol/ThermalManager.java:2868` | thermal display-control code 1 | `displayControl(60)` |

`ThermalManager.displayControl` delegates at lines 2881-2888:

```java
DisplayFrameSetting.getDFSInstance().setScreenEffect(i2, THERMAL);
```

`THERMAL` is cookie 253 at `ThermalManager.java:175`.

### 3.2 State constants and default-60 seeds

`DisplayFrameSetting.java`:

| Lines | Value | Classification |
| --- | --- | --- |
| 519-521 | `DEFAULT_FPS_VALUE = 60`, `CAMERA_FPS_VALUE = 60`, `VIDEO_FPS_VALUE = 60` | named fallback/vote constants |
| 643 | `mLastFps = 60` | initial last-rate state |
| 644 | `mEnterHighFpsValue = 60` | initial high-FPS detection state |

Other PowerKeeper classes:

| Site | Value | Classification |
| --- | --- | --- |
| `perfengine/PeGameController.java:66` | `f502e0 = 60` | scheduler performance-state seed; overwritten from `DisplayFrameSetting.getUserFps()` |
| `thermal/listener/FpsListener.java:21` | `mEnterHighFpsValue = 60` | video-FPS listener state, not a display vote |
| `statemachine/FKVideoReceiver.java:12,54,62` | `FPS_60 = 60` | video-record event classifier, not a display vote |
| `unionpower/corehandler/HandlerC0754j.java:199` | `optInt("frameRate", 60)` | lazy-FPS cloud-config default |

### 3.3 Policy and list parsers that materialize 60

`DisplayFrameSetting.java`:

| Lines | Source key / policy | Result |
| --- | --- | --- |
| 1206-1208 | `key_top_names` | every listed package gets 60 in `getPkgFpsConfig` |
| 1212-1214 | top-video package list | every listed package gets 60 |
| 1331-1349 | `list60`, `list60_game`, `list60_fold` | every listed package gets 60 |
| 3717-3731 | `input_list60` | input apps get 60 |
| 3746-3753 | `audio_list60` | audio apps get 60 |
| 4096, 4144, 4171 | whitelist policy | `mDefaultFps = 60` |
| 4102, 4150, 4176, 4432, 4451 | white-FPS-list policy | `mDefaultFps = 60` |
| 4106, 4154, 4178, 4435, 4453 | `FeatureParser.getInteger("defaultFps", 60)` | blacklist/default fallback |
| 4186-4198 | `list60` in define config | `mTopDefineApps` gets 60 |
| 4461-4485 | `list60`, `list60_fold`, `list60_game` | smart-app maps get 60 |
| 5240 | `updateRefreshRate` fallback | absent user rate -> `defaultFps`, default 60 |
| 5388 | `getUserFps` fallback | absent user rate -> `defaultFps`, default 60 |

Important nuance: when the parsed default is exactly 60, the code calls
`Utils.getArrayMaxMember(supportFps, 60)` (for example lines 4106-4109 and
4178-4181). On a panel whose supported list includes 120, this selects the
max supported member while still treating 60 as the policy baseline. The
hard Roblox game vote at lines 6393-6395 bypasses this list-selection logic.

### 3.4 User/custom high-refresh table stores 60

The PowerKeeper `highRefreshRateTable` rows are interpreted as custom-app
60 entries:

| Lines | Context |
| --- | --- |
| 2503 | package added in video/package-change path |
| 2540 | top-define package added under custom switch |
| 2668 | top-define package added under custom switch |
| 2747 | top-define package added under custom switch |
| 4085 | database rows loaded into `mCustomApps` |
| 4245 | list60 package inserted into custom table |
| 4588 | video package inserted into custom table |
| 5195 | `custom_mode` observer adds package at 60 |

The table itself is created in
`provider/HighRefreshRateHelper.java:49-50`, exposed through
`provider/HighRefreshRateConfigure.java:7-8`, and consumed by MISettings at
`p009a8/C0057h.java:329`.

### 3.5 Comparisons, guards, and diagnostic 60s

These contain 60 but do not impose 60 by themselves:

| Lines | What happens |
| --- | --- |
| 2322 | skip Youku high-FPS notification when custom Youku value or `thermal_limit_refresh_rate` is 60 |
| 4186, 4461 | only parse list60 when `mDefaultFps != 60` |
| 5242 | ignore a `miui_refresh_rate` reset when computed user rate is <= 60 |
| 5326, 5329 | dump labels `mDefaultGameApp(60)` and `mVideoApps(60)` |
| 5972 | extreme-scene branch only when measured refresh rate <= 60.0 |
| 6207, 6209 | checks whether Youku's configured rate is 60 |
| 6596, 6637 | honor a user-selected rate <= 60 |

## 4. PowerKeeper Foreground Precedence

Order in `onForegroundChanged`, `DisplayFrameSetting.java:6200-6472`:

1. Input-list branch, with 30 / 60 fallbacks (`6214-6225`).
2. Audio-list branch, with 30 / 60 fallbacks (`6226-6238`).
3. Blacklist low-FPS and VR activity branches (`6239-6256`).
4. High-FPS activity branch, can emit 120 (`6257-6260`).
5. Extreme-video and applet branches, emit 60 (`6263-6284`).
6. Split-screen / map / Qsync early exits (`6290-6350`).
7. Whitelist-policy `mTopApps` branch (`6351-6365`).
8. Video-app branch, emits 60 (`6367-6369`).
9. `mPrivGames` lookup (`6381-6391`).
   - If present, uses the private-game rate unless SmartFPS has a
     `mGameTopSmartApps` entry for it.
10. `mDefaultGameApp` lookup, emits literal 60 (`6393-6395`).
11. White-FPS-list `mTopApps` branch (`6397-6411`).
12. Highest-FPS switches (`6413-6428`).
13. Normal `mTopApps` branch (`6429-6450`).
14. Video scene fallback (`6452-6454`).
15. Game scene fallback, emits literal 60 (`6456-6458`).
16. Normal fallback, emits `mUserFps` (`6460-6471`).

The 120 override is priority 9 because message 12 stores the package in
`mPrivGames`:

- broadcast handling at lines 764-774;
- message 12 handling at lines 5730-5743;
- `getPrivGamesFps` loads persisted `key_priv_names` at lines 1220-1237;
- initialization loads those values into `mPrivGames` at lines 3607-3616.

## 5. MISettings Refresh-Rate Surface

### 5.1 Current and written rate

`mod/misettings_jadx/sources/ma/AbstractC3047a.java`:

- `f13561a` = `ro.vendor.fps.switch.default` at line 26.
- default/static rate is `smart_fps_value` when SmartFPS is supported,
  otherwise `defaultFps`, at line 38.
- current rate is Secure `user_refresh_rate` (API 33+) or System
  `user_refresh_rate`, otherwise property `persist.vendor.dfps.level`, at
  lines 64-80.
- user write path at lines 172-187:
  - Secure/System `user_refresh_rate`
  - System `peak_refresh_rate` and Secure `miui_refresh_rate` only when
    `f13561a` is true
  - otherwise feature id 24.
- SmartFPS read/write at lines 141 and 194.
- speed-mode read at line 122.

MISettings does not hardcode a 60 default. Its `FeatureParser.getInteger`
helper is invoked with default `0` in
`p128g7/AbstractC2174a.java:19-20`.

### 5.2 UI choices

`NewRefreshRateFragment.java`:

- choices come from `FeatureParser.getIntArray("fpsList")` at lines 186-194;
- the helper is `p128g7/AbstractC2174a.java:14-15`;
- `defaultFps` is read from feature config at line 90;
- the "save battery" label is formatted with 60 at line 468.

`OldRefreshRateFragment.java`:

- the `60` branch uses string resource `fps_standard_title` at lines 68-70.
  That is a label, not an enforcement value.

The two 60s at `NewRefreshRateFragment.java:125` and `130` are power-save /
DC-backlight compatibility checks against the current rate; they do not
force 60.

### 5.3 High-refresh app screen

- `C0057h` queries both
  `content://com.miui.powerkeeper.configure/highRefreshRateTable` and
  `content://com.xiaomi.Joyose.provider/game_list`.
- Packages returned from Joyose's `getGameList` are placed under the
  `follow_apps_settings` section, which has no toggle.
- A toggle change sends `miui.intent.action.HIGH_REFRESH_SWITCH` with
  `packagename` and `state` to
  `com.android.settings.MiuiSettingsReceiver`
  (`p262oa/AbstractC3777a.java:53-59`).
- Shared preference `last_fps_value` is only a UI memory at
  `AbstractC3047a.java:168` and `NewRefreshRateFragment.java:278,317`.

## 6. Joyose Conditional Refresh-Rate Vote

Joyose is not the source of the Roblox 60 vote in the bundled APK. Its
dynamic-refresh code only votes for packages that meet an explicit cloud
condition.

`mod/joyose_jadx/sources/com/xiaomi/joyose/utils/AbstractC0532k.java`:

- the vote block requires the package to be in
  `support_dynamic_refresh_rate_games` or to have an explicit configurable
  entry, checked at line 175;
- the low-scene branch sets `iM1999c = 60` at line 183;
- otherwise `m1999c` chooses the nearest supported display refresh rate from
  the cloud list;
- the result is sent as
  `com.xiaomi.joyose.OVERRIDE_GAME_FRESHRATE` at lines 46-50 and 201;
- `m2000d` computes `Math.max(configured_rate, 60)` at line 78.

Call flow:

- foreground game -> `C0457i.java:2195` -> `m2005i` -> `m2008l`.
- target-FPS update -> `m2013q` at `C0457i.java:1230-1257` and 1443/2234.

### 6.1 Joyose TARGET_FPS default 60

The per-package target-FPS preference defaults to the string `"60"` in
multiple places:

- `p047f0/C0814z.java:728`
- `p047f0/C0782a0.java:68`
- `p047f0/C0791f.java:29`
- `com/xiaomi/joyose/utils/AbstractC0547w.java:97-102`
- `com/xiaomi/joyose/smartop/gamebooster/control/C0457i.java:1443,2234`
- `com/xiaomi/joyose/smartop/gamebooster/control/C0458j.java:357`

This is a target-FPS preference used by game-booster calculations, not an
unconditional display-refresh vote.

### 6.2 Cloud parsing

`p047f0/C0814z.java:2279-2348` parses:

- `support_display_refresh_rates`
- `low_display_refresh_rate_scenes`
- `support_dynamic_refresh_rate_games`
- `invalid_low_display_scenes_games`
- `support_calculate_target_fps_games`
- `support_speed_mode_games`
- `support_mtk_targetfps_v1_games`
- `support_highfps_app`

`support_highfps_app` entries whose max FPS is `<= 60` are explicitly
rejected at lines 2336-2339. That is an anti-high-FPS gate, not a 60 cap.

### 6.3 Which cloud file is selected

`p046f/C0777h.java`:

- `m3293A` builds a device-specific cloud object at lines 528-549.
- `m3320w` produces `default_cloud_<suffix>.json` at lines 909-916.
- `m3323z` overlays generic `default_cloud.json` with the device/ROM config at
  lines 937-952.
- device suffix comes from `Utils.m1889q` using `ro.product.real_model` or
  `Build.MODEL` (`Utils.java:581-586`).
- stability/region suffix comes from `Utils.m1874b` using alpha/stable/dev and
  global flags (`Utils.java:275-287`).
- ROM fallback is `/odm/etc/default_cloud.json`.

### 6.4 Shipped Joyose data conclusion

`tools/audit_joyose_cloud.py mod/Joyose.apk` enumerated all 26 JSON assets.
Conclusions:

- `assets/default_cloud.json` only has `common_config.support_app`; it has no
  game-booster refresh keys.
- bundled `default_cloud_<model>.json` files cover older commercial model
  numbers, not `klee` or a 2511-series model.
- no bundled `support_dynamic_refresh_rate_games`,
  `support_highfps_app`, or scene list contains Roblox.
- the only bundled Roblox hit is `assets/top_game_list.json`, which feeds the
  PowerKeeper default-game path.
- the runtime cloud/ODM JSON is not bundled and remains unverified.

`tools/audit_joyose_cloud.py mod/Joyose.apk --roblox-only` returns no hits for
the refresh keys, which is expected and confirms the shipped-data conclusion.

## 7. Thermal Stack

`mod/powerkeeper_jadx/sources/com/miui/powerkeeper/feedbackcontrol/ThermalManager.java`:

- `TEMP_DISPLAY_CTRL_60HZ = 1` at line 151.
- settings observer may call `displayControl(60)` at lines 583-585 when the
  ninety-FPS thermal-limit feature is enabled and the last FPS is 90.
- display-control mapping calls 60 for control code 1 at lines 2867-2868.
- control code 5 emits 60 only for `popsicle`, `pudding`, `pandora`, `nezha`
  at lines 2860-2865; otherwise it emits 90.
- `displayControl` forwards to `DisplayFrameSetting.setScreenEffect(i2, 253)`
  at lines 2881-2888.
- `DisplayFrameSetting.setScreenEffect(int,int)` writes System
  `thermal_limit_refresh_rate` and forwards cookie 253 when the FPS thermal
  switch is enabled at lines 6522-6526.

The special ninety-to-60 observer device list is in
`thermal/resource/ThermalFeatureConfig.java:51`:

```java
popsicle, pudding, pandora, nezha
```

`klee` is not in that list, so that specific observer branch does not target
the reported device model.

Temperature-related 60 values are not refresh caps:

- `ThermalManager.java:98` default backlight threshold
- `ThermalManager.java:225` field initialization
- `ThermalManager.java:3120,3146` threshold lookups

## 8. Settings And Property Reference

### 8.1 Settings values found in decompiled code

| Key | Type | Writes / reads |
| --- | --- | --- |
| `miui_refresh_rate` | Secure | PowerKeeper 5119, 5247, 6584, 6661; MISettings 185 |
| `user_refresh_rate` | Secure / System | MISettings 74, 177, 179; PowerKeeper 5238, 5386; Joyose reads with 120 defaults in many classes |
| `peak_refresh_rate` | System | MISettings 184 |
| `thermal_limit_refresh_rate` | System | PowerKeeper write 6524; read 2322 |
| `speed_mode` | System | PowerKeeper 517, 3539, 3604, 6488-6498; MISettings 122 |
| `is_smart_fps` | System | PowerKeeper 3509, 3526; MISettings 141, 194 |
| `custom_mode_switch` | System | PowerKeeper 515, 3170, 6488-6502; MISettings 176, 280 |
| `custom_mode` | System | PowerKeeper 3557-3560; MISettings `C0057h` 303 |
| `POWER_SAVE_MODE_OPEN` | System | MISettings 125; PowerKeeper observer 3565 |
| `support_highfps` | Secure | Joyose `C0814z` 737 |

PowerKeeper `SimpleSettings.Misc` persisted values:

- `key_top_names` - default-game list; write 5574, 5584; read 1206, 2520,
  2651, 2730, 2785, 3609
- `key_priv_names` - private/override map; read 1225; write 5629
- `lazy_fps_group` - UnionPower lazy-FPS JSON

Provider URIs:

- `content://com.miui.powerkeeper.configure/highRefreshRateTable`
- `content://com.xiaomi.Joyose.provider/game_list`

### 8.2 System properties

| Property | Use |
| --- | --- |
| `ro.vendor.fps.switch.default` | enables direct `miui_refresh_rate` writes; PowerKeeper 619, MISettings 26 |
| `ro.vendor.fps.switch.thermal` | enables `thermal_limit_refresh_rate`; PowerKeeper 626 |
| `ro.vendor.smart_dfps.enable` | Smart DFPS path; PowerKeeper 620 |
| `ro.vendor.video.decode.only` | disables video-package 60 branch; PowerKeeper 621 |
| `ro.miui.surfaceflinger_affinity` | SurfaceFlinger affinity feature; PowerKeeper 627 |
| `ro.miui.product.home` | launcher package; PowerKeeper 629 |
| `persist.sys.smartpower.display.enable` | delay behavior; PowerKeeper 630 |
| `persist.vendor.dfps.level` | fallback current FPS; MISettings 76 |
| `ro.product.real_model` / `Build.MODEL` | Joyose cloud-file selection; Joyose `Utils` 581-586 |
| `ro.miui.build.region` | extra-video / international config checks; PowerKeeper 204, 1432 |
| `ro.miui.region` | Joyose `Utils` 591 |

FeatureParser / MIUI feature-config keys:

| Key | Default | Where |
| --- | --- | --- |
| `defaultFps` | 60 in PowerKeeper | DisplayFrameSetting 4106 and similar |
| `smart_fps_value` | 120 in PowerKeeper | DisplayFrameSetting 5240, 5388 |
| `support_max_fps` | 120 in PowerKeeper | DisplayFrameSetting 628 |
| `fpsList` | no local 60 default | MISettings `AbstractC2174a` 14-15 |
| `support_smart_fps` | false | PowerKeeper 3526, 5240, 5388 |

## 9. Classification Summary

Hard renderer/engine defaults:

- Roblox `TaskSchedulerTargetFps` zero -> 60
- Roblox `GraphicsOptimizationModeFRMFrameRateTarget` -> 60
- Roblox `PhysicsStepLimitMaxFPS` -> 60
- Roblox display-rate floor to 60

UI choices:

- Roblox `FramerateCaps` starts at 60
- Roblox `PhysicsSimulationRate.Fixed60Hz`
- MISettings old `fps_standard_title` label
- MISettings battery-tip text using 60

Unconditional or policy ROM votes:

- PowerKeeper `mDefaultGameApp` -> 60, cookie 254
- PowerKeeper generic game scene -> 60, cookie 254
- PowerKeeper whitelist / white-FPS-list defaults to 60
- PowerKeeper `key_top_names` and `getPkgFpsConfig` map to 60
- PowerKeeper video apps -> 60, cookie 248

Conditional ROM votes:

- PowerKeeper input/audio/low-FPS/VR/extreme-video/applet/camera branches
- Thermal Manager thermal-control code branches
- Joyose low-display-scene -> 60, only for explicitly listed packages

Telemetry, defaults, and unrelated constants:

- `ScrollingPerfTrackerTargetFPS = 60`
- `PeGameController.f502e0 = 60` before `getUserFps()` overwrites it
- `FpsListener.mEnterHighFpsValue = 60`
- `FKVideoReceiver.FPS_60 = 60`
- UnionPower `frameRate` fallback 60
- thermal temperature thresholds equal to 60
- RecyclerView 60 ms smooth-scroll fallback from the Roblox DEX

## 10. Verification Commands For A Live Device

These were not run in this static session. They are the device-side checks
needed to confirm the active branch:

```text
adb shell getprop ro.product.real_model
adb shell getprop ro.vendor.fps.switch.default
adb shell getprop ro.vendor.fps.switch.thermal
adb shell settings get secure miui_refresh_rate
adb shell settings get secure user_refresh_rate
adb shell settings get system peak_refresh_rate
adb shell settings get system thermal_limit_refresh_rate
adb shell settings get system is_smart_fps
adb shell settings get system speed_mode
adb shell settings get system custom_mode_switch
adb shell settings get system custom_mode
adb shell dumpsys powerkeeper
adb shell dumpsys power
adb shell content query --uri content://com.miui.powerkeeper.configure/highRefreshRateTable
adb shell content call --uri content://com.xiaomi.Joyose.provider/game_list --method getGameList
```

The most direct PowerKeeper evidence appears in its dump:

```text
fpsconfig mPrivGames={com.roblox.client=120, ...}
fpsconfig mDefaultGameApp(60):{com.roblox.client, ...}
setScreenEffect pkg=com.roblox.client fps=60 cookie=254
```

## 11. Residual Gaps

- Live MIUI cloud and `/odm/etc/default_cloud.json` were not available.
- SurfaceFlinger, display driver, and panel firmware behavior are outside the
  decompiled APK scope.
- No live `adb` trace was performed in this session.
- The exact MIUI software version on the device is not derived from these APK
  dumps; line numbers are from the extracted APKs in `mod/`.

## 12. Artifacts And Tools

- [`12_60HZ_CAP_AUDIT.md`](12_60HZ_CAP_AUDIT.md) - Roblox APK detail
- [`20_MIUI_REFRESH_OVERRIDE.md`](20_MIUI_REFRESH_OVERRIDE.md) - observed
  override and patch
- [`21_NATIVE_TASK_SCHEDULER_CAPS.md`](21_NATIVE_TASK_SCHEDULER_CAPS.md)
- [`22_NATIVE_FRAME_PACING_MAP.md`](22_NATIVE_FRAME_PACING_MAP.md)
- [`13_SCHEDULER_DEFAULT_AND_FRM_INIT_PATCH.md`](13_SCHEDULER_DEFAULT_AND_FRM_INIT_PATCH.md)
- `analysis/docs/artifacts/powerkeeper_fps_configs.tsv`
- [`tools/audit_joyose_cloud.py`](../../tools/audit_joyose_cloud.py)

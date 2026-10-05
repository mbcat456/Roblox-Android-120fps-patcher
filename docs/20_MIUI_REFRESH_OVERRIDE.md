# MIUI 60 Hz Hard Cap and the 120 Hz Override

## Why The App Looked Locked

On the `klee_eea` test device, Roblox appears in the MIUI "follow app
settings" bucket. That bucket is built from Joyose's game list:

- `MISettings` decompile:
  `mod/misettings_jadx/sources/com/xiaomi/misettings/display/RefreshRate/HighRefreshOptionsFragment.java:197`
  builds the list and appends the `follow_apps_settings` header at line 207.
- The game-list lookup is `p009a8/C0057h.m182f()`, which calls
  `content://com.xiaomi.Joyose.provider/game_list`, method `getGameList`.

Packages returned by that provider are deliberately shown without a switch.
This is why the settings screen says "In base alle impostazioni dell'app"
for Roblox even after removing `Surface.setFrameRate`.

## The Actual 60 Hz Vote

`com.miui.powerkeeper` has a cloud game table
(`SimpleSettings.Misc.getString(context, "key_top_names")`) that includes
`com.roblox.client`. PowerKeeper stores it in `mDefaultGameApp`.

Relevant decision points in
`mod/powerkeeper_jadx/sources/com/miui/powerkeeper/statemachine/DisplayFrameSetting.java`:

```text
6393  if (this.mDefaultGameApp.contains(pkg))
6394      setScreenEffect(pkg, 60, 254);
```

The live service dump on the device showed:

```text
fpsconfig mDefaultGameApp(60):{com.roblox.client, com.miHoYo.Yuanshen}
setScreenEffect pkg=com.roblox.client fps=60 cookie=254
```

The app-side `preferredDisplayModeId=3` request was already correct, so this
MIUI vote was the remaining 60 Hz source.

## The Override Path

MIUI's receiver also handles `com.xiaomi.joyose.OVERRIDE_GAME_FRESHRATE`:

```text
764  ACTION_OVERRIDE_GAME_FRESHRATE
5730 case MSG_OVERRIDE_GAME_FRESHRATE (12)
5736 mPrivGames.put(pkg, suitableFps)
5741 onForegroundChanged(current app)
```

Foreground selection checks `mPrivGames` first:

```text
6381  Integer num2 = mPrivGames.get(pkg);
6385      setScreenEffect(pkg, num2, 254);
```

Joyose itself uses the same broadcast in
`mod/joyose_jadx/sources/com/xiaomi/joyose/utils/AbstractC0532k.java:46`.
Its normal sender sets the explicit PowerKeeper package in
`AbstractC0531j0.java:16`.

## Patch

`MiuiRefreshOverride` sends this explicit broadcast with
`override_pkg_name=com.roblox.client` and `override_freshrate=120`, then
repeats it after 1500 ms so it wins over Joyose's own recalculation:

```text
apktool_out/smali_classes2/com/roblox/client/MiuiRefreshOverride.smali
apktool_out/smali_classes2/com/roblox/client/MiuiRefreshOverride$1.smali
MainGameActivity.onCreate / onResume
ActivityNativeMain.onCreate / onResume
```

Expected live state after the patch:

```text
fpsconfig mPrivGames={com.roblox.client=120, ...}
setScreenEffect pkg=com.roblox.client fps=120 cookie=254
```

The manual equivalent is:

```powershell
adb shell am broadcast -a com.xiaomi.joyose.OVERRIDE_GAME_FRESHRATE `
  --es override_pkg_name com.roblox.client --ei override_freshrate 120
```

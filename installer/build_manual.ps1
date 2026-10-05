param(
    [string]$SdkDir = (Join-Path $PSScriptRoot "..\local_sdk"),
    [string]$Key = "mod\keys\mod_release.jks",
    [string]$Alias = "modkey",
    [string]$StorePass = "modpass123",
    [string]$KeyPass = "modpass123",
    [string]$PythonExe = "python.exe"
)

$ErrorActionPreference = "Stop"
$bt = Join-Path $SdkDir "build-tools\36.0.0"
$android = Join-Path $SdkDir "platforms\android-36\android.jar"
$src = "installer\app\src\main"
$out = "installer\manual"
$java = "C:\Program Files\Java\jdk-26.0.2.1\bin\javac.exe"

Remove-Item -Recurse -Force $out -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $out | Out-Null

& "$bt\aapt2.exe" compile --dir "$src\res" -o "$out\res.zip"
& "$bt\aapt2.exe" link `
    -I "$android" `
    --manifest "$src\AndroidManifest.xml" `
    --java "$out\gen" `
    --min-sdk-version 24 `
    --target-sdk-version 35 `
    --version-code 2 `
    --version-name 1.1 `
    -o "$out\app.unsigned.apk" `
    "$out\res.zip"

New-Item -ItemType Directory -Force -Path "$out\classes" | Out-Null
& $java `
    -source 8 -target 8 -Xlint:-options `
    -classpath $android `
    -d "$out\classes" `
    "$out\gen\com\marco\robloxapkm\R.java" `
    "$src\java\com\marco\robloxapkm\MainActivity.java"
$javacExit = $LASTEXITCODE
if ($javacExit -ne 0 -and -not (Test-Path "$out\classes\com\marco\robloxapkm\MainActivity.class")) {
    throw "javac failed and MainActivity.class was not produced"
}

New-Item -ItemType Directory -Force -Path "$out\dex" | Out-Null
$classFiles = Get-ChildItem -Recurse -File "$out\classes" -Filter *.class |
    Select-Object -ExpandProperty FullName
& "$bt\d8.bat" --min-api 24 --output "$out\dex" $classFiles

$env:PYTHONPATH = "tools\pylibs"
& $PythonExe installer\add_dex_to_apk.py `
    "$out\app.unsigned.apk" `
    "$out\dex\classes.dex" `
    "$out\app.with_dex.apk"

& "$bt\zipalign.exe" -f 4 "$out\app.with_dex.apk" "$out\app.aligned.apk"
New-Item -ItemType Directory -Force -Path release | Out-Null
& "$bt\apksigner.bat" sign `
    --ks $Key `
    --ks-key-alias $Alias `
    --ks-pass "pass:$StorePass" `
    --key-pass "pass:$KeyPass" `
    --out release\RobloxApkmInstaller.apk `
    "$out\app.aligned.apk"

& "$bt\apksigner.bat" verify --print-certs release\RobloxApkmInstaller.apk

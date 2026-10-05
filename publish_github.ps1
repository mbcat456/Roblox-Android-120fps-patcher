param(
    [string]$Owner = "mbcat456",
    [string]$Repo = "Roblox-Android-120fps-patcher",
    [string]$Tag = "v2.741.1061",
    [string]$ReleaseTitle = "Roblox 2.741.1061 120fps mod"
)

$ErrorActionPreference = "Stop"

gh auth status
if ($LASTEXITCODE -ne 0) {
    throw "GitHub CLI is not authenticated. Run: gh auth login"
}

git init
git add .
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git -c user.name="Anonymous" -c user.email="anonymous@users.noreply.github.com" commit -m "Roblox 120fps patcher and APKM installer"
}

gh repo create "$Owner/$Repo" --public --source . --push

$assets = @(
    "release\Roblox_2.741.1061_120fps_mod.apkm",
    "release\Roblox_2.741.1061_120fps_mod.apks",
    "release\RobloxApkmInstaller.apk",
    "release\base_mod_signed.apk",
    "release\split_config.arm64_v8a.apk",
    "release\split_config.armeabi_v7a.apk",
    "release\split_config.x86_64.apk"
)

gh release create $Tag $assets `
    --repo "$Owner/$Repo" `
    --title $ReleaseTitle `
    --notes "See README.md and docs/ for install and reverse-engineering notes."

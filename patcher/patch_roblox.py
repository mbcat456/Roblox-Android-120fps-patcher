import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
KNOWN_VERSION = "3212"


def run(command, cwd=None):
    print("+ " + " ".join(str(part) for part in command))
    result = subprocess.run(command, cwd=cwd, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def unpack_bundle(bundle: Path, work: Path):
    if not bundle.is_dir():
        with zipfile.ZipFile(bundle) as archive:
            archive.extractall(work)
        return
    for source in bundle.rglob("*.apk"):
        target = work / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for name in ("info.json", "icon.png"):
        source = bundle / name
        if source.is_file():
            shutil.copyfile(source, work / name)


def bundle_info(work: Path):
    info_path = work / "info.json"
    if info_path.exists():
        info = json.loads(info_path.read_text(encoding="utf-8"))
        return info.get("versioncode", ""), info
    return "", {}


def list_apks(work: Path):
    return sorted(work.rglob("*.apk"))


def patch_base_dex(base: Path, patched: Path):
    with zipfile.ZipFile(base) as archive:
        names = set(archive.namelist())
    dex_name = "classes2.dex" if "classes2.dex" in names else "classes.dex"
    raw = Path(HERE / "_work" / dex_name)
    with zipfile.ZipFile(base) as archive:
        raw.write_bytes(archive.read(dex_name))
    run([sys.executable, str(HERE / "patch_dex_auto.py"), str(raw)])
    run([
        sys.executable,
        str(HERE / "rewrite_apk_entries.py"),
        str(base),
        str(patched),
        f"{dex_name}={raw}",
    ])


def patch_split(split: Path, patched: Path, version: str):
    with zipfile.ZipFile(split) as archive:
        lib_names = [
            name for name in archive.namelist()
            if name.startswith("lib/") and name.endswith("/libroblox.so")
        ]
    replacements = []
    for name in lib_names:
        abi = name.split("/")[1]
        raw = Path(HERE / "_work" / "libs" / abi / "libroblox.so")
        raw.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(split) as archive:
            raw.write_bytes(archive.read(name))
        if version == KNOWN_VERSION:
            script = HERE / "patch_native_fps_cap_2741.py"
        else:
            script = HERE / "patch_native_auto.py"
        run([sys.executable, str(script), str(raw)])
        replacements.append(f"{name}={raw}")
    if not replacements:
        shutil.copyfile(split, patched)
        return
    run([
        sys.executable,
        str(HERE / "rewrite_apk_entries.py"),
        str(split),
        str(patched),
        ",".join(replacements),
    ])


def sign_apk(source: Path, target: Path, apksigner: Path, key: Path,
             alias: str, store_pass: str, key_pass: str):
    run([
        str(apksigner),
        "sign",
        "--ks", str(key),
        "--ks-key-alias", alias,
        "--ks-pass", f"pass:{store_pass}",
        "--key-pass", f"pass:{key_pass}",
        "--out", str(target),
        str(source),
    ])


def make_bundle(output: Path, files: list[Path]):
    bundle = output / "Roblox_120fps_mod.apks"
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.name)
    print(f"bundle={bundle}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help=".apkm, .apks, or extracted directory")
    parser.add_argument("--output", default="patched_output")
    parser.add_argument(
        "--apksigner",
        default="apksigner.bat",
    )
    parser.add_argument("--key", default="mod/keys/mod_release.jks")
    parser.add_argument("--alias", default="modkey")
    parser.add_argument("--store-pass", default="modpass123")
    parser.add_argument("--key-pass", default="modpass123")
    args = parser.parse_args()

    output = Path(args.output).resolve()
    work = Path(HERE / "_work")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    output.mkdir(parents=True, exist_ok=True)

    unpack_bundle(Path(args.input), work)
    version, _ = bundle_info(work)
    apks = list_apks(work)
    base = next((path for path in apks if path.name == "base.apk"), None)
    if base is None:
        raise SystemExit("base.apk not found in bundle")
    splits = [path for path in apks if path.name != "base.apk"]

    base_patched = work / "base_mod.apk"
    patch_base_dex(base, base_patched)
    split_patched = []
    for split in splits:
        target = work / f"{split.stem}_mod.apk"
        patch_split(split, target, version)
        split_patched.append(target)

    signed = []
    base_signed = output / "base_mod_signed.apk"
    sign_apk(base_patched, base_signed, Path(args.apksigner),
             Path(args.key), args.alias, args.store_pass, args.key_pass)
    signed.append(base_signed)
    for split in split_patched:
        target = output / f"{split.name.replace('.apk', '')}_signed.apk"
        sign_apk(split, target, Path(args.apksigner), Path(args.key),
                 args.alias, args.store_pass, args.key_pass)
        signed.append(target)

    make_bundle(output, signed)
    print(f"done: {output}")


if __name__ == "__main__":
    main()

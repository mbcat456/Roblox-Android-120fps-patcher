import json
import shutil
import sys
import zipfile
from pathlib import Path


def add_zip(archive: zipfile.ZipFile, path: Path, name: str) -> None:
    info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, path.read_bytes())


def make_bundle(web_dir: Path, bundle_name: str, names: dict) -> Path:
    output = web_dir / bundle_name
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for zip_name, source in names.items():
            add_zip(archive, source, zip_name)
    return output


def main() -> None:
    if len(sys.argv) != 3:
        print(
            "usage: make_phone_bundle.py RELEASE_DIR OUTPUT_DIR",
            file=sys.stderr,
        )
        raise SystemExit(2)

    release = Path(sys.argv[1])
    output = Path(sys.argv[2])
    output.mkdir(parents=True, exist_ok=True)

    base_source = release / "base_mod_signed.apk"
    split_source = release / "split_arm64_signed3.apk"
    info_source = release.parent / "apkm_extracted" / "info.json"
    icon_source = release.parent / "apkm_extracted" / "icon.png"
    for source in (base_source, split_source, info_source, icon_source):
        if not source.exists():
            raise SystemExit(f"missing source: {source}")

    base_copy = output / "base.apk"
    split_copy = output / "split_config.arm64_v8a.apk"
    shutil.copyfile(base_source, base_copy)
    shutil.copyfile(split_source, split_copy)

    info = json.loads(info_source.read_text(encoding="utf-8"))
    info["apk_title"] = "Roblox 2.741.1061 120fps mod"
    info_copy = output / "info.json"
    info_copy.write_text(json.dumps(info, indent=2), encoding="utf-8")
    icon_copy = output / "icon.png"
    shutil.copyfile(icon_source, icon_copy)

    names = {
        "base.apk": base_copy,
        "split_config.arm64_v8a.apk": split_copy,
        "info.json": info_copy,
        "icon.png": icon_copy,
    }
    apkm = make_bundle(
        output, "Roblox_2.741.1061_120fps_mod.apkm", names
    )
    apks = make_bundle(
        output, "Roblox_2.741.1061_120fps_mod.apks", names
    )

    for source, name in (
        (base_source, "Roblox_2.741.1061_base_mod.apk"),
        (split_source, "Roblox_2.741.1061_arm64_mod.apk"),
    ):
        shutil.copyfile(source, output / name)

    print(f"apkm={apkm} ({apkm.stat().st_size} bytes)")
    print(f"apks={apks} ({apks.stat().st_size} bytes)")
    print(f"individual APKs and installer metadata in {output}")


if __name__ == "__main__":
    main()

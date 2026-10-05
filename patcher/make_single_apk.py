import sys
import zipfile
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 4:
        print(
            "usage: make_single_apk.py BASE_APK OUTPUT_APK "
            "SPLIT_APK [SPLIT_APK ...]",
            file=sys.stderr,
        )
        raise SystemExit(2)

    base = Path(sys.argv[1])
    output = Path(sys.argv[2])
    splits = [Path(path) for path in sys.argv[3:]]

    entries = {}
    with zipfile.ZipFile(base) as archive:
        for info in archive.infolist():
            if info.filename.startswith("META-INF/"):
                continue
            entries[info.filename] = (archive.read(info.filename), info)

    for split in splits:
        with zipfile.ZipFile(split) as archive:
            for info in archive.infolist():
                if not info.filename.startswith("lib/"):
                    continue
                entries[info.filename] = (archive.read(info.filename), info)

    with zipfile.ZipFile(
        output, "w", zipfile.ZIP_DEFLATED
    ) as destination:
        for name, (data, info) in entries.items():
            copy = zipfile.ZipInfo(
                name, (1980, 1, 1, 0, 0, 0)
            )
            copy.compress_type = zipfile.ZIP_DEFLATED
            copy.external_attr = info.external_attr
            copy.create_system = info.create_system
            destination.writestr(copy, data)

    with zipfile.ZipFile(output) as check:
        for name in entries:
            if check.read(name) != entries[name][0]:
                raise RuntimeError(f"{name} did not round-trip")

    print(f"{output}: {len(entries)} entries, {output.stat().st_size} bytes")


if __name__ == "__main__":
    main()

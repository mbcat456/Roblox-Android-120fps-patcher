import sys
import zipfile
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 4:
        print(
            "usage: rewrite_apk_entries.py INPUT_APK OUTPUT_APK "
            "ENTRY=FILE[,ENTRY=FILE...]",
            file=sys.stderr,
        )
        raise SystemExit(2)

    source = Path(sys.argv[1])
    output = Path(sys.argv[2])
    replacements = {}
    for pair in sys.argv[3].split(","):
        entry, path = pair.split("=", 1)
        replacements[entry] = Path(path).read_bytes()
    expected = dict(replacements)

    with zipfile.ZipFile(source) as src, zipfile.ZipFile(
        output, "w", zipfile.ZIP_DEFLATED
    ) as dst:
        for info in src.infolist():
            data = replacements.pop(info.filename, src.read(info.filename))
            dst.writestr(info, data)
        for entry, data in replacements.items():
            dst.writestr(entry, data)

    with zipfile.ZipFile(output) as check:
        for entry, data in expected.items():
            if check.read(entry) != data:
                raise RuntimeError(f"{entry} did not round-trip")

    print(f"{source.name}: {len(expected)} entries -> {output}")


if __name__ == "__main__":
    main()

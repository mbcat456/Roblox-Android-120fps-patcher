import sys
import zipfile
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 4:
        print(
            "usage: add_dex_to_apk.py INPUT_APK DEX_FILE OUTPUT_APK",
            file=sys.stderr,
        )
        raise SystemExit(2)

    source = Path(sys.argv[1])
    dex = Path(sys.argv[2]).read_bytes()
    output = Path(sys.argv[3])

    with zipfile.ZipFile(source) as src, zipfile.ZipFile(
        output, "w", zipfile.ZIP_DEFLATED
    ) as dst:
        for info in src.infolist():
            dst.writestr(info, src.read(info.filename))
        dst.writestr("classes.dex", dex)

    print(f"{source.name}: added classes.dex ({len(dex)} bytes) -> {output}")


if __name__ == "__main__":
    main()

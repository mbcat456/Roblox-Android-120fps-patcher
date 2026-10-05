import sys
import zipfile
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 4:
        print(
            "usage: rewrite_split_lib.py SPLIT_APK PATCHED_LIB OUT_APK",
            file=sys.stderr,
        )
        raise SystemExit(2)

    split = Path(sys.argv[1])
    library = Path(sys.argv[2])
    output = Path(sys.argv[3])
    target = f"lib/{library.parent.name}/{library.name}"
    replacement = library.read_bytes()

    with zipfile.ZipFile(split) as source:
        infos = source.infolist()
        with zipfile.ZipFile(
            output,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as destination:
            for info in infos:
                data = source.read(info.filename)
                if info.filename == target:
                    data = replacement
                copy = zipfile.ZipInfo(info.filename, (1980, 1, 1, 0, 0, 0))
                copy.compress_type = zipfile.ZIP_DEFLATED
                copy.external_attr = info.external_attr
                copy.create_system = info.create_system
                destination.writestr(copy, data)

    with zipfile.ZipFile(output) as check:
        if check.read(target) != replacement:
            raise RuntimeError("replacement did not round-trip")
    print(f"{split.name}: replaced {target} -> {output}")


if __name__ == "__main__":
    main()

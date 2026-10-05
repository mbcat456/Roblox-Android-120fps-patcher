import hashlib
import struct
import sys
import zlib
from pathlib import Path

from patch_dex_minimal import (
    get_method_names_and_protos,
    get_type_descriptors,
    parse_class_data,
    read_code_item,
    read_dex,
)


WANTED_PROTO = "(Landroid/view/Display;)F"


def iter_methods(data, header):
    names, protos = get_method_names_and_protos(data, header)
    for class_index in range(header["class_defs_size"]):
        for name, proto, code_start, code_len, code_off in parse_class_data(
            data, header, class_index, names, protos
        ):
            yield class_index, name, proto, code_start, code_len, code_off


def patch_code_item(data: bytearray, code_off: int):
    item = read_code_item(data, code_off)
    if item["registers"] < 1 or item["insns_size"] < 2:
        raise RuntimeError(
            f"display-rate method is too small at 0x{code_off:x}"
        )

    # const/high16 v0, 0x42f00000; return v0
    replacement = bytes.fromhex("1500F0420E00")
    instruction_offset = code_off + 16
    data[instruction_offset:instruction_offset + 4] = replacement[:4]
    struct.pack_into("<I", data, code_off + 8, 0)
    struct.pack_into("<I", data, code_off + 12, 2)
    return instruction_offset


def rewrite_checksums(data: bytearray):
    signature = hashlib.sha1(bytes(data[32:])).digest()
    data[12:32] = signature
    checksum = zlib.adler32(bytes(data[12:])) & 0xFFFFFFFF
    struct.pack_into("<I", data, 8, checksum)


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: patch_dex_auto.py CLASSES_DEX", file=sys.stderr)
        raise SystemExit(2)

    path = Path(sys.argv[1])
    data = bytearray(path.read_bytes())
    header = read_dex(data)
    candidates = [
        (class_index, code_off)
        for class_index, name, proto, _, _, code_off in iter_methods(data, header)
        if proto == WANTED_PROTO and code_off
    ]

    if len(candidates) != 1:
        print(
            f"display-rate method candidates={len(candidates)}; "
            "skipping automatic DEX patch"
        )
        print([(class_index, hex(code_off)) for class_index, code_off in candidates])
        return

    _, code_off = candidates[0]
    patch_code_item(data, code_off)
    rewrite_checksums(data)
    path.write_bytes(data)
    print(f"patched display-rate getter at code offset 0x{code_off:x}")


if __name__ == "__main__":
    main()

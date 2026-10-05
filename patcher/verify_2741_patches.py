import hashlib
import sys
import zipfile
from pathlib import Path


ARM64 = {
    "lib/arm64-v8a/libroblox.so": [
        (0x283122C, "2040201E"),
        (0x24203EC, "000F80521F2003D51F2003D5"),
        (0x22B2BEC, "28F0E7F2"),
        (0x1E6FF5C, "080F8052"),
        (0x2F3CBE4, "000F8052"),
        (0x44577D8, "000F8052"),
        (0x44C31E8, "080F8052"),
        (0x44C31F4, "084C01B9"),
        (0x2E06E50, "20008052C0035FD6"),
        (0x22C7D00, "28008052"),
        (0x4609B04, "000F8052C0035FD61F2003D5"),
        (0x6383D68, "20008052C0035FD6"),
    ],
}

X86_64 = {
    "lib/x86_64/libroblox.so": [
        (0x237135F, "48B8111111111111813F"),
        (0x24FE959, "B878000000909090"),
        (0x29792AC, "0F28D8" + "90" * 37),
        (0x1E58EF1, "C7052D614E0578000000"),
        (0x28941F3, "B001C390909090"),
        (0x2370118, "0F1F4000"),
    ],
}


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: verify_2741_patches.py ARM64_SPLIT X86_64_SPLIT",
              file=sys.stderr)
        raise SystemExit(2)

    failures = []
    checks = 0
    for split_path, entries in (
        (Path(sys.argv[1]), ARM64),
        (Path(sys.argv[2]), X86_64),
    ):
        with zipfile.ZipFile(split_path) as apk:
            for name, patches in entries.items():
                data = apk.read(name)
                digest = hashlib.sha256(data).hexdigest()
                print(f"{split_path.name} {name} sha256={digest}")
                for offset, expected_hex in patches:
                    expected = bytes.fromhex(expected_hex)
                    actual = data[offset:offset + len(expected)]
                    checks += 1
                    if actual != expected:
                        failures.append(
                            f"{split_path.name} 0x{offset:x}: "
                            f"{actual.hex()} != {expected.hex()}"
                        )

    if failures:
        print("FAIL")
        for failure in failures:
            print(failure)
        raise SystemExit(1)

    print(f"PASS: {checks} patch byte-ranges verified")


if __name__ == "__main__":
    main()

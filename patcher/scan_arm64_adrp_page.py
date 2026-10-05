import struct
import sys
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN


def sign_extend(value: int, bits: int) -> int:
    sign = 1 << (bits - 1)
    return (value ^ sign) - sign


def executable_text_range(elf_path: Path):
    data = elf_path.read_bytes()
    if data[:4] != b"\x7fELF" or data[4] != 2:
        raise RuntimeError("expected a 64-bit ELF")
    phoff = struct.unpack_from("<Q", data, 0x20)[0]
    phentsize = struct.unpack_from("<H", data, 0x36)[0]
    phnum = struct.unpack_from("<H", data, 0x38)[0]
    for index in range(phnum):
        offset = phoff + index * phentsize
        p_type, p_flags = struct.unpack_from("<II", data, offset)
        if p_type == 1 and p_flags & 1:
            return (struct.unpack_from("<Q", data, offset + 8)[0],
                    struct.unpack_from("<Q", data, offset + 32)[0])
    raise RuntimeError("no executable PT_LOAD segment")


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: scan_arm64_adrp_page.py ELF_PATH TARGET_PAGE_HEX",
              file=sys.stderr)
        raise SystemExit(2)

    elf_path = Path(sys.argv[1])
    target_page = int(sys.argv[2], 16) & ~0xFFF
    text_offset, text_size = executable_text_range(elf_path)
    data = elf_path.read_bytes()
    decoder = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    decoder.detail = True
    hits = []

    for index in range(0, text_size - 16, 4):
        address = text_offset + index
        word = struct.unpack_from("<I", data, text_offset + index)[0]
        if (word & 0x9F000000) != 0x90000000:
            continue

        immhi = (word >> 5) & 0x7FFFF
        immlo = (word >> 29) & 3
        immediate = sign_extend((immhi << 2) | immlo, 21)
        page = (address & ~0xFFF) + (immediate << 12)
        if page != target_page:
            continue

        tail = data[text_offset + index:text_offset + index + 32]
        rendered = " | ".join(
            f"{instruction.address:x}: {instruction.mnemonic} "
            f"{instruction.op_str}"
            for instruction in decoder.disasm(tail, address)
        )
        hits.append(rendered)

    print(f"total={len(hits)}")
    for hit in hits:
        print(hit)


if __name__ == "__main__":
    main()

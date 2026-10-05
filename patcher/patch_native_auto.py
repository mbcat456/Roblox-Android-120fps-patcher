import struct
import sys
from pathlib import Path

try:
    from capstone import (
        Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, CS_OP_IMM, CS_OP_MEM
    )
    from capstone.arm64 import ARM64_REG_X0
except ImportError:
    print("missing dependency: pip install capstone", file=sys.stderr)
    raise SystemExit(2)


ARM64_TEXT = None
ARM64_TEXT_SIZE = None


def executable_text_range(data: bytes):
    if data[:4] != b"\x7fELF" or data[4] != 2:
        raise RuntimeError("expected a 64-bit ELF")
    phoff = struct.unpack_from("<Q", data, 0x20)[0]
    phentsize = struct.unpack_from("<H", data, 0x36)[0]
    phnum = struct.unpack_from("<H", data, 0x38)[0]
    for index in range(phnum):
        offset = phoff + index * phentsize
        p_type, p_flags = struct.unpack_from("<II", data, offset)
        if p_type == 1 and p_flags & 1:
            return (
                struct.unpack_from("<Q", data, offset + 8)[0],
                struct.unpack_from("<Q", data, offset + 32)[0],
            )
    raise RuntimeError("no executable PT_LOAD segment")


def sign_extend(value: int, bits: int) -> int:
    sign = 1 << (bits - 1)
    return (value ^ sign) - sign


def adrp_target(data: bytes, address: int) -> tuple[int, int, int] | None:
    word = struct.unpack_from("<I", data, address)[0]
    if (word & 0x9F000000) != 0x90000000:
        return None
    register = word & 0x1F
    immhi = (word >> 5) & 0x7FFFF
    immlo = (word >> 29) & 3
    immediate = sign_extend((immhi << 2) | immlo, 21)
    page = (address & ~0xFFF) + (immediate << 12)
    return register, page, immediate


def add_low_target(data: bytes, address: int, register: int) -> int | None:
    word = struct.unpack_from("<I", data, address)[0]
    if (word & 0xFF000000) != 0x91000000:
        return None
    if (word & 0x1F) != register:
        return None
    register_base = (word >> 5) & 0x1F
    if register_base != register:
        return None
    return word >> 10 & 0xFFF


def disasm(data: bytes, start: int, length: int):
    decoder = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    decoder.detail = True
    return list(decoder.disasm(data[start:start + length], start))


def find_all(data: bytes, pattern: bytes):
    hits = []
    start = 0
    while True:
        offset = data.find(pattern, start)
        if offset < 0:
            return hits
        hits.append(offset)
        start = offset + 1


def patch_one(data: bytearray, offset: int, expected: bytes, replacement: bytes):
    actual = bytes(data[offset:offset + len(expected)])
    if actual == replacement:
        print(f"  already patched 0x{offset:x}")
        return False
    if actual != expected:
        raise RuntimeError(
            f"unexpected bytes at 0x{offset:x}: {actual.hex()} "
            f"(wanted {expected.hex()})"
        )
    data[offset:offset + len(replacement)] = replacement
    print(f"  patched 0x{offset:x}: {expected.hex()} -> {replacement.hex()}")
    return True


def find_string(data: bytes, value: str) -> int:
    offset = data.find(value.encode("ascii"))
    if offset < 0:
        raise RuntimeError(f"string not found: {value}")
    return offset


def adrp_xrefs(data: bytes, target_va: int):
    target_page = target_va & ~0xFFF
    text_offset, text_size = executable_text_range(data)
    decoder = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    decoder.detail = True
    hits = []
    for index in range(0, text_size - 32, 4):
        address = text_offset + index
        parsed = adrp_target(data, address)
        if parsed is None:
            continue
        _, page, _ = parsed
        if page != target_page:
            continue
        low = add_low_target(data, address + 4, parsed[0])
        if low is not None and target_page + low == target_va:
            hits.append(address)
            continue
        for instruction in decoder.disasm(
            data[address + 4:address + 40], address + 4
        ):
            for operand in instruction.operands:
                if operand.type == CS_OP_MEM:
                    if (
                        operand.mem.base == parsed[0] + ARM64_REG_X0
                        and operand.mem.disp == target_va & 0xFFF
                    ):
                        hits.append(address)
                        break
            else:
                continue
            break
    return hits


def data_refs(data: bytes, target_va: int):
    refs = []
    for address in adrp_xrefs(data, target_va):
        low = add_low_target(data, address + 4, adrp_target(data, address)[0])
        instructions = disasm(data, address, 32)
        refs.append((address, low, instructions))
    return refs


def derive_feature_global(data: bytes, feature: str) -> int:
    string_va = find_string(data, feature)
    for xref in adrp_xrefs(data, string_va):
        instructions = disasm(data, max(0, xref - 16), 112)
        for index, instruction in enumerate(instructions):
            if instruction.mnemonic != "adrp":
                continue
            parsed = adrp_target(data, instruction.address)
            if parsed is None:
                continue
            register, page, _ = parsed
            low = add_low_target(data, instruction.address + 4, register)
            if low is None:
                continue
            target = page + low
            for later in instructions[index + 1:index + 12]:
                if (
                    later.mnemonic == "strb"
                    and later.op_str.startswith("wzr, [")
                    and f"x{register}" in later.op_str
                ):
                    return target
    raise RuntimeError(f"could not derive global flag for {feature}")


def patch_feature_gates(data: bytearray, feature: str):
    print(f"[feature] {feature}")
    global_va = derive_feature_global(bytes(data), feature)
    print(f"  global=0x{global_va:x}")
    patched = 0

    for address, low, instructions in data_refs(bytes(data), global_va):
        if len(instructions) < 3:
            continue
        first = instructions[0]
        second = instructions[1]
        third = instructions[2]
        if first.mnemonic != "adrp":
            continue
        if second.mnemonic == "ldrb" and second.op_str.startswith("w0, ["):
            if len(instructions) > 2 and instructions[2].mnemonic == "ret":
                patch_one(
                    data,
                    address,
                    bytes(data[address:address + 8]),
                    bytes.fromhex("20008052C0035FD6"),
                )
                patched += 1
        if second.mnemonic == "ldrb" and second.op_str.startswith("w8, ["):
            if len(instructions) > 2 and instructions[2].mnemonic == "cbz":
                patch_one(
                    data,
                    second.address,
                    bytes(data[second.address:second.address + 4]),
                    bytes.fromhex("28008052"),
                )
                patched += 1
            if len(instructions) > 2 and instructions[2].mnemonic == "tbz":
                patch_one(
                    data,
                    address,
                    bytes(data[address:address + 12]),
                    bytes.fromhex("000F8052C0035FD61F2003D5"),
                )
                patched += 1

    print(f"  gate patches={patched}")
    return patched


def patch_policy_getter(data: bytearray, feature: str):
    print(f"[policy] {feature}")
    global_va = derive_feature_global(bytes(data), feature)
    for address, low, instructions in data_refs(bytes(data), global_va):
        if len(instructions) < 5:
            continue
        if (
            instructions[0].mnemonic == "adrp"
            and instructions[1].mnemonic == "adrp"
            and instructions[2].mnemonic == "ldrb"
            and instructions[3].mnemonic == "ldrb"
            and instructions[4].mnemonic == "cmp"
            and instructions[5].mnemonic == "csel"
        ):
            patch_one(
                data,
                address,
                bytes(data[address:address + 8]),
                bytes.fromhex("20008052C0035FD6"),
            )
            return 1
    raise RuntimeError(f"policy getter not found for {feature}")


def patch_arm64(data: bytearray):
    counts = {
        "resolution": 0,
        "scheduler_fallback": 0,
        "scheduler_interval": 0,
        "frm_initializer": 0,
        "frm_getter": 0,
        "property_getter": 0,
        "property_setter": 0,
    }

    resolution_hits = find_all(data, bytes.fromhex("201C201E"))
    if len(resolution_hits) == 1:
        offset = resolution_hits[0]
        patch_one(data, offset, bytes.fromhex("201C201E"),
                  bytes.fromhex("2040201E"))
        counts["resolution"] += 1
    else:
        print(f"  resolution candidates={len(resolution_hits)} (skipped)")

    scheduler_fallback_hits = find_all(
        data, bytes.fromhex("1F010071880780520001891A")
    )
    if len(scheduler_fallback_hits) == 1:
        offset = scheduler_fallback_hits[0]
        patch_one(
            data,
            offset,
            bytes.fromhex("1F010071880780520001891A"),
            bytes.fromhex("000F80521F2003D51F2003D5"),
        )
        counts["scheduler_fallback"] += 1
    else:
        print(
            f"  scheduler fallback candidates="
            f"{len(scheduler_fallback_hits)} (skipped)"
        )

    interval_hits = find_all(data, bytes.fromhex("28F2E7F2"))
    if len(interval_hits) == 1:
        offset = interval_hits[0]
        patch_one(data, offset, bytes.fromhex("28F2E7F2"),
                  bytes.fromhex("28F0E7F2"))
        counts["scheduler_interval"] += 1
    else:
        print(f"  interval candidates={len(interval_hits)} (skipped)")

    initializer_hits = []
    for offset in find_all(data, bytes.fromhex("88078052")):
        tail = bytes(data[offset + 4:offset + 20])
        if any(
            struct.unpack_from("<I", tail, i)[0] & 0x9F000000
            == 0x90000000
            for i in range(0, len(tail) - 3, 4)
        ):
            initializer_hits.append(offset)
    if len(initializer_hits) == 1:
        patch_one(data, initializer_hits[0], bytes.fromhex("88078052"),
                  bytes.fromhex("080F8052"))
        counts["frm_initializer"] += 1
    else:
        print(f"  FRM initializer candidates={len(initializer_hits)} (skipped)")

    frm_hits = find_all(data, bytes.fromhex("00994BB9"))
    if len(frm_hits) == 1:
        offset = frm_hits[0]
        patch_one(data, offset, bytes.fromhex("00994BB9"),
                  bytes.fromhex("000F8052"))
        counts["frm_getter"] += 1
    else:
        print(f"  FRM getter candidates={len(frm_hits)} (skipped)")

    property_hits = find_all(data, bytes.fromhex("004C41B9"))
    if len(property_hits) == 1:
        offset = property_hits[0]
        patch_one(data, offset, bytes.fromhex("004C41B9"),
                  bytes.fromhex("000F8052"))
        counts["property_getter"] += 1
    else:
        print(
            f"  FramerateCap getter candidates={len(property_hits)} (skipped)"
        )

    setter_hits = []
    for offset in find_all(data, bytes.fromhex("084C41B9")):
        tail = bytes(data[offset:offset + 20])
        store = tail.find(bytes.fromhex("014C01B9"))
        if store >= 0:
            setter_hits.append((offset, offset + store))
    if len(setter_hits) == 1:
        offset, store = setter_hits[0]
        patch_one(data, offset, bytes.fromhex("084C41B9"),
                  bytes.fromhex("080F8052"))
        patch_one(data, store, bytes.fromhex("014C01B9"),
                  bytes.fromhex("084C01B9"))
        counts["property_setter"] += 1
    else:
        print(f"  FramerateCap setter candidates={len(setter_hits)} (skipped)")

    patch_feature_gates(data, "GameBasicSettingsFramerateCap")
    patch_policy_getter(data, "ApplicationFrameRatePolicy")
    print(f"  fixed patterns={counts}")
    return sum(counts.values()) > 0


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: patch_native_auto.py LIBROBLOX_SO", file=sys.stderr)
        raise SystemExit(2)

    path = Path(sys.argv[1])
    data = bytearray(path.read_bytes())
    if path.as_posix().lower().find("arm64") >= 0:
        changed = patch_arm64(data)
    else:
        print("only arm64 automatic gate patching is supported", file=sys.stderr)
        raise SystemExit(2)
    path.write_bytes(data)
    print(f"wrote {path}, arm64_changed={changed}")


if __name__ == "__main__":
    main()

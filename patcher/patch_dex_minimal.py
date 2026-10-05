import argparse
import hashlib
import struct
import sys
import zipfile
import zlib
from pathlib import Path


TYPE_CODE_ITEM = 0x2001
TYPE_MAP_LIST = 0x1000

TARGETS = [
    ("Lnl/a;", "a", "(Landroid/view/Display;)F"),
]


def uleb(data, pos):
    result = 0
    shift = 0
    while True:
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if byte < 0x80:
            return result, pos
        shift += 7


def encode_uleb(value):
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def read_mutf8(data, off):
    pos = off
    _, pos = uleb(data, pos)
    end = data.index(b"\x00", pos)
    return data[pos:end].decode("utf-8", errors="replace"), end + 1


def read_dex(data):
    header_size = struct.unpack_from("<I", data, 0x24)[0]
    fields = struct.unpack_from("<20I", data, 0x20)
    names = (
        "file_size",
        "header_size",
        "endian_tag",
        "link_size",
        "link_off",
        "map_off",
        "string_ids_size",
        "string_ids_off",
        "type_ids_size",
        "type_ids_off",
        "proto_ids_size",
        "proto_ids_off",
        "field_ids_size",
        "field_ids_off",
        "method_ids_size",
        "method_ids_off",
        "class_defs_size",
        "class_defs_off",
        "data_size",
        "data_off",
    )
    header = dict(zip(names, fields))
    if header["endian_tag"] == 0x78563412:
        raise ValueError("reverse-endian DEX is not supported")
    if header["endian_tag"] != 0x12345678:
        raise ValueError("invalid DEX endian tag")
    if header["header_size"] < 0x70:
        raise ValueError("unsupported DEX header size")
    return header


def get_string(data, string_ids, index):
    off = struct.unpack_from("<I", data, string_ids + index * 4)[0]
    value, _ = read_mutf8(data, off)
    return value


def get_type_descriptors(data, header):
    out = []
    string_ids = header["string_ids_off"]
    type_ids = header["type_ids_off"]
    for i in range(header["type_ids_size"]):
        descriptor_idx = struct.unpack_from("<I", data, type_ids + i * 4)[0]
        out.append(get_string(data, string_ids, descriptor_idx))
    return out


def get_proto_descriptors(data, header):
    out = []
    string_ids = header["string_ids_off"]
    type_ids = header["type_ids_off"]
    proto_ids = header["proto_ids_off"]
    for i in range(header["proto_ids_size"]):
        shorty_idx, return_idx, params_off = struct.unpack_from(
            "<III", data, proto_ids + i * 12
        )
        params = []
        if params_off:
            size = struct.unpack_from("<I", data, params_off)[0]
            for j in range(size):
                type_idx = struct.unpack_from(
                    "<H", data, params_off + 4 + j * 2
                )[0]
                descriptor_idx = struct.unpack_from(
                    "<I", data, type_ids + type_idx * 4
                )[0]
                params.append(get_string(data, string_ids, descriptor_idx))
        return_descriptor_idx = struct.unpack_from(
            "<I", data, type_ids + return_idx * 4
        )[0]
        ret = get_string(data, string_ids, return_descriptor_idx)
        out.append(f"({''.join(params)}){ret}")
    return out


def get_method_names_and_protos(data, header):
    names = []
    protos = []
    string_ids = header["string_ids_off"]
    proto_table = get_proto_descriptors(data, header)
    method_ids = header["method_ids_off"]
    for i in range(header["method_ids_size"]):
        _, proto_idx, name_idx = struct.unpack_from(
            "<HHI", data, method_ids + i * 8
        )
        names.append(get_string(data, string_ids, name_idx))
        protos.append(proto_table[proto_idx])
    return names, protos


def find_class(data, header, descriptors, wanted):
    string_ids = header["string_ids_off"]
    class_defs = header["class_defs_off"]
    type_ids = header["type_ids_off"]
    for i in range(header["class_defs_size"]):
        class_idx = struct.unpack_from("<I", data, class_defs + i * 32)[0]
        descriptor_idx = struct.unpack_from(
            "<I", data, type_ids + class_idx * 4
        )[0]
        descriptor = get_string(data, string_ids, descriptor_idx)
        if descriptor == wanted:
            return i
    raise ValueError(f"class not found: {wanted}")


def parse_class_data(data, header, class_idx, method_names, protos):
    class_defs = header["class_defs_off"] + class_idx * 32
    class_data_off = struct.unpack_from("<I", data, class_defs + 24)[0]
    if not class_data_off:
        return []
    pos = class_data_off
    static_fields_size, pos = uleb(data, pos)
    instance_fields_size, pos = uleb(data, pos)
    direct_methods_size, pos = uleb(data, pos)
    virtual_methods_size, pos = uleb(data, pos)

    for _ in range(static_fields_size):
        _, pos = uleb(data, pos)
        _, pos = uleb(data, pos)
    for _ in range(instance_fields_size):
        _, pos = uleb(data, pos)
        _, pos = uleb(data, pos)

    methods = []
    method_idx = 0
    for _ in range(direct_methods_size):
        diff, pos = uleb(data, pos)
        access_flags, pos = uleb(data, pos)
        code_start = 0
        code_off = 0
        if not (access_flags & 0x500):
            code_start = pos
            code_off, pos = uleb(data, pos)
        method_idx += diff
        if method_idx >= len(method_names):
            continue
        methods.append(
            (
                method_idx,
                code_start,
                (pos - code_start) if code_start else 0,
                code_off,
            )
        )

    method_idx = 0
    for _ in range(virtual_methods_size):
        diff, pos = uleb(data, pos)
        access_flags, pos = uleb(data, pos)
        code_start = 0
        code_off = 0
        if not (access_flags & 0x500):
            code_start = pos
            code_off, pos = uleb(data, pos)
        method_idx += diff
        if method_idx >= len(method_names):
            continue
        methods.append(
            (
                method_idx,
                code_start,
                (pos - code_start) if code_start else 0,
                code_off,
            )
        )

    return [
        (
            method_names[idx],
            protos[idx],
            code_start,
            code_len,
            code_off,
        )
        for idx, code_start, code_len, code_off in methods
        if code_off
    ]


def find_method(data, header, class_idx, wanted_name, wanted_proto):
    names, protos = get_method_names_and_protos(data, header)
    for name, proto, code_start, code_len, code_off in parse_class_data(
        data, header, class_idx, names, protos
    ):
        if name == wanted_name and proto == wanted_proto:
            return code_start, code_len, code_off
    raise ValueError(
        f"method not found in {header['class_defs_size']}: "
        f"{wanted_name}{wanted_proto}"
    )


def read_code_item(data, code_off):
    registers, ins, outs, tries, debug_off, insns_size = struct.unpack_from(
        "<HHHHII", data, code_off
    )
    insns = data[code_off + 16 : code_off + 16 + insns_size * 2]
    return {
        "registers": registers,
        "ins": ins,
        "outs": outs,
        "tries": tries,
        "debug_off": debug_off,
        "insns_size": insns_size,
        "insns": insns,
    }


def patch_map_code_item_count(data, header, increment):
    map_off = header["map_off"]
    size = struct.unpack_from("<I", data, map_off)[0]
    found = False
    for i in range(size):
        entry = map_off + 4 + i * 12
        item_type, _, item_size, _ = struct.unpack_from(
            "<HHII", data, entry
        )
        if item_type == TYPE_CODE_ITEM:
            struct.pack_into("<I", data, entry + 4, item_size + increment)
            found = True
    if not found:
        raise ValueError("code_item map entry not found")


def patch_dex(stock, reference):
    data = bytearray(stock)
    header = read_dex(data)
    ref_data = reference
    ref_header = read_dex(ref_data)

    descriptors = get_type_descriptors(data, header)
    ref_descriptors = get_type_descriptors(ref_data, ref_header)

    patches = []
    new_items = []
    for descriptor, method, proto in TARGETS:
        class_idx = find_class(data, header, descriptors, descriptor)
        code_start, code_len, code_off = find_method(
            data, header, class_idx, method, proto
        )

        ref_class_idx = find_class(
            ref_data, ref_header, ref_descriptors, descriptor
        )
        _, _, ref_code_off = find_method(
            ref_data, ref_header, ref_class_idx, method, proto
        )
        item = read_code_item(ref_data, ref_code_off)
        item["debug_off"] = 0
        item["tries"] = 0
        new_items.append(item)
        patches.append((code_start, code_len, code_off))

    base = header["data_off"] + header["data_size"]
    new_code_offs = []
    for item in new_items:
        base = (base + 3) & ~3
        new_code_offs.append(base)
        size = 16 + len(item["insns"])
        if len(data) < base + size:
            data.extend(b"\x00" * (base + size - len(data)))
        struct.pack_into(
            "<HHHHII",
            data,
            base,
            item["registers"],
            item["ins"],
            item["outs"],
            0,
            0,
            item["insns_size"],
        )
        data[base + 16 : base + 16 + len(item["insns"])] = item["insns"]
        base += size

    new_data_end = base
    new_data_size = new_data_end - header["data_off"]
    new_file_size = new_data_end

    for (code_start, code_len, old_code_off), new_code_off in zip(
        patches, new_code_offs
    ):
        encoded = encode_uleb(new_code_off)
        if len(encoded) != code_len:
            raise ValueError(
                f"code_off ULEB length changed at {code_start:#x}: "
                f"{code_len} -> {len(encoded)}"
            )
        data[code_start : code_start + code_len] = encoded

    patch_map_code_item_count(data, header, len(new_items))
    struct.pack_into("<I", data, 0x68, new_data_size)
    struct.pack_into("<I", data, 0x20, new_file_size)

    signature = hashlib.sha1(data[32:]).digest()
    data[12:32] = signature
    checksum = zlib.adler32(data[12:]) & 0xFFFFFFFF
    struct.pack_into("<I", data, 8, checksum)

    return bytes(data), {
        "old_file_size": len(stock),
        "new_file_size": new_file_size,
        "appended_code_items": len(new_items),
        "code_offsets": new_code_offs,
    }


def load_zip_entry(path, name):
    with zipfile.ZipFile(path) as zf:
        return zf.read(name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stock_apk")
    parser.add_argument("reference_apk")
    parser.add_argument("output_dex")
    args = parser.parse_args()

    stock = load_zip_entry(args.stock_apk, "classes2.dex")
    reference = load_zip_entry(args.reference_apk, "classes2.dex")
    patched, summary = patch_dex(stock, reference)
    output = Path(args.output_dex)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(patched)
    print(summary)


if __name__ == "__main__":
    main()

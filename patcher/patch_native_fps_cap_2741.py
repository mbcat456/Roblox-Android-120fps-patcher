import sys
from pathlib import Path


def apply(path: Path, patches):
    data = bytearray(path.read_bytes())
    for offset, expected_hex, replacement_hex in patches:
        expected = bytes.fromhex(expected_hex)
        replacement = bytes.fromhex(replacement_hex)
        current = data[offset:offset + len(expected)]
        if current == replacement:
            print(f"already patched {path} at 0x{offset:x}")
            continue
        if current != expected:
            raise RuntimeError(
                f"unexpected bytes at 0x{offset:x}: {current.hex()}"
            )
        data[offset:offset + len(replacement)] = replacement
        print(
            f"patched {path} at 0x{offset:x}: "
            f"{expected.hex()} -> {replacement.hex()}"
        )
    path.write_bytes(data)


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: patch_native_fps_cap_2741.py ELF_PATH", file=sys.stderr)
        raise SystemExit(2)

    path = Path(sys.argv[1])
    lower = path.as_posix().lower()
    if "arm64" in lower:
        patches = [
            # High-DPI framebuffer final selection: force scale 1.0.
            (0x283122C, "201C201E", "2040201E"),
            # TaskScheduler target-FPS zero fallback: 60 -> 120.
            (
                0x24203EC,
                "1F010071880780520001891A",
                "000F80521F2003D51F2003D5",
            ),
            # TaskScheduler constructor default interval: 1/60 -> 1/120.
            (0x22B2BEC, "28F2E7F2", "28F0E7F2"),
            # FRM target global initializer: 60 -> 120.
            (0x1E6FF5C, "88078052", "080F8052"),
            # FRM getter: return 120.
            (0x2F3CBE4, "00994BB9", "000F8052"),
            # FramerateCap property getter: return 120.
            (0x44577D8, "004C41B9", "000F8052"),
            # FramerateCap property setter: store 120.
            (0x44C31E8, "084C41B9", "080F8052"),
            (0x44C31F4, "014C01B9", "084C01B9"),
            # GameBasicSettingsFramerateCap engine feature callback:
            # always return true so the settings page and native setup path
            # take the official framerate-cap flow.
            (0x2E06E50, "48F001D000416E39", "20008052C0035FD6"),
            # Native startup gate that skipped the ApplicationFrameRate
            # setup block whenever the feature byte was false.
            (0x22C7D00, "08416E39", "28008052"),
            # GetDefaultFramerateCap reflection wrapper: return 120 instead
            # of raising "GetDefaultFramerateCap() is not enabled."
            (0x4609B04, "283001F008416E3948000036",
             "000F8052C0035FD61F2003D5"),
            # ApplicationFrameRatePolicy engine feature getter: return true
            # so the policy path is selected rather than the 60 Hz fallback.
            (0x6383D68, "C851009009680090", "20008052C0035FD6"),
        ]
    elif "armeabi" in lower:
        patches = [
            # TaskScheduler constructor default interval: 1/60 -> 1/120.
            (0x2AEA7CA, "C3F69170", "C3F68170"),
            # TaskScheduler target-FPS zero fallback: 60 -> 120.
            (0x2BEB2B8, "002908BF3C20", "782000BF00BF"),
            # High-DPI framebuffer scale: 0.5 -> 1.0.
            (0x2EE3766, "B6EE001A", "B7EE001A"),
            # FRM getter: return 120 instead of the table value at +0x48.
            (0x13E3ED0, "01487844806C7047", "7820704700000000"),
        ]
    elif "x86_64" in lower:
        patches = [
            # TaskScheduler constructor default interval: 1/60 -> 1/120.
            (
                0x237135F,
                "48B8111111111111913F",
                "48B8111111111111813F",
            ),
            # TaskScheduler target-FPS zero fallback: 60 -> 120.
            (0x24FE959, "B83C0000000F45C1", "B878000000909090"),
            # High-DPI framebuffer blend: force the 1.0 scale lane.
            (
                0x29792AC,
                "0F28D084C97508F30F1015D5F3C2FD"
                "F30F101D8DF4C2FDF30FC2D9060F28CB"
                "0F55CA0F54D80F56D9",
                "0F28D8" + "90" * 37,
            ),
            # FRM target global initializer: 60 -> 120.
            (
                0x1E58EF1,
                "C7052D614E053C000000",
                "C7052D614E0578000000",
            ),
            # GameBasicSettingsFramerateCap engine feature callback.
            (0x28941F3, "8A057F99A904C3", "B001C390909090"),
            # Native flag check that selects the primary frame-rate path.
            (0x2370118, "4C0F44C8", "0F1F4000"),
        ]
    else:
        raise RuntimeError("only arm64, armeabi-v7a, and x86_64 are supported")

    apply(path, patches)


if __name__ == "__main__":
    main()

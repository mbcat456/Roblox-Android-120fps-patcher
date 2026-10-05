# Zero-Data Native Labels

This report classifies the Ghidra function-index entries that lie outside
the executable first-load segment. They are not real engine functions.

## Counts

```text
abi           total index   outside segment   FUN_ labels   external labels
arm64-v8a         171127              3601          2457             1144
x86_64            111115              2505          1424             1081
armeabi-v7a       151161              1236           168             1068
```

The arm64 number matches the 3,601-item residual gap in the coverage matrix.

## Composition

- `FUN_*` labels are bogus function objects that Ghidra inferred from
  relocations, padding, or imported-code stubs outside the loaded image.
- The remaining entries are external-library symbols (`pthread_*`, `gl*`,
  `egl*`, `AMedia*`, libc/stdio/math/socket functions, and `__*` runtime
  helpers) that Ghidra recorded in the same synthetic address space.

The labels are harmless loader/decompiler artifacts. They do not hide an
unpacked code block or an encrypted payload; the executable segment itself is
fully indexed and decompiled.

Summary artifact:

```text
analysis/docs/artifacts/zero_data_labels_summary.tsv
```

This closes the zero-data-label portion of `09_COVERAGE.md`; the labels are
classified rather than left as an unexplained count.

# Native Recovery Guide

## Naming Conventions

Ghidra names are derived from the stripped symbol table:

- `Java_*` - exported JNI entry points, joined to Java declarations in
  `analysis/maps/jni_bridge_master.csv`
- `FUN_<hex>` - internal function discovered by control-flow analysis
- `_INIT_<n>` - static initializer produced by the compiler
- `thunk_FUN_*` - PLT/GOT indirection thunks
- imported names such as `memcpy`, `strlen`, `pthread_mutex_lock` - external
  symbols from the ELF import table
- labels such as `DAT_`, `UNK_`, `PTR_`, `s_` - data/string references

Functions in `libroblox.so_functions.json` outside the executable first-load
segment (above `0x62d8190`) are zero-data artifacts, not executable code.

## Reading The Chunked C

The full output is:

```text
analysis/native/arm64-v8a/libroblox/libroblox.so_decompiled/
  libroblox.so_part_0001.c ...
  libroblox.so_index.csv
```

Every function starts with:

```c
/* Function: NAME @ ADDRESS size=BYTES */
```

The Java JNI bridge is extracted into `libroblox_jni_annotated.c`, where each
function is prefixed with its original Java class, method, signature, and ELF
address.

`libroblox.so_functions.json` carries each function's incoming/outgoing calls,
size, and source type. `libroblox.so_calls.json` is the complete call graph,
and `libroblox_arm64_full_function_index.csv` is the one-row-per-function
searchable index.

## Renaming Strategy

1. Resolve JNI functions first from `jni_bridge_master.csv`.
2. Use imported APIs to classify leaf helpers.
3. Follow the `most_called` list in `libroblox_arm64_profile.json`; the
   top hubs are allocator/refcount/string routines used throughout the
   engine.
4. Match function-contained constants against `libroblox.so_strings.json`
   and the categorized string index.
5. Use TeamCity source paths from
   `analysis/maps/native/native_source_paths_unique.txt` to name the
   corresponding modules.

## Expected Recovery Cost

The engine is normal stripped C++ rather than bytecode-protected code. The
remaining work is mechanical renaming/type recovery, not decryption or
devirtualization. The decompiler occasionally reports
`VarnodeContext: out of address spaces` on generated protobuf/reflection
functions; those can be reconstructed from the address-level disassembly and
the surrounding call graph.

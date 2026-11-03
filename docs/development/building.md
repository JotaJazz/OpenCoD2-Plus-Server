# Building

User-facing build instructions are in the [README](../../README.md#building).
This page covers what a contributor needs on top.

## Variants

| Command | Output |
|---|---|
| `make` | Linux 64-bit, 1.0 (protocol 115) → `bin/cod2rev_lnxded` |
| `make PROTOCOL=118` | Linux 64-bit, 1.3 → same name in `bin/` |
| `make ARCH=x86` | Linux 32-bit ([ADR 0010](../architecture/adr/0010-64-bit-default-on-linux.md)); combines with `PROTOCOL=118` → same name in `bin/` |
| `make ARCH=arm64` | Linux aarch64, experimental ([ADR 0013](../architecture/adr/0013-arm64-linux-build.md)), built natively on the ARM host → same name in `bin/` |
| `make PLUS=1` | CoD2 1.3 Plus: the 1.3 build with `COD2_PLUS`, only for the Plus client ([ADR 0015](../architecture/adr/0015-plus-as-a-build-variant.md)); combines with `ARCH` and `windows` → same name in `bin/` |
| `make windows` | MinGW cross-build → `bin/cod2rev_win32.exe` (`PROTOCOL=118` for 1.3) |
| `make BIN_DIR=<folder>` | Same build into another folder, to keep 1.0 and 1.3 side by side |
| `make clean` | Removes the binary and the objects |

- Objects go to `obj/<binary>_<protocol>` (`_x64` or `_arm64` added for 64-bit, `_plus` for `PLUS=1`), so
  switching platform, version or architecture does not rebuild everything;
  the binary name in `bin/` is shared.
- The 32-bit Linux build needs `gcc-multilib` and `g++-multilib`, the
  64-bit one only the usual `gcc`/`g++`; Windows needs the posix
  thread variant of MinGW-w64 (`i686-w64-mingw32-gcc-posix`; Debian/Ubuntu
  package `gcc-mingw-w64-i686-posix`).
- `-D LIBCOD` and the `LIBCOD_COMPILE_*` switches are on by default (see the
  README's Makefile options). Code differs between `#ifdef LIBCOD` and the
  stock path, and between `PROTOCOL_VERSION` 115 and 118: check both sides of
  an `#if`. `make WITH_LIBCOD=false` uses the same `obj/` folder, so delete
  `obj/cod2rev_lnxded_115` before and after it, or stale objects fail to link.
- Hardening flags are on in every Makefile build: `-fstack-protector-strong`,
  `-D_FORTIFY_SOURCE=2`, `-fno-strict-aliasing`, `-fwrapv`, full RELRO on
  Linux. The reversed code relies on `-fno-strict-aliasing` and `-fwrapv`. A
  command-line `CFLAGS`/`LFLAGS`, as in the ASan build below, replaces them.
- Known warnings: four (`-Wwrite-strings`, `-Wmultichar`) in reversed files;
  new code adds none. The 64-bit build adds about 15 `-Wformat` ones in
  reversed files (a pointer difference printed with `%d`/`%i`); harmless on
  x86-64, where each variadic argument has its own 8-byte slot, and kept as
  upstream has them.

## Before committing a change under src/

1. `make`, `make PROTOCOL=118` and `make PLUS=1`; `make ARCH=x86` for changes
   that touch pointers, sizes or the Makefile. Read both sides of
   `#ifdef COD2_PLUS`.
2. `make windows`.
3. The smoke test for 1.0, 1.3 and 1.3 Plus ([testing.md](testing.md)).
4. For memory-sensitive changes, an ASan run with bots.

CI (`.github/workflows/build.yml`) builds the seven variants (Linux 32 and
64-bit, Windows, each for 1.0 and 1.3, and 1.3 Plus on Linux 64-bit) on pushes
to `master` and `dev` and on pull requests that change `src/`, the `Makefile` or the
workflow, and on a manual run (`workflow_dispatch`).

## MySQL

`make WITH_MYSQL=true` builds the MySQL script functions against the
system's client library: MariaDB Connector/C (`libmariadb-dev`) or MySQL's
(`libmysqlclient-dev`), found with `mariadb_config` or `mysql_config`.
Distributions ship it 64-bit only. `MYSQL_LIBS=-l:libmariadb.so.3` links
against the runtime package alone. The binary needs the library where it
runs, so CI builds it (job `mysql`) but does not publish it. Use other
`OBJ_ROOT`/`BIN_DIR` folders: libcod objects differ with `WITH_MYSQL`.
`docs/superpowers/harness/t_mysql.py` (local) tests it against a server with
database `cod2test` and user `cod2`. Scripts need `+set sv_libcodUnsafe 1`.

## AddressSanitizer build

A command-line `CFLAGS` replaces the Makefile's, so `-m64` and
`-D_FILE_OFFSET_BITS=64` must be repeated:

```bash
make OBJ_ROOT=<scratch>/asan_obj BIN_DIR=<scratch>/asan_bin \
  CFLAGS="-fno-pie -O1 -g -fno-omit-frame-pointer -mfpmath=387 -DNDEBUG -DPROTOCOL_VERSION=115 -MMD -MP -m64 -D_FILE_OFFSET_BITS=64 -fsanitize=address" \
  LFLAGS="-no-pie -m64 -fsanitize=address"
```

Use `-DPROTOCOL_VERSION=118` and other folders for 1.3. For 32-bit add
`ARCH=x86` and write `-m32` instead of `-m64` in both.

## Line endings

`.gitattributes` is `* -text`: git never converts line endings. Most files
under `src/` are CRLF; `src/libcod/*`, `src/qcommon/msg_mp.cpp`,
`src/qcommon/qcommon.h`, the scripts and the docs are LF. Keep each file's
endings (`grep -c $'\r' <file>` counts CR lines). An editor that converts a
file makes the whole file a diff and a conflict with upstream.

## Code style

Quake 3 style in `src/`: tabs, braces on their own line, and a comment block
with the function name between `=====` lines above each function. Comments only where the reason is not
obvious. Python scripts: 4 spaces, standard library only, a module
docstring with the usage line.

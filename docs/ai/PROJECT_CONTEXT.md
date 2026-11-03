# Project context

## Identity

OpenCoD2-Plus Server: a fork of
[voron00/CoD2rev_Server](https://github.com/voron00/CoD2rev_Server), the
reverse-engineered source of the Call of Duty 2 multiplayer dedicated server
(1.0 and 1.3). Maintained by one person for running their own servers, with
an AI assistant; AGPL-3.0.

## Goal

A dedicated server that stock CoD2 clients join unchanged, more robust than
the original binaries, with a script layer (libcod) rich enough for modern
server mods.

## Non-goals

- A game client or any client-side change; client prediction stays intact.
- Reverse-engineering the engine: that happens upstream. The fork reverses
  only what a fix or feature needs (for example the client calls of `LISTEN_SERVER`).
- Distributing game files (iwds, stock scripts).
- Sending changes back upstream.
- Protocols or features that need a modified client (CoD2x API), except the
  CoD2 Plus protocol of the `make PLUS=1` build
  ([ADR 0015](../architecture/adr/0015-plus-as-a-build-variant.md)).

## Principles

- Compatibility with stock clients first.
- Reversed code mirrors the binary; fork features live in `src/libcod`.
- Everything is verified on the real server: builds for both platforms and
  versions, tests against a real game folder.
- One self-contained binary: vendored libraries; on Linux only libc, libm,
  pthread, libdl and libstdc++ at run time.
- Script-facing names follow zk_libcod.

## Stack

C++ (C-style, Quake 3 code base), x86-64 by default on Linux, 32-bit x86 as an option and on Windows, GNU Make,
MinGW-w64 for Windows; GSC for the bots mod; Python 3 (standard library) for
tools and tests; GitHub Actions for builds.

## Constraints

- 64-bit is the Linux default and 32-bit the only Windows build; both keep
  the same network formats ([ADR 0010](../architecture/adr/0010-64-bit-default-on-linux.md)).
- Fixed engine limits (`MAX_CLIENTS` 64, `MAX_GENTITIES` 1024) and wire formats.
- Tests need a CoD2 install, which is not in the repository.
- Protocol 119 (Game Pass) cannot be tested.

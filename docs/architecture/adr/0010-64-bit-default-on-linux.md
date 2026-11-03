# 0010. 64-bit is the default Linux build

- Status: Accepted; its x87 math superseded by [0017](0017-sse2-math.md)
- Date: 2026-10-31

## Context

[ADR 0009](0009-linux-64-bit-build.md) added `ARCH=x64` and kept 32-bit as the
default so nothing changed for existing builds. Forcing `-m32` was a
maintainer's early choice, not a need: upstream builds natively, new hosts
lack `gcc-multilib`, and MySQL client libraries ship 64-bit only.

## Decision

`make` on Linux builds 64-bit. `make ARCH=x86` builds the 32-bit binary, which
stays supported and built by CI. Windows stays 32-bit, so `ARCH` defaults to
`x86` there. Math stays on x87 (`-mfpmath=387`) on both.

## Consequences

- `make` needs only `gcc` and `g++`.
- CI artifact names follow the default: `cod2rev_lnxded-1.0` is now 64-bit and
  the 32-bit one is `cod2rev_lnxded-1.0-x86` (same for 1.3).
- Graph files move between both builds. `memory_*` builtins return 64-bit
  addresses, so mods written for 32-bit offsets need `ARCH=x86`.
- Crash reports from the default build show `rip`.

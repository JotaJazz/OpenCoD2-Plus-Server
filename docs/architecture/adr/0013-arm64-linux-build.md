# 0013. Experimental arm64 Linux build

- Status: Accepted
- Date: 2026-11-02

## Context

Small hosts such as a Raspberry Pi 3, 4 or 5 run 64-bit ARM Linux. The engine
has almost no x86 code left: the crash handler and the FPU setup have generic
paths and `sse_mathfun.h` is only used with `USE_SSE2`. What ties the build to
x86 is the Makefile: `-mfpmath=387`, `-m32`/`-m64`, and the math, which stays
on x87 to round as the original binary does ([ADR 0010](0010-64-bit-default-on-linux.md)).
ARM has no x87, and its `char` is unsigned where the reversed code expects
x86's signed one.

## Decision

`make ARCH=arm64` builds a native aarch64 binary. It drops `-mfpmath=387` and
adds `-fsigned-char`, and `-ffp-contract=off` so GCC does not fuse multiplies
and adds, which rounds differently again. It is experimental: not the default,
not built by CI, and 32-bit ARM (armhf) is not supported.

## Consequences

- Under qemu the smoke test and the bots test pass on 1.0. Bringing it up found
  one real bug, a dvar buffer that the order of `printf` arguments exposed.
- Floats round as IEEE single and double instead of x87's extended precision,
  so player movement and hit locations can differ from the original in the
  last bit. Until real clients have played on an arm64 server it is not for
  competitive play ([../../roadmap/debt.md](../../roadmap/debt.md)).
- Behaviour that C leaves undefined and x86 and ARM resolve differently
  (out-of-range float to int conversions, shifts of 32 bits or more) could
  still hide in the reversed code; tests are the only way to find it.
- Crash reports show only the fault address, not the program counter.

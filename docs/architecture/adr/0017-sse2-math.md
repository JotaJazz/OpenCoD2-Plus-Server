# 0017. Float math on SSE2, not x87

- Status: Accepted
- Date: 2026-11-03

## Context

The x86 and x64 builds forced `-mfpmath=387` so that float math would round as
the original binary does ([ADR 0010](0010-64-bit-default-on-linux.md)). That
assumed the original ran x87 at its default precision. It does not: the 1.3
client sets x87 to 24 bits at start (`_controlfp(_PC_24, _MCW_PC)` in
`Sys_CreateConsole`, in OpenCoD2-Plus's reconstruction of the binary), and that
client is what predicts the player's movement. This server ran x87 with a
64-bit mantissa on Linux, so it already rounded otherwise, and the results of
x87 code also depend on when the compiler spills a register to memory.
Upstream moved to SSE in `8319e9b`, and the arm64 build, which rounds as SSE
does, played without a difference a player could notice
([ADR 0013](0013-arm64-linux-build.md)).

## Decision

Every x86 and x64 build, Windows included, compiles with `-msse2
-mfpmath=sse`: float operations round to single precision at each step, as the
client's 24-bit x87 does, and doubles to double. `USE_SSE2` stays off, so
upstream's vector approximations of `sin` and `cos` (`sse_mathfun.h`, `I_sin`)
and its float math helpers are not used. arm64 already rounds this way.

## Consequences

- Movement, hit locations and every other float result can change in the last
  bit on every build. That is a change of client-predicted behaviour, accepted
  here because it moves the server towards the client's rounding.
- Results no longer depend on register allocation, and the x86, x64 and arm64
  builds round the same way, apart from undefined behaviour in reversed code.
- The 32-bit builds need an SSE2 CPU (Pentium 4, Athlon 64 and later).
- Only `Q_vsnprintf`'s `long double` formatting still uses x87 instructions.
- Doubles in the reversed code are computed as doubles; with x87 at 24 bits
  the client rounds them to single precision. Where that matters, the fix is to
  follow 1.3's float constants, as was done for the player controllers.

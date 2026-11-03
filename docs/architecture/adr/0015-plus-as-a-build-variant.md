# 0015. CoD2 1.3 Plus is a build variant, not a branch

- Status: Accepted
- Date: 2026-11-02

## Context

[ADR 0012](0012-plus-leaves-1-3-out.md) put Plus on its own `plus` branch so
that `master`'s builds kept the stock formats. Every fix then went from
`master` to `plus` by a merge, and the two lines differed in about 110 lines of
code, most of them already behind `#if PROTOCOL_VERSION == 118`. The
maintainer wants a single line of development.

## Decision

`make PLUS=1` builds the CoD2 1.3 Plus server: a 1.3 build with `COD2_PLUS`
defined. Everything Plus changes sits behind `#ifdef COD2_PLUS`: the handshake,
the notice and `sv_plusNotice`, the Plus snapshot, script time and
`trDuration` that follow `sv_fps`, and the raised `g_forceRate` and
`g_forceSnaps` caps. Without it the code is the stock one. `plus` is merged
into `master` and retired; work goes on `dev` and reaches `master` for a
release. What ADR 0012 decided for a Plus server (only the Plus client, 40–60
Hz) holds for this build.

## Consequences

- Every build but `PLUS=1` keeps the stock formats, limits and prediction: on
  the day of the change the 1.0 and 1.3 x64 objects were byte for byte
  `master`'s, apart from the build time in `unix_main.o`.
- One more build to check before a commit under `src/`, and its smoke run
  (`scripts/smoke_test.py --plus`); CI builds it as `cod2rev_lnxded-1.3-plus`.
- Both sides of `#ifdef COD2_PLUS` have to be read in review.
- OpenCoD2-Plus vendors one line of this repository instead of two; how it
  follows is decided in that repository.
- The rejected mode of ADR 0012, one binary serving stock and Plus clients,
  stays rejected: each binary has one format.

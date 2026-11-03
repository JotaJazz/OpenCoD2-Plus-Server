# AGENTS.md

OpenCoD2-Plus Server: reverse-engineered Call of Duty 2 dedicated server (1.0 and
1.3), C++, 64-bit on Linux with a 32-bit build, 32-bit on Windows. A fork of
voron00/CoD2rev_Server that adds hardening, admin features, libcod script
functions and a bots mod.

## Read first

1. [docs/ai/README_AI.md](docs/ai/README_AI.md), then the files it lists in order.
2. For a change in an area: its page under [docs/architecture/](docs/architecture/overview.md).
3. Before building or testing: [docs/development/](docs/development/building.md).

## Hard rules

- Reversed code mirrors the original binary; change only what a fix needs,
  and explain the original bug in the commit.
- Script extensions go in `src/libcod`, attached with `#ifdef LIBCOD` hooks;
  hardening and admin fixes are small changes in the engine file they fix.
- Check both sides of `#ifdef LIBCOD`, of `#if PROTOCOL_VERSION` and of
  `#ifdef COD2_PLUS`; build `make`, `make PROTOCOL=118`, `make PLUS=1`,
  `make windows` and `make ARCH=x86` before committing under `src/`.
- Never change network formats, engine limits or client-predicted behaviour
  outside `#ifdef COD2_PLUS`. The `make PLUS=1` build serves only the CoD2 1.3
  Plus client and may change them
  ([ADR 0015](docs/architecture/adr/0015-plus-as-a-build-variant.md)).
- Keep each file's line endings (`.gitattributes` is `* -text`).
- Do not edit vendored libraries; do not add runtime dependencies.
- Tests need a CoD2 folder with only stock iwds; stop test servers by their PID
  or `pkill -x cod2rev_lnxded`, never `pkill -f`.
- Commit locally; push only when the maintainer asks. Commit messages:
  imperative subject, a body with the why, and a `Co-Authored-By: Claude`
  line for AI-assisted commits.
- Never commit `CLAUDE.md`, `docs/superpowers/`, `.superpowers/` or `.claude/`.

## Doc-sync

- A change that makes a document wrong updates it in the same commit; the
  table is in [docs/ai/DEVELOPMENT_GUIDE.md](docs/ai/DEVELOPMENT_GUIDE.md#doc-sync).
- User-visible changes get a `docs/CHANGES.md` entry; the six READMEs change
  only when a milestone summary changes.
- Finished work adds a stage to [docs/ai/PROJECT_MEMORY.md](docs/ai/PROJECT_MEMORY.md).
- Run `python3 scripts/check_docs.py` before committing documentation.

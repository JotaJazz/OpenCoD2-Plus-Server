# Development guide

Commands: [../development/building.md](../development/building.md),
[../development/testing.md](../development/testing.md).

## Workflow

1. Work on a local branch from `dev`, in batches of related commits.
2. Verify each batch: `make`, `make PROTOCOL=118`, `make PLUS=1`,
   `make windows`, `make ARCH=x86`, smoke test
   on 1.0, 1.3 and 1.3 Plus (`--plus`); bots tests and ASan for gameplay or
   memory changes; `scripts/check_docs.py` when docs changed.
3. Merge to `dev` by fast-forward after the maintainer approves; `dev` reaches
   `master` for a release. Push only
   when asked: CI runs on pushes to `master` and `dev` and on pull requests that touch
   `src/`, the `Makefile` or the workflow.
4. Watch the CI run after a push.

## Commits

- Imperative subject, about 50–70 characters.
- The body explains the bug or need and why the change is right, not a list
  of edits.
- AI-assisted commits end with a `Co-Authored-By: Claude` line; the READMEs'
  Transparency section relies on it.
- Never commit `CLAUDE.md`, `docs/superpowers/`, `.superpowers/`, `.claude/`
  (local, listed in `.git/info/exclude`).

## Quality bars

- No new compiler warnings.
- Both versions, both platforms build.
- No ASan reports in a bots run for memory-related changes.
- Tests that a change could break are run, and their results reported as they
  are.

## Recipes

| Task | Steps |
|---|---|
| Add a GSC builtin | Implement in the matching `src/libcod/gsc_*.cpp`, declare in its `.hpp`, add to `scriptFunctions` or `scriptMethods` in `src/libcod/gsc.cpp`; validate arguments; state in `libcodClients`/`libcodEntities`; `docs/CHANGES.md` entry |
| Add a dvar | Register with range and default; `python3 scripts/gen_server_cfg.py`; row in the "New variables" table of `docs/CHANGES.md` |
| Fix reversed code | Smallest change; both `#if` sides; commit body with the original bug |
| Add a vendored library | New folder under `src/libcod`, `WITH_*` switch in the Makefile, own config file; ask the maintainer first |
| Merge upstream | [../development/upstream-sync.md](../development/upstream-sync.md) |
| Record a decision | New ADR from the template in [../architecture/adr/README.md](../architecture/adr/README.md) |

## Doc-sync

A change that makes a document wrong updates it in the same commit.

| When you change | Update |
|---|---|
| Anything user-visible | `docs/CHANGES.md`; the six READMEs only if a milestone line changes |
| A dvar | `scripts/server.cfg.example` (generator), CHANGES.md variables table |
| Module layout, a file named in docs | [../architecture/overview.md](../architecture/overview.md), README "Repository layout" (six languages) |
| A rule or exception | [../architecture/boundaries.md](../architecture/boundaries.md), [ARCHITECTURE_NOTES.md](ARCHITECTURE_NOTES.md) |
| libcod state, hooks or VM facts | [../architecture/libcod.md](../architecture/libcod.md) |
| Network code | [../architecture/networking.md](../architecture/networking.md) |
| Build or test scripts | [../development/](../development/building.md), [SYSTEM_SUMMARY.md](SYSTEM_SUMMARY.md) commands |
| A known risk or gap, fixed or found | [../roadmap/debt.md](../roadmap/debt.md) |
| A finished piece of work | New stage in [PROJECT_MEMORY.md](PROJECT_MEMORY.md); [SYSTEM_SUMMARY.md](SYSTEM_SUMMARY.md) if the state changed |

Run `python3 scripts/check_docs.py` before committing docs.

## Memory entry template

```markdown
## YYYY-MM-DD — topic

- What changed and why it mattered.
- What was rejected or left out, and why.
- What is left open (link to roadmap/debt.md).
```

At most three bullets; newest stage first; never rewrite an old stage.

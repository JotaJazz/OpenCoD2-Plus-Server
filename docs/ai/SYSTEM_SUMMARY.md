# System summary

Live snapshot. Last updated: 2026-11-02 (`master` and `dev` at the CoD2 1.3
Plus build variant; the latest release is `v1.0.0-rc2`).

## Tree

```
src/                     engine, server, game, libcod (see ../architecture/overview.md)
mods/bots/               bots mod (GSC, 4 files)
scripts/                 launchers, systemd unit, cfg generator, bots installer, tests, docs checker
  linux/                 iniciar_cod2rev.sh, cod2rev@.service
  windows/               iniciar_cod2rev.bat
docs/                    this documentation, CHANGES.md
.github/workflows/       build.yml (8 jobs: 5 Linux with 1.3 Plus, 1 MySQL, 2 Windows)
Makefile                 all builds
README*.md               user README in 6 languages
AGENTS.md                agent entry point
LICENSE                  AGPL-3.0
run_bin.sh               runs bin/ from the repository (upstream's)
```

## Outputs

| Binary | Build | Accepts |
|---|---|---|
| `bin/cod2rev_lnxded` (64-bit) | `make` | protocols 115–119 (libcod) |
| `bin/cod2rev_lnxded` (64-bit) | `make PROTOCOL=118` | protocol 118 |
| `bin/cod2rev_lnxded` (64-bit, CoD2 1.3 Plus) | `make PLUS=1` | the Plus client (protocol 118 with `plus\\122`) |
| `bin/cod2rev_lnxded` (32-bit) | `make ARCH=x86` (with or without `PROTOCOL=118`) | as the 64-bit build of the same version |
| `bin/cod2rev_lnxded` (aarch64, experimental) | `make ARCH=arm64` on the ARM host | as the 64-bit build of the same version |
| `bin/cod2rev_win32.exe` | `make windows` / `PROTOCOL=118` | as the Linux build of the same version |

## State per subsystem

| Subsystem | State |
|---|---|
| Reversed engine | Upstream's; reviewed to voron00 `2d12404` (2026-11-02; its `libcod_t` move, SSE math and float math helpers not taken) |
| Network hardening | Done: message/fragment bounds, rate limits, rcon lockout and whitelist, download checks, format strings |
| Logging and admin | Done: log naming/rotation/timestamps, `g_logRotateSize`, forced rate/snaps, kick/timeout messages, clean SIGTERM/SIGINT/SIGHUP quit |
| Long uptime | Time wrap restart moved to a map change after day 18.6; snapshot counters reload the map; full dvar pool is not fatal for scripts or rcon |
| Crash reports | Done: `crash.log` in `fs_homepath`, Linux and Windows |
| libcod | 203 function and 200 method entries, aliases included (`src/libcod/gsc.cpp`); zk_libcod port complete, its callbacks and dvars included (left-outs in [libcod.md](../architecture/libcod.md#not-ported-on-purpose)) ([ADR 0003](../architecture/adr/0003-zk-libcod-names.md)); shell, memory, raw path and any-address builtins need `+set sv_libcodUnsafe 1` ([ADR 0008](../architecture/adr/0008-unsafe-builtins-behind-a-dvar.md)) |
| JSON, HTTP/WebSocket, sounds | Done: yyjson, Mbed TLS 3.6.7 with own HTTP client, Speex 1.2.1 |
| Bots mod | dm, tdm, sd, ctf, hq; A\* over per-map cached graphs |
| One game for 1.0 and 1.3 | `net_altPort` (1.0 build): a second port announces 1.3, so one process is listed for both versions; run it without `iw_15.iwd` ([networking.md](../architecture/networking.md)) |
| CoD2 1.3 Plus | `make PLUS=1` ([ADR 0015](../architecture/adr/0015-plus-as-a-build-variant.md)): only the Plus client, Plus version 122; handshake and snapshot offset done, a real match at 40 Hz left ([plus-protocol.md](../architecture/plus-protocol.md#milestones)); needs OpenCoD2-Plus, which cannot be distributed yet |
| arm64 | `make ARCH=arm64`, experimental ([ADR 0013](../architecture/adr/0013-arm64-linux-build.md)): smoke and bots pass on a Raspberry Pi 5; not built by CI |
| Listen server | `LISTEN_SERVER` builds the server into a client, for the maintainer's client project; off in this repo's builds |
| Windows build | MinGW, static, threads through a stdcall wrapper |
| Deployment | Launchers (LAN/internet mode, port 28960), `scripts/linux/cod2rev@.service` |
| Branches and releases | Work goes on `dev`, which reaches `master` for a release; `v1.0.0-rc2` (pre-release, 2026-11-03, first as OpenCoD2-Plus Server) has the six stock CI binaries with `LICENSE`, the example cfg and the launcher (and the systemd unit on Linux); 1.3 Plus and arm64 are build-from-source |
| Docs | This layer plus `scripts/check_docs.py` (2026-10-22) |

## Commands

| Task | Command |
|---|---|
| Build 1.0 / 1.3 / 1.3 Plus / Windows / 32-bit | `make`, `make PROTOCOL=118`, `make PLUS=1`, `make windows`, `make ARCH=x86` |
| Smoke test | `python3 scripts/smoke_test.py <game>` (`--protocol 118` or `--plus`, `--binary <bin>`) |
| Bots test | `python3 scripts/bots_test.py <game> [--gametype sd\|ctf\|hq]` |
| HTTP test | `python3 scripts/http_test.py <game>` |
| Docs check | `python3 scripts/check_docs.py` and `python3 -m unittest discover -s scripts -p 'test_*.py'` |
| Regenerate example cfg | `python3 scripts/gen_server_cfg.py` |
| Install bots | `python3 scripts/install_bots.py <game> --dest <home>` |

## Contracts

| Contract | Defined by | Consumers |
|---|---|---|
| Network protocol 115/118/119 | Stock clients | Every client; must not change |
| GSC builtins and `CodeCallback_*` | zk_libcod names | Server mods, `mods/bots` |
| Dvars | `scripts/server.cfg.example`, [../CHANGES.md](../CHANGES.md#new-variables) | Admins' `server.cfg` |
| `crash.log` format | `Sys_InstallCrashHandler` in `src/unix/unix_main.cpp`, `src/win32/win_main.cpp` | Admins, `addr2line` |
| Waypoint graph files | `src/libcod/gsc_graph.cpp` | `mods/bots` cache per map |

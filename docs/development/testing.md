# Testing

User-facing summary: [README](../../README.md#testing). CI builds every binary
and starts the published Linux ones without game files, which must end with the engine's
error and exit code 1. There are no unit
tests for the C++ code; tests run the real server against a game folder.

## Game folder

Tests need a CoD2 folder with `main/*.iwd`. Use one with only the stock
`iw_*.iwd` and `localized_*.iwd`: mod iwds that replace gametype scripts stop
the map from loading. Check with `ls <game>/main/*.iwd`; a clean folder can be
made of symlinks to only those iwds. Tests only read it; each run uses a
temporary `fs_homepath`.

## Test scripts

| Script | What it checks | Typical run |
|---|---|---|
| `scripts/smoke_test.py` | Map loads; `getinfo`, `getstatus`, rcon; minimal client connects, gets the gamestate, enters, sends fragmented messages, keeps its address from a guessed qport and after a port change, runs at most 64 commands per message, calls at most three votes, has its menu commands limited and its malformed packets logged at most 10 a second, cannot start chat with 0x14; a challenge pushed out of the table, or under `sv_challengeStateless 1` during a flood, still joins after a fake authorize reply; `getinfo` answers through a `getstatus` burst and takes 50 at once; over-long query challenges and `../` map names refused; a `bulletTrace` into a model before the first frame; master heartbeats; SIGTERM shutdown; log handling | `python3 scripts/smoke_test.py <game>`, `--protocol 118 --binary <1.3 binary>` and `--plus --binary <1.3 Plus binary>` |
| `scripts/bots_test.py` | Bots mod: graph built, saved and reloaded; paths, sights, grenades, knives; no script errors. `--gametype sd`: roles, active bomb sites, plants; `--gametype ctf`: roles, flag pickups (defuses and captures are only printed); `--fps N` runs it at that `sv_fps`, with a snapshot every frame | `python3 scripts/bots_test.py <game> --map mp_carentan` |
| `scripts/http_test.py` | `httpFetch` and `webSocket*` against local HTTP, HTTPS, WS and WSS servers | `python3 scripts/http_test.py <game>` |
| `scripts/plus_rules_test.py` | The Plus 123 gameplay rules ([plus-protocol.md](../architecture/plus-protocol.md#version-123)), with a minimal Plus client reading its playerstate: fast reload (no bolt-action shot sooner with a switch taken back), prone peek (no lean back faster than let go), mg clip (leaving a turret keeps the player behind it); shotgun spread (`g_shotgun_spread_fix` puts a shot's impacts on a pattern), which every build passes; and mg rate (a manned MG fires once a `fireTime`, a turret turns back at 200 degrees a second), whose `--fps N` runs the server at that `sv_fps` with a snapshot every frame, and which other builds fail above 20 Hz; and snapshot rate (with `sv_lanForceRate 0`, a snapshot every frame and the server's rate, and `g_forceSnaps` by rcon at once); `--only` picks checks. Other builds fail the rest, as they keep the bugs | `python3 scripts/plus_rules_test.py <game> --binary <1.3 Plus binary>` |
| `scripts/check_docs.py` | Documentation links, paths, personal data, memory stages | `python3 scripts/check_docs.py` |
| `scripts/test_check_docs.py` | Unit tests of the checker | `python3 -m unittest discover -s scripts -p 'test_*.py'` |

Helpers: `scripts/cod2client.py` (minimal client: connect, gamestate, enter,
commands, fragments, `read_frames()` for snapshots and voice) and
`scripts/cod2snap.py` (parser for gamestate, snapshots and server commands).
The server tests take `--binary` to test a build outside `bin/`;
`bots_test.py` and `http_test.py` also take `--keep <folder>` to keep the
logs. They pick free ports, so they can run in parallel.

## Soak run with ASan and bots

Covers map changes and gameplay under AddressSanitizer
([building.md](building.md#addresssanitizer-build)):

1. `python3 scripts/install_bots.py <game> --dest <home>`.
2. Start the ASan binary from the game folder with
   `ASAN_OPTIONS=detect_leaks=0:log_path=<logs>/asan`, `+set fs_homepath <home>`,
   `+set fs_game cod2rev_bots`, `+set bots_count 10`, short
   `scr_<gametype>_timelimit` values and an `sv_mapRotation` over dm, tdm, ctf,
   hq and sd, then `+map_rotate`.
3. After a while: `getstatus` (ping `-1` means a bot is out of the game),
   kills per map in `games_mp.log`, no `<logs>/asan.*` files.

The bots tests also accept the ASan binary with `--binary`.

## Pitfalls

- Stop servers by the PID you started, or `pkill -x cod2rev_lnxded`;
  `pkill -f` also matches the shell running it. With several agents testing
  at once, stop only your own PIDs: matching a shared path in
  `/proc/*/cmdline` once killed other agents' servers.
- Parallel servers need their own port and `fs_homepath`.
- A game client on Windows playing on a server inside WSL2 (NAT networking)
  skips steps now and then while walking; the same build run natively on
  Windows plays smoothly. Use the Windows build for play tests by hand.
- `+set x ""` on the Linux command line must reach the server (fixed in
  `src/unix/unix_main.cpp`; the smoke test checks it with `sv_master2`).
- Bullet tests: antilag rewinds targets to recorded positions; wait about
  0.3 s after moving one, or set `g_antilag 0`. Use
  `setWeaponSpreadScale(0)`, target health 1000, and clear lines of fire
  from the spawn points (`mp_brecourt` has minefields).
- `bot notify("disconnect")` takes a bot out of the mod's control;
  `freezeControls` keeps a player still.
- Client-side checks with the test client: use one bot (a second one, driven
  by the mod, kills things), a fixed spawn (`mp_tdm_spawn[0]`), start each
  phase with a cvar sent over rcon, and check the second half of each phase:
  a phase command can land a few frames early.
- Temp entities in snapshots: `eType` is `ET_EVENTS` (10) plus the event;
  trajectory types are 0 stationary, 2 linear, 5 gravity.
- CTF pickups are infrequent and the CTF bots test can flake; rerun before
  investigating.
- `scripts/gen_server_cfg.py` takes no options: any run regenerates
  `scripts/server.cfg.example`.

## Local GSC harness

The maintainer keeps a GSC test harness outside git, in
`docs/superpowers/harness` (`harness.py` and one `t_*.py` per test).
`harness.Server(gsc, bots=N, binary=..., map=...)` installs the bots mod in a
temporary `fs_homepath`, appends the test GSC (which defines `libcodTest()`)
to `_callbacksetup.gsc` and starts the server; the GSC reports with
`logprint("T name value")` lines, read back with `s.results()`.
`join_client(s)` connects `scripts/cod2client.py` and joins a team. Run a test
with `PYTHONPATH=scripts python3 <test> <binary>`. It is not part of the
repository; promote a test to `scripts/` when it is worth keeping.

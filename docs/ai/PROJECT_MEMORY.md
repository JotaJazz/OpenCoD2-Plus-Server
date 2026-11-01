# Project memory

Operational memory: new stages are added at the top, old stages are never
rewritten, at most three bullets each. It records why work mattered, what was
rejected and what is left open; for what changed in detail see
[../CHANGES.md](../CHANGES.md) and `git log`.

## 2026-11-01 — 40 Hz played

- The maintainer played on a public server with this branch's 1.0 build at `sv_fps` 40 and noticed no difference from 20 Hz: the game's pace held.
- That also means no improvement was felt, and the test likely ran from the server's own network, where the LAN exemption ignores `rate` and `snaps`. Left open: a player on the internet.

## 2026-10-31 — script time follows the frame rate on Plus

- `wait` was fixed at 20 steps a second, so scripts ran at the frame rate. It follows `sv_fps` now, and 100 `wait 0.05` take 5,000 ms at 20 and at 40 Hz. `sv_fps` still defaults to 20.
- 40 Hz goes first because the 50 ms steps left in the game divide into it: at 62.5 Hz `wait 0.05` is 48 ms, and turrets would think late. The killcam's 50 ms looked like a speed bug and is not: it searches the archive.
- Clients ask for 30 snapshots at most, which is 20 a second at 40 Hz, so `g_forceSnaps` and `g_forceRate` go higher on `plus`: 41 snapshots a second with the LAN exemption removed. Left open: a match with people; see [plus-protocol.md](../architecture/plus-protocol.md#tick-rate).

## 2026-10-31 — Plus leaves 1.3 out and tests the tick rate

- The maintainer chose a Plus that differs from stock, so a Plus server refuses other clients with an update notice and aims at 40–60 Hz ([ADR 0012](../architecture/adr/0012-plus-leaves-1-3-out.md)). Fairness stops being a limit, and `master` stays the line for stock clients.
- `sv_fps` alone gives 40 and 62.5 Hz at 21.5% and 29.8% of a core with 64 players, but scripts run at the frame rate: `WAIT_FRAME_TIME` is 20, so `wait 1` lasts 0.5 s and 0.32 s. Bandwidth grows about 3 times at 60, to 25 KB/s a client.
- Left open: making script time follow `sv_fps`, then a real match. The bots and client tests pass but do not show the game's speed, and the client test holds the client at 20 fps.

## 2026-10-31 — unchanged fields no longer resent

- `MSG_WriteDeltaField` compared the field pointers, which never match, so 47–49% of the fields written were unchanged values sent in full; the bug came from upstream. Written both ways on the same snapshots in one server, comparing values saves 20.5% on `mp_toujane` and 19.8% on `mp_carentan`, from 499 to 396 and from 386 to 309 bytes a message, with 20 test clients and 20 bots.
- OpenCoD2-Plus's real client gave the same result against `v1.0.0-rc1` and this fix: 10 prediction misses and 1 animation miss. Smoke (1.0 and 1.3) and bots pass.
- Left open: no stock 1.3 or 1.0 client has played on it yet, and the original binary was not disassembled; the reference is OpenCoD2-Plus's reconstruction.
## 2026-10-31 — network measured for CoD2 Plus

- `MSG_WriteDeltaField` compares pointers, not values, so unchanged fields go out in full. Comparing values takes 20% off with stock clients, written both ways on the same snapshots in one server. Comparing separate matches hid it: traffic varied too much (−6.9% and +4.3%).
- On top of that no candidate reaches the 20% gate: zstd with a trained dictionary gives 12–14% and a delta recoding about 12–14% (estimated). Numbers in [plus-protocol.md](../architecture/plus-protocol.md#milestone-0-results).
- Left open: the fix itself, which needs a real client, and whether milestone 1 goes ahead. Test clients only walk, so a real match may differ.

## 2026-10-31 — CoD2 Plus protocol designed

- `plus` is the line for changes that do not fit stock clients. OpenCoD2-Plus is its client, and code flows one way, from here to there. The design is in [plus-protocol.md](../architecture/plus-protocol.md); nothing is implemented.
- The server keeps announcing 118 and the two sides agree in the `connect` handshake, because CoD2x browsers hide anything but 118 or 120 and a new number would need a new master. A mismatch falls back to 1.3, so the repositories can be released apart.
- Left open: what compression is worth it (milestone 0 measures that first), and OpenCoD2-Plus's license, which blocks any release that requires its client.

## 2026-10-31 — first release candidate

- `v1.0.0-rc1` is the first release, marked as a pre-release: the six CI binaries of the tagged commit, each with `LICENSE` and the example cfg. From here `master` takes fixes only.
- The project number is separate from the game versions 1.0 and 1.3, which still name what each binary announces.
- Left open: the bots mod is not in the archives (`scripts/install_bots.py` needs the repository), and packing is by hand until a second release asks for a script.

## 2026-10-31 — `net_altPort` on the real masters

- Tested on the maintainer's public server, which settles the masters left untried in the stage below: both ports answer (115 and 118), the server is listed for 115 on both masters, and it appears in a CoD2x 1.4 client's online browser.
- A real CoD2x client joined through the second port and fetched the `mp_rhine` and `mp_harbor` iwd (26 MB) over HTTP while a real 1.0 client played the same match.
- Left open: the plain 1.3 browser was not checked. A direct `getservers 118` returns a capped 111 servers without this one, so that query proves nothing.

## 2026-10-31 — one process for 1.0 and 1.3

- Real 1.0 (from the disc) and 1.3 clients played one match on one 1.0 build, kills both ways, so only the listing was missing: `net_altPort` is a second socket that announces 1.3. Checked with the smoke test and a fake master; real masters not tried, and that was left out on purpose: a test would publish the server.
- The hard part was data, not protocol: `iw_15.iwd` overrides 33 stock files and is referenced on every map, so a mixed server runs the disc's iwds. `mp_rhine` and `mp_harbor` work for both from a separate iwd of their 15 files; the real 1.0 client loaded `mp_rhine` that way.
- Rejected a proxy (zk_libcod): the 1.0 build already switches formats per client. Left open: the 1.0 client has no HTTP download, only about 20 KB/s in game, so that iwd takes 20 minutes there.

## 2026-10-31 — bots play HQ

- A bot takes the radio by standing watch inside it, or guards it from around when its team holds it. All 15 stock maps had captures in a 5-minute run with 6 bots (1 to 5 each).
- The graph's islands decided the design: a neutral radio never leaves, so one no bot could reach stopped the game there, and 2 to 5 radios of most maps were like that. The mod drops them from `level.radio` before `hq_setup` when 3 others remain. A player on that server never sees those radios; the multi-floor graph work would give them back.
- `bots_test.py` leaves out `array index -1`: stock `hq_obj_think` reads `level.radio[-1]`, and outside developer mode the script goes on.

## 2026-10-31 — network leftovers of the audit

- Of the three deferred items one was as described: a refused `donedl` or `wwwdl` gamestate was lost, and is now sent later. The rcon reflection was wrong: wrong passwords get about 2 replies a second, whitelisted or not (10 of 2,400 in 5 s).
- The challenge note missed the real problem. The table turning over was harmless, but the global limit let 1000 made-up addresses a second delay a join by 40 s, and 3000 stop it. Retries now have their own 20 a second: 3 s at either rate.
- That lane only beats floods that do not repeat addresses (see debt.md). Rejected the stateless challenge for now: it reaches the reversed connect and authorize paths.

## 2026-10-31 — load measured

- 64-bit 1.0 on `mp_toujane` tdm with protocol clients that join a team and take delta snapshots: 20 bots alone 3% of a core; 20 clients and 20 bots 7%, 136 KB/s; 60 clients and 4 bots 12%, 400 KB/s, 171 MB, 20 snapshots a second and no stall over 150 ms. A full server is far from the 20 fps budget, so no CPU work is planned.
- `-O2` gave nothing over `-O1` (2.9% against 3.0%), so the build flags stay.
- The test clients only walk and never fire, and all ran over loopback on one 32-core WSL machine: real fights, internet paths and small hosts will cost more.

## 2026-10-31 — 64-bit by default on Linux

- `make` builds 64-bit, `make ARCH=x86` 32-bit, Windows stays 32-bit ([ADR 0010](../architecture/adr/0010-64-bit-default-on-linux.md)). Forcing `-m32` had been the maintainer's early choice, not a need.
- Checked before the switch: smoke, HTTP, bots and the harness on 64-bit, and a 15-minute ASan soak over five gametypes with no reports. Graph files came out byte-identical from both builds, so existing caches keep working.
- CI artifact names follow the default: the plain name is 64-bit, `-x86` the 32-bit one.

## 2026-10-31 — upstream review to dbe3621

- Merged voron00 up to `dbe3621` keeping our tree (`-s ours`): six commits read, two lines of their work taken. `iplist.txt` now also checks a proxied client's real address, through our trusted `proxy_realip`, and `sqrtInv` uses `I_rsqrt`, which drops `Q_rsqrt` and its `long` type punning.
- Rejected their `libcod_t` move: it clears speed, gravity, item pickup, animation and bot input on every `ClientSpawn` and map change, and it parses the client's `ip` key with `NET_StringToAdr`, so any client could set `getIP()` or make the main thread wait on DNS. Rejected the `inuse` checks: the VM already raises "removed entity" first (tested). SSE stays behind [the x87 decision](../roadmap/debt.md).
- Upstream's later work on `libcod_t` will conflict with our per-slot arrays; read those commits by hand.

## 2026-10-31 — lean pass

- From the audit: copied libcod helpers, Makefile rules and test helpers merged, unused platform code removed, 1,420 lines fewer. Script error texts and the build commands of every configuration stayed the same.
- The one behaviour change is on purpose: `graphAutodiscover` uses the typed flood of `graphAutodiscoverEx`. Same nodes, 23 fewer edges on `mp_toujane`; nothing in the repo calls the plain one.
- The stream stubs stay: `com_files.cpp` and `Sys_Init` still call them. Only the disabled `#else` thread went.

## 2026-10-30 — bots: patrols and ammo

- From the audit. Its cause for the graph islands was wrong: dropping nodes without links moved mp_carentan from 10.1% to 10.0%. They are upper floors and cellars with a spawn of their own, the multi-floor gap; patrols now skip what a bot cannot reach (39 of 300 picks to 0).
- A bot with no ammo left pressed reload forever; it changes weapon or charges now. A bot that spawns on a cut-off floor still stays there ([../roadmap/debt.md](../roadmap/debt.md)).

## 2026-10-30 — logs, CI and docs

- From the audit. A fatal error's reason now reaches the console log and Linux flushes the logs before `_exit`; the launchers keep five old console logs. CI starts each published Linux binary without game files and expects exit code 1; the Windows binary is still only built.
- The docs caught up with the 64-bit build, which they still called impossible.

## 2026-10-30 — script callbacks

- From the audit. `CodeCallback_DPrintf` cleared the arguments of the running builtin, because `stackGetParams` prints on a type mismatch; `getArrayKeys` dropped integer keys; re-entry guards stayed set after a `Com_Error`, so a callback never ran again.
- `connectionlessPacket` was reported broken and is not: the three stray `0xff` bytes read as whitespace by the tokenizer.

## 2026-10-30 — libcod data safety

- From the audit. `ATTACH` and `VACUUM INTO` wrote files past `sqlite_open`'s folder; `map_restart` dropped queued async SQLite writes (498 of 500 in a test); on Windows `json_save_async` only worked once, confirmed by running the `.exe` through WSL; big JSON or a 64 KB cell ended the map; `mysql_*` had no gate, timeouts or queue cap.
- Outside developer mode a script error does not stop the thread: the statement goes on with `undefined`. Tests must check return values, and the `stackPushUndefined()` after `stackError()` is needed.
- Left open: many distinct cells of a few KB in one sync query can still run the string pool out; only each cell is cut.

## 2026-10-30 — network floods

- From an audit of the whole repo. `donedl` before entering the game cost 95% of a core and 130 MB in 6 s; `connect` had no limit; `getchallenge` shared the 10 replies a second of `getinfo`; a full bucket table refused every new address; bans were only read in the authorize reply. Fixed; the `donedl` run uses 1% of a core now.
- Rejected: limiting `donedl` by `messageAcknowledge`, which the client chooses. A per-slot budget covers every gamestate a client can trigger.
- rcon's global limit runs before the password now, at the maintainer's choice: blind guessing ends, and during a flood only `sv_rconWhitelist` and local tools get rcon. The entry eviction change could not be tested, since 127.x is exempt from the lockout.

## 2026-10-29 — bot script error cascade located; repaths and grenade suicides

- The "rare cascade when a bot joins a freed slot during a grenade kill" was misdescribed: 120 `developer 2` runs (tdm, dm, sd, ctf) showed one error source, stock `sd.gsc` (defuser killed on the last tick still defuses, lines 1925–1926). A grenade never passes to the next player in a slot: `G_FreeEntityRefs` clears `parent`, so a gone player's grenade does no damage. `bots_test.py` leaves out exactly that stock race.
- The same runs showed DM failing `bots search paths sparingly` in 16 of 40: repath on every goal-node change and after every combat tick. Fixed in the mod (moving goal twice a second, combat repath at most 0.5 s away). Grenade suicides were measured with a probe: most walked into their own grenade, the rest threw at cover past the 150-unit check; both fixed, 2.8 to 1.4 per 100 throws. Fight runs failing any check: 19 of 80 before, 1 of 24 after.

## 2026-10-29 — bot graph reload per SD round measured

- Rejected a graph cache across `map_restart`: `graphLoad` of a saved graph takes 0.36–0.40 ms on mp_toujane (1370 nodes), 0.44–0.51 ms on mp_burgundy (1659) and 0.57–1.08 ms on mp_carentan (2040), against a 50 ms frame. Building a graph the first time a map is played costs more, but happens once and is saved.
- If ever needed, `graphLoad(path, 1)` already keeps a graph across map restarts and map changes; the mod would only have to find its id again (for example in a cvar).

## 2026-10-29 — MySQL on 64-bit Linux

- `make ARCH=x64 WITH_MYSQL=true` links the system client (`mariadb_config`/`mysql_config`, or `MYSQL_LIBS`); the vendored 5.7 headers work with MariaDB's library (only `field->name`, the first member, is read). CI builds it without publishing.
- Fixed while testing against a private `mariadbd`: a 0 handle crashed the server; the async worker wrote `done`/`result` without the lock (TSan: 15 races before, none after); `mysql_close` left `mysql_reuse_connection` pointing at the closed connection; `int64 == int` was a type error in the VM, which broke `handle == 0` in every build.
- Local harness: `t_mysql.py` added; `t_zk4` placed `a` next to b's random spawn, sometimes inside a wall, and now picks a clear spot.

## 2026-10-29 — smoke and sightTracePassed

- Not a gap: in the 1.3 dedicated server (`cod2_lnxded`, `pc_1.3_1_1`) `sightTracePassed` also sees through smoke. `SV_FX_GetVisibility` reads blockers that only the client adds while drawing smoke particles; the dedicated server initialises the FX system, registers effects and reads their length, but never runs them, so the answer is always 1. The stub was right; it is now documented.
- Rejected: reversing the FX system (about 10k lines, Raven's effects code) for no change on a dedicated server; OpenCoD2 has it but no license, so it is read only ([ADR 0004](../architecture/adr/0004-upstream-and-references.md)). Left open: a smoke model of our own for bots, off by default, if wanted.

## 2026-10-29 — Linux 64-bit build

- `make ARCH=x64` ([ADR 0009](../architecture/adr/0009-linux-64-bit-build.md)): upstream already builds 64-bit, so only the Makefile, Mbed TLS's AES-NI flags (`-maes -mpclmul`), `rip` in the crash report and six libcod format strings changed. 32-bit stays the default.
- Verified on x64: smoke (1.0, 1.3), bots dm/sd/ctf (1.0) and dm/sd (1.3), HTTP, an 11-minute ASan rotation with 10 bots. The local GSC harness: 17 of 22 pass; the other 5 fail the same way on 32-bit (tests not updated for `sv_libcodUnsafe`, an old scratch path, changed messages; `t_collide` is position-dependent).
- Left open: making x64 the default, a Windows x64 build, the engine's `-Wformat` warnings on x64 (kept as upstream has them).

## 2026-10-29 — map ambience switches

- `g_ambientSound`, `g_fireFx`, `g_smokeFx`, `g_weatherFx`, `g_fog`: zPAM's `scr_allow_ambient_*` done in the engine, so they work for every mod and custom map. Looped effects are matched by the folder of their file; their entities are still spawned with `SVF_NOCLIENT`, as scripts keep and delete them.
- Played by hand: walking skipped steps on servers inside WSL2, and also on the build from before the upstream merge; the stock `CoD2MP_s.exe` and the fork's Windows build, both run natively, played smoothly ([../development/testing.md](../development/testing.md)).

## 2026-10-29 — upstream sync: q_shared and com_math review

- Merged voron00 up to `672a220`: `q_shared` and `com_math` reviewed (string helpers split into `com_shared.cpp`), double literals turned into floats across `bgame` and `game`, `sv_fastDownload` loop fix, SQLite 3.54.1.
- Conflicts: `bg_animation_mp.cpp` kept the fork's 1.3 constants (folded `46.25f`, float start-time division, which upstream still divides as integers); `q_shared` took upstream's and re-applied `I_strcmpConstantTime`, the `>=` info-string checks and the printf attributes; the fast download loop kept `sv_fastDownloadSpeed`.
- Rejected for now: upstream's SSE math flags; the Makefile stays on x87 and `sse_mathfun.h` is only included with `USE_SSE2` ([../roadmap/debt.md](../roadmap/debt.md)). Verified with smoke tests and ASan bots runs (dm, sd, ctf on 1.0; dm, sd on 1.3) and a rotation soak.

## 2026-10-24 — animation script as the 1.3 client

- Compared with the 1.3 client (CoD2MP_s.exe) while porting it into OpenCoD2-Plus: the parser set the strafe flags 0x10/0x20 for every condition but STRAFING (1.3 `0x4f7f54` checks STRAFING only), which turned the legs of 55 anims (the MG42 ones too) as strafes; `BG_IsCrouchingAnim` counted the crouched runs and turns and not the crouched stumbles (`0x4f9750`), and it and `BG_IsProneAnim` answered a bit mask, not 0 or 1, so two prone anims compared as a stance change (`0x4f97b0`).
- `BG_SetNewAnimation` divided the start time as integers, so every looping anim started at its first frame (1.3 divides as floats, `0x4f9adb`); the angles, swing, blend and rate code now uses 1.3's float constants (`0x4fa000`, `0x4fa230`, `0x4f9850`, `0x4f9d80`, `0x4faff0`), with 1/130 multiplied as 1.3 does.

## 2026-10-24 — player controllers as floats

- `BG_Player_DoControllersInternal` multiplied the torso, neck and head angles by double literals (`0.69999999`, `0.30000001`, ...) and `fLeanFrac * 50.0 * 0.925`; 1.3 (`0x4fa8c4`, controllers `0x4fac80`-`0x4fad54`) uses only float constants, with `50 * 0.925` and `50 * 0.075` folded to `46.25f` and `3.7500002f`. Under x87 the double products rounded differently in the last bit now and then; the hit-location bones follow 1.3 exactly now.

## 2026-10-24 — zk_libcod batch 6: last functions

- `getAuthorizationStatus`, `setActivateOnUseButtonRelease`, `lookAtKiller`, `playScriptAnimation` ported. The authorize answer is kept per challenge and copied to the client before `ClientConnect`, so the connect callback can read it.
- Left out: `setWeaponFuseTime` and `setWeaponRaiseTime` (`PM_Weapon` predicts both on the client; ADR 0003's rule). With this batch every zk_libcod builtin is either here or in the left-out list.

## 2026-10-24 — zk_libcod batch 5: mod folders

- `fs_callbacks`, `fs_gametypes`, `fs_mapScriptDirectories`, `fs_replaceStockMaps`, `loc_loadLocalizedMods` ported; every `_callbacksetup` lookup (stock and libcod) goes through `Libcod_CallbacksScript`.
- `fs_replaceStockMaps 0` changes manymaps: a stock map's library iwd used to be linked when coming from a custom map. `loc_loadLocalizedMods` only touches the loaded lists (`sv_iwds`, `sv_iwdNames`); the referenced lists already held every non-main iwd.
- Tested in the harness except `fs_replaceStockMaps` (needs a manymaps library with a custom map).

## 2026-10-24 — zk_libcod batch 4: load and network

- `sv_isLookingAtOnDemand`, `sv_fastDownloadSpeed` and `sv_minimizeSysteminfo` ported. The minimized dvars are found by name and only moved if they have `DVAR_SYSTEMINFO` here (`sv_cheats` is `DVAR_INIT` only); turning the dvar off restores the flags on the next map.
- Not ported: `net_noFragmentationDelay`; the `#ifdef LIBCOD` loop in `SV_SendClientMessages` already sends every pending fragment before a snapshot.

## 2026-10-24 — zk_libcod batch 3: admin switches

- `g_corpseHit`, `g_spectateBots`, `g_logPickup`, `sv_botKickMessages`, `sv_noAuthorize`, `sv_authorizeTimeout`, `sv_limitLocalRcon` ported. `sv_limitLocalRcon` defaults to 0 here (zk: 1) so LAN rcon tools keep working as before.
- Not ported: `sv_disconnectMessages` (voron00 already hides that message) and `sv_botReconnectMode` (bots come back after a map change since 2026-10-17; `sv_kickbots` is mode 1).
- `sv_botKickMessages` checked with a real client in the harness; the others are one-line conditions.

## 2026-10-24 — zk_libcod batch 2: callbacks

- Nine zk_libcod callbacks in `src/libcod/libcod_callbacks.cpp`, hooked with one call each in `BG_AddPredictableEventToPlayerstate`, `G_AddEvent`, `Scr_Notify`, `VM_Notify`, `G_MoverPush`, `G_CallSpawn`, `Scr_LoadGameType`, `Com_DPrintf` and the four rate limit sites. Notify arguments are kept as `VariableValue`s with `AddRefToValue`, which covers every type; zk copies a few types by hand.
- Event callbacks do not call themselves again (a callback that plays a sound would recurse); the NotifyDebug queue drops its references in `Libcod_ShutdownLevel`.
- Tested in the harness on 1.0 and 1.3, except `CodeCallback_MoverBlockage`/`g_noMoverBlockage` (no reproducible blockage on stock maps) and `CodeCallback_CLSpam` (rate limits skip LAN addresses, and the test only has local ones).

## 2026-10-24 — zk_libcod batch 1: precache limits

- `g_safePrecache`, `g_reservedModels`, `logErrors`, `error()` and the `execute*` aliases ported from zk_libcod. The stand-ins take model and effect index 1, set in `Libcod_SpawnServerConfigstrings` right after `SV_SpawnServer` empties the configstrings; the precache dvars are latched and registered again there.
- `logErrors` prints only the message: without developer the VM keeps no source positions (zk notes its lookup tables can be stale then).
- `make WITH_LIBCOD=false` shares `obj/` with the default build; mixing them fails to link until the folder is removed.

## 2026-10-24 — fprintln is stock

- `fprintln` writing each argument followed by `,` and no newline matches the stock game: OpenCoD2-Plus reversed the same function from the 1.3 client, in its `g_scr_main_mp.c`, with the same body. Gap closed, nothing changed.

## 2026-10-24 — graph node cap

- `sv_graphMaxNodes` defaults to 16384: generated graphs need 15014 nodes on `mp_brecourt` and 1377–3788 on the other stock maps (1.0 and 1.3 maps measured with no cap). Generation adds under a second to the first load only; a bots run on `mp_brecourt` showed no hitches after loading.
- Rejected: caching the graph across SD rounds; it is read back from a binary file in milliseconds, and a persistent graph would leak on a map change.

## 2026-10-24 — snapshot counters and the clock wrap

- Risk R3 closed. The seven snapshot counter checks in `SV_Frame` reload the map instead of `Com_Shutdown`: `SV_SpawnServer` already resets every counter, so players stay connected. A fast restart resets the archived and cached ones too, so round-based modes rarely get there.
- Audit of `Sys_Milliseconds` at day 24.8: every use compares differences, which wrap safely with `-fwrapv`; `Com_Frame` loses one frame (`com_lastFrameTime` is clamped). `getSystemMilliseconds` jumps back to 0 for scripts. No change needed.
- Checked by writing the counters through `/proc/<pid>/mem` with a client and bots connected, on 1.0 and 1.3.

## 2026-10-24 — time wrap restart between maps

- Risk R2 closed: `SV_Map_f` shuts the server down before loading the map once `svs.time` passes `0x60000000` (day 18.6); `SV_Frame`'s mid-match restart at `0x70000000` stays as the fallback. The snapshot counters were already reset on every map load, so only `svs.time` grows across maps.
- `SV_Shutdown` cleared `svs.redirectAddress` with the rest of `svs`, so an rcon command that shut the server down replied to an empty address; it is kept now.
- Checked by writing `svs.time` through `/proc/<pid>/mem` from a local harness test (the test process is the server's parent, so ptrace rules allow it), on 1.0 and 1.3.

## 2026-10-24 — full dvar pool

- Risk R4 closed: dvars named by a script, the console, rcon or a config check `Dvar_CanCreate` first, so a full pool (1280) is a script error or a printed message; engine registrations stay fatal, as in the binary.
- Checked with a local harness test that fills the pool from a script and then sets new names over rcon, on 1.0 and 1.3.

## 2026-10-24 — unsafe builtins behind a dvar

- Risk R5 closed ([ADR 0008](../architecture/adr/0008-unsafe-builtins-behind-a-dvar.md)): shell, raw memory, raw path and any-address builtins fail without `+set sv_libcodUnsafe 1`; `sqlite_open` is kept under `fs_homepath/<mod>`; HTTP refuses private addresses without `sv_httpAllowPrivate`. Off by default, so old mods need the dvar.
- Both dvars are read once at startup: a script's `setCvar` uses the internal source and ignores `DVAR_INIT`. `fread` and the other handle functions are gated too, since a forged handle is a raw pointer.
- Checked with `scripts/http_test.py` (now starts with `sv_httpAllowPrivate 1`) and a local harness test on 1.0 and 1.3.

## 2026-10-24 — sv_pure left as is

- Risk R1 closed as an inherent limit, not fixed: the client (`FS_ReferencedIwdPureChecksums`, read in OpenCoD2-Plus) sends only the iwds it has referenced, in a 1024-byte command, so requiring every server iwd drops legit clients, and a cheater with the stock files computes the same pure checksums from the `checksumFeed`.
- Rejected: a draft that required all checksums and removed the protocol 119 skip.

## 2026-10-24 — walkable normal as a float

- `MIN_WALK_NORMAL` was the double `0.69999999`; every site that uses it (mantle `0x512131`, prone `0x514863`/`0x5149ea`/`0x514be8`/`0x514eaa`, pmove `0x5172b6`/`0x519db7`, missile `0x521f18`) compares with the float `0.7` at `0x5c427c` in 1.3, as `WALKABLE_NORMAL_Z` already did in the collision code. Only a normal of exactly `0.7f` changes side.

## 2026-10-23 — eye bob

- `BG_GetSpeed` used the 3D velocity, so the shot origin (`G_GetPlayerViewOrigin`) bobbed while jumping or falling; 1.3's game (`0x4fde06`) and client (`0x4cfa44`) use x and y only. Found while porting the client's view in OpenCoD2-Plus, which had the same bug.
- `BG_GetBobCycle` divided as integers, so the server's eye never bobbed at all and the `BG_GetSpeed` bug hid behind it; 1.3 (`0x4fddb6`) divides by `255.0f`. OpenCoD2-Plus's server eye test checks both through libcod's `getViewOrigin` (the stock `getEye` is the origin plus 40).

## 2026-10-22 — README front page

- The six READMEs now open with what the server is for, "What it does today", how to run it and a section for contributors; build, running, testing and layout fold into `<details>`, with Notice and License at the end ([ADR 0007](../architecture/adr/0007-readme-front-page.md)), following OpenCoD2-Plus.
- "How to run" promises a Releases page that does not exist yet: publishing releases is open.

## 2026-10-22 — documentation system

- Project map, conventions, engine facts and open leads moved from a local `CLAUDE.md` and the assistant's private memory into `AGENTS.md` and `docs/` ([ADR 0006](../architecture/adr/0006-ai-documentation-layer.md)).
- `scripts/check_docs.py` runs locally, not in CI, so doc edits do not start builds.
- Rejected: committing `CLAUDE.md`; it stays local for machine-specific paths.

## 2026-10-22 — upstream sync: xanim review

- Merged voron00 up to `8301c00`: xanim code reviewed (`xanim_calc.cpp` folded into `xanim.cpp`), the old `test/` folder removed, named walkable-normal constants.
- `src/qcommon/qcommon.h` conflicted only by line endings; ours (LF) kept plus upstream's one new line.
- Verified with ASan bots runs (dm, sd, ctf on 1.0; dm, sd on 1.3) and a 10-minute rotation; hit locations spread over the whole skeleton.

## 2026-10-18 — listen server and rcon errors

- `LISTEN_SERVER` lets a client embed this server for local games (FX system recreated after `dedicated 1`); this repo's builds are unchanged.
- An error raised inside an rcon command now ends the redirect before unwinding, instead of writing over a freed stack buffer.

## 2026-10-17 — base hardening

- Format strings checked at build time, map name overflows refused, stack protector, FORTIFY, RELRO, `-fno-strict-aliasing -fwrapv`.
- Clean SIGTERM/SIGINT/SIGHUP quit, `g_logRotateSize`, `net_strictPort`, per-thread `sigaltstack`, systemd unit, Windows threads through a stdcall wrapper.
- Left open: `sv_pure` bypass, long-run time wraps, unsafe builtins behind a dvar ([../roadmap/debt.md](../roadmap/debt.md)).

## 2026-10-17 — audit of the fork

- A six-area review found about 60 issues: player and bot argument checks, level state reset on every `G_InitGame` with `libcodLevelGeneration`, SQLite/exec references and locking, HTTP limits, rcon guess counting and `sv_rconWhitelist`, WAV parsing, deferred map commands.
- The fake master check added to the smoke test found that `+set x ""` was dropped on Linux.

## 2026-10-17 — zk_libcod port completed

- Batches A–H: callbacks, player/weapon/admin functions, per-player visuals, script model physics and bullet drop, JSON, HTTP/WebSocket, sounds through voice chat.
- Libraries vendored and built in ([ADR 0002](../architecture/adr/0002-vendored-libraries.md)); names kept, unsafe or prediction-breaking functions left out ([ADR 0003](../architecture/adr/0003-zk-libcod-names.md)).
- Detailed change list moved from the READMEs to `docs/CHANGES.md` ([ADR 0005](../architecture/adr/0005-readme-and-changes.md)).

## 2026-10-16 — bots mod

- Bots navigate per-map waypoint graphs with A\*, hunt and patrol, use sights, grenades and knives; SD and CTF roles followed on 2026-10-17.
- `scripts/bots_test.py` checks graphs, paths, combat and objectives; CTF pickups are infrequent and can flake.
- Left open: HQ, multi-floor cells, graph node cap on `mp_brecourt`, a rare script error cascade.

## 2026-10-13 — fork started

- MinGW Windows build, game version chosen at build time ([ADR 0001](../architecture/adr/0001-game-version-at-build-time.md)), CI for four builds, launchers and `server.cfg` generator.
- First hardening: rcon lockout, bounded libcod strings, 1.3 fragment offsets, protocol 119 systeminfo overflow, `dedicated 1`, 64-bit file offsets, monotonic clock.
- Smoke test against a real game folder, six-language README with a Transparency section.

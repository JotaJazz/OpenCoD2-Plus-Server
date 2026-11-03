# Debt, risks and open leads

What is known to be missing or fragile, with what a fix needs. Remove an
entry in the commit that resolves it and record the stage in
[../ai/PROJECT_MEMORY.md](../ai/PROJECT_MEMORY.md).

## Risks

None open. R1 became a known gap; R2–R5 were fixed on 2026-10-24
(see [../ai/PROJECT_MEMORY.md](../ai/PROJECT_MEMORY.md)).

## Known gaps

| Gap | Where | Notes |
|---|---|---|
| `sv_pure` only proves the client has the server's iwds, not that it uses no others: the client reports only the iwds it has read from (`FS_ReferencedIwdPureChecksums`), so the server cannot require them all, and anyone with the stock files can compute the pure checksums from the `checksumFeed` in the gamestate; protocol 119 skips the check | `src/server/sv_client_mp.cpp` | Inherent to the Quake 3 design; a stricter check drops legit clients |
| zPAM 4.x needs the CoD2x API (`getHWID`, `match*`, `g_cod2x` ≥ 5) | — | zPAM 3.36 runs on 1.0 and 1.3 |
| Protocol 119 fragment offset format | `src/qcommon/net_chan_mp.cpp` | Needs a Game Pass client |
| A `getchallenge` flood that repeats its addresses still delays joins, and `getinfo`/`getstatus` share 10 replies a second, so a few addresses hide the server from browsers | `SV_GetChallenge` in `src/server/sv_client_mp.cpp`, `SVC_Info`/`SVC_Status` in `sv_main_mp.cpp` | Two addresses at 10 a second fill the 20 a second for retries. A full answer is a stateless challenge (as a SYN cookie), which reaches the connection and authorize paths, or per-/24 limits with the masters exempt |
| `sess.teamVoteCount` is checked but never incremented, so a player can call votes without end; a reconnect may clear `EF_VOTED` and allow a second vote | `src/game/g_cmds_mp.cpp`, `g_client_mp.cpp` | Game rules: compare with 1.3 first |
| A leading 0x14–0x16 byte in chat survives `Cmd_ReplaceControlChars` and may show as an engine string on clients | `src/qcommon/cmd.cpp`, `G_Say` | The client's rendering is unconfirmed |
| `mr` and `score` skip flood protection, and `mr` notifies `menuresponse` (and runs `CodeCallback_PlayerCommand`) each time | `SV_ClientCommand` in `src/server/sv_client_mp.cpp` | Bounded per message by the 64-command cap; the cost depends on the gametype scripts |
| About 40 guards in `gsc_player.cpp` and `gsc_bots.cpp` compare with `MAX_CLIENTS`, not `sv_maxclients` | `src/libcod/` | Not reachable: entities in that range are never in use |
| `MSG_ReadDeltaPlayerstate` never checks the field count it reads against `playerStateFields` | `src/qcommon/msg_mp.cpp` | The server only reads its own snapshots; matters for a client facing a hostile server |
| Bad packets are printed each time (command byte, cmdCount, mute index, voice size), which can flood the log | `src/server/` | Cosmetic |
| An authorize reply is only checked by its source IP: anyone who can forge the authorize server's address can answer their own challenge with any GUID, taking an admin's GUID or slipping a GUID ban. Do not grant rights by GUID; use rcon, passwords or IP addresses | `SV_AuthorizeIpPacket` in `src/server/sv_client_mp.cpp` | The protocol has no signature, and a forged reply arrives before the real one. Since 2026-11-02 a reply no longer changes the GUID of a challenge that already connected |
| The arm64 build rounds floats without x87, and no real client has played on it yet; movement and hit locations may differ in the last bit, and undefined behaviour that x86 and ARM resolve differently may hide in reversed code | `Makefile` (`ARCH=arm64`) | [ADR 0013](../architecture/adr/0013-arm64-linux-build.md); smoke and bots pass under qemu |
| Script runtime errors cascade outside developer mode | `src/script/scr_vm.cpp` | Stock behaviour |
| The rcon lockout's entry eviction is untested | `src/server/sv_main_pc_mp.cpp` | Read, never run: `127.x` is exempt from the lockout, so a local test cannot reach it |

## Bots mod

| Item | Notes |
|---|---|
| Stock `sd.gsc` defuse race: a defuser killed on the last tick still defuses (logged as `A;…;bomb_defuse` after the round's `W;`/`L;`) and then destroys progress bars the death already removed, two script errors at lines 1925–1926; about one SD run with bots in twenty | A stock gametype bug, also with humans; `bots_test.py` leaves exactly these two errors out. A mod's own `sd.gsc` could check `isAlive(other)` after the loop |
| `bots_test.py` checks on rare actions (`bots use ads`, `bots use melee`) fail now and then in a game with little fighting; the staged knife duel puts the bots 40 units apart, sometimes into a wall, and in DM pairs nobody (every `pers["team"]` is the same) | About one run in twenty-four after the repath and grenade fixes |
| `bots_test.py` check `few grenade suicides` fails now and then | Threshold noise: suicides are about 2% of kills |
| `sd --bombmode 1` on `mp_brecourt` sometimes never plants | Cause unknown. It planted in 2 of 3 runs before the audit and 3 of 3 after, but a separate run after it failed too. `bombmode 1` only means anything on the six maps with single-mode marks |
| Local harness `t_ammo` failed once on `a loaded weapon stays` | Cause not proven (perhaps a bot throwing a grenade); 12 of 12 passed after |
| A charging bot keeps the strafe's `rightmove`, so it comes in on a diagonal | Cosmetic. `setWalkDir("forward")` in `mods/bots/maps/mp/bots/_bots_combat.gsc` |
| Multi-floor cells in the graph builder | 1–2 days of work. Upper floors and cellars that hold a spawn get a graph of their own, cut off from the rest: 10.1% of the nodes on mp_carentan, 8.8% on mp_toujane, under 2% on mp_burgundy and mp_brecourt. Dropping nodes without links does not help. Patrols already avoid them; a bot that spawns on one stays there |
| Bullet antilag rewinds are not grouped per frame | Performance only |

## Deferred decisions

| Lead | Notes |
|---|---|
| Stats mod (kills with positions into SQLite) | Compatible with Lonsofore/CoD2MapStats |
| MySQL on Windows | The Makefile's Windows branch names a `libmysql.lib` that is not vendored; the 64-bit Linux build works ([../development/building.md](../development/building.md#mysql)) |
| soundalias functions | See [ADR 0003](../architecture/adr/0003-zk-libcod-names.md) |
| Windows x64 build | Windows is LLP64 (`long` stays 32-bit) and upstream's script VM assumes LP64: GSC int64 values are a `long int` (`src/script/script_public.h`, `Scr_AddInt64`/`Scr_GetInt64`, which also carry libcod's handles) and the bytecode is read and written with `sizeof(unsigned long)` (`Scr_ReadUnsigned`, `EmitUnsigned`, `SWITCH_CASE_ENTRY_SIZE`). About 60 `long`s in reversed files would become `int64_t`/`intptr_t`, a conflict on every upstream merge; the 32-bit `.exe` already runs on 64-bit Windows. Needs `gcc-mingw-w64-x86-64-posix` ([ADR 0009](../architecture/adr/0009-linux-64-bit-build.md)) |
| SSE math (`-msse2 -mfpmath=sse -DUSE_SSE2`, upstream since `8319e9b`, `dbe3621` adds SSE sqrt, fabs and lerp) | Kept x87 to stay with the original binary's rounding; `USE_SSE2` also swaps `FastSinCos` (animation, hit bones, weapons) for the `sse_mathfun.h` approximation. Adopting it needs bots and ASan runs and a look at hit locations |

## Accepted simplifications

- `playFxOnTagForPlayer` filters spectators by the followed player's
  `clientNum`: kept on purpose.
- One announced version per port; the 1.3 build has one port and the 1.0 build
  can add a second for 1.3 with `net_altPort`
  ([ADR 0001](../architecture/adr/0001-game-version-at-build-time.md)).

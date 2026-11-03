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
| A `getchallenge` flood that repeats its addresses still delays joins; spoofed `getinfo` from 100 addresses a second, or `getstatus` from 10, still fill their global limits for everyone but the masters | `SV_GetChallenge` in `src/server/sv_client_mp.cpp`, `SVC_Info`/`SVC_Status` in `sv_main_mp.cpp` | Two addresses at 10 a second fill the 20 a second for retries. A full answer is a stateless challenge (as a SYN cookie), which reaches the connection and authorize paths, or per-/24 limits |
| A reconnect clears `EF_VOTED` and the count of votes called, so a player can vote twice or call three more votes; the `connect` limit slows it | `src/game/g_cmds_mp.cpp`, `g_client_mp.cpp` | `ClientConnect` clears the whole client, as in 1.3 |
| About 40 guards in `gsc_player.cpp` and `gsc_bots.cpp` compare with `MAX_CLIENTS`, not `sv_maxclients` | `src/libcod/` | Not reachable: entities in that range are never in use |
| `MSG_ReadDeltaPlayerstate` never checks the field count it reads against `playerStateFields` | `src/qcommon/msg_mp.cpp` | The server only reads its own snapshots; matters for a client facing a hostile server |
| An authorize reply is only checked by its source IP: anyone who can forge the authorize server's address can answer their own challenge with any GUID, taking an admin's GUID or slipping a GUID ban. Do not grant rights by GUID; use rcon, passwords or IP addresses | `SV_AuthorizeIpPacket` in `src/server/sv_client_mp.cpp` | The protocol has no signature, and a forged reply arrives before the real one. Since 2026-11-02 a reply no longer changes the GUID of a challenge that already connected |
| The arm64 build rounds floats without x87; movement and hit locations may differ in the last bit, and undefined behaviour that x86 and ARM resolve differently may hide in reversed code | `Makefile` (`ARCH=arm64`) | [ADR 0013](../architecture/adr/0013-arm64-linux-build.md). On a Raspberry Pi 5 smoke (1.0 and 1.3) and bots pass, and one player's few minutes against bots felt as on x86; a full match with several real players is still missing |
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
| Windows x64 build | Windows is LLP64 (`long` stays 32-bit) and upstream's script VM assumed LP64. The bytecode slots that hold a pointer (calls to functions compiled later, the switch table, animation references) and the negated stack indexes were fixed for OpenCoD2-Plus's 64-bit Windows client (`f33a05e`, `72c9f3e`); slots that hold numbers stay `unsigned long` on both sides. Left: GSC int64 values are a `long int` (`Scr_AddInt64`/`Scr_GetInt64` in `src/script/script_public.h`), so libcod handles that carry a pointer would be cut to 32 bits; the Makefile has no Windows x64 target and no 64-bit Windows server has run here. The 32-bit `.exe` runs on 64-bit Windows. Needs `gcc-mingw-w64-x86-64-posix` ([ADR 0009](../architecture/adr/0009-linux-64-bit-build.md)) |
| Leave x87 for SSE2 math | The x86 builds force `-mfpmath=387` to round as the original binary does ([ADR 0010](../architecture/adr/0010-64-bit-default-on-linux.md)); x87 is legacy, its 80-bit intermediates make results depend on register spills, and upstream moved to SSE (`8319e9b`, `dbe3621`, `2d12404`). The arm64 build already rounds as SSE does and a player noticed no difference ([ADR 0013](../architecture/adr/0013-arm64-linux-build.md)). Steps: plain `-msse2 -mfpmath=sse` first, without `USE_SSE2` and upstream's `sse_mathfun.h`/`I_sin` approximations, which change `FastSinCos` (animation, hit bones, weapons) and the GSC math builtins; compare movement and hit locations against the x87 build with bots, ASan and real clients; an ADR, as it changes client-predicted rounding on every build |

## Accepted simplifications

- `playFxOnTagForPlayer` filters spectators by the followed player's
  `clientNum`: kept on purpose.
- One announced version per port; the 1.3 build has one port and the 1.0 build
  can add a second for 1.3 with `net_altPort`
  ([ADR 0001](../architecture/adr/0001-game-version-at-build-time.md)).

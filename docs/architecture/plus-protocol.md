# CoD2 Plus protocol

The contract between OpenCoD2-Plus Server's `make PLUS=1` build and OpenCoD2-Plus.
This file is the source of truth; OpenCoD2-Plus follows it. The decision is
[ADR 0012](adr/0012-plus-leaves-1-3-out.md), which builds on
[ADR 0011](adr/0011-plus-protocol.md); since
[ADR 0015](adr/0015-plus-as-a-build-variant.md) it is a build variant, not a
branch.

| Field | Value |
|---|---|
| Name | CoD2 Plus; players read "1.3 Plus" ([ADR 0014](adr/0014-name-1-3-plus.md)) |
| Plus version | 123 |
| Base | The 1.3 build, as `make PLUS=1` (`COD2_PLUS`) |
| State | Third version: milestones 0 and 2 are done, milestone 1 lacks a player on the internet, and milestone 3's format is in and lacks a real match |

## Goals

- Plus plays better than stock can: a tick rate of 40–60 Hz first, and the
  network to carry it.
- A player on an old client always learns why they cannot join, and what to do.
- The Plus client keeps joining stock 1.3 servers.

## Non-goals

- A second master server, or a new listing.
- Keeping 1.3 clients on a Plus server: `master` serves them.
- 1.0 clients: they stay on `master`.

## Anti-goals

These would make the work a failure even if it ran:

- A game that plays at another speed: a second of script stays a second.
- A Plus client that cannot join a stock server.
- A player refused with no explanation.
- A server that trusts anything because a client claims to be Plus.

## Numbers

Stock uses 115 (1.0) and 118 (1.3), Game Pass 119, CoD2x 120. CoD2x clients
drop info replies whose `protocol` is not 118 or 120, so a server announcing a
Plus version would vanish from their browser. It is therefore never announced:
`protocol` stays 118, and the Plus version only appears in the handshake.

## Handshake

The server still announces protocol 118 and version 1.3, so it stays in every
list, and no client needs to look at a server before connecting.

1. The Plus client always sends a `plus` key in the `connect` userinfo, with
   its Plus version, next to the usual `protocol\118`. Stock servers do not
   read it. The key is set for that packet only, not as a user variable.
2. The server compares it with its own Plus version.
   - Equal: it answers `connectResponse 123`, and the client slot stores the
     version, which chooses the format of that client's snapshots.
   - Anything else, or no key: it refuses the client with the update notice.
3. The client keeps no state from the answer: each snapshot says its format
   ([Format](#format)). A bare answer comes from a stock server.

Every incompatible change raises the Plus version.

A client that lies gets a format it cannot read, and hurts nobody else. The
server's Plus decoder treats everything a client sends as hostile, like the
rest of the network code, and the value only ever selects a format.

## Update notice

The refusal is an `error` packet with the text, as the ban messages in
`SV_DirectConnect` (`src/server/sv_client_mp.cpp`), so stock clients show it on
screen and it needs nothing from them. It goes out after the challenge is
checked, so a spoofed address gets no reply, and bots and local clients do not
pass through it. Only the `PLUS=1` build refuses; every other build takes
stock clients. The default text asks for the current
client, because it also reaches Plus clients of another version, and links to
the OpenCoD2-Plus releases.

`sv_plusNotice` holds the text, for admins who need another language or link,
and an empty value restores the default.

The read-only `sv_plus` dvar holds `PLUS_VERSION` in this build only, so a
mod can require it with `getCvarInt("sv_plus")`. It is not in serverinfo
nor in info replies: the version still travels only in the handshake.

## Format

Version 122 changes one thing. A Plus snapshot has its own message byte,
`svc_snapshotPlus` (8, after `svc_EOF`, so that the stock numbers stay), and is
the same as `svc_snapshot` except for the changed `pos.trTime` of an entity: a
bit that is 1 when 11 bits follow, the snapshot's time minus `pos.trTime`, and
that is 0 when the stock encoding of the field follows, for a time ahead of the
snapshot or 2,048 ms or more behind it. Gamestate baselines, archived entities
and everything else stay stock.

The byte is what makes a message readable alone: a demo plays with no record of
the server, a stock server never sends it, and the client's local game, which
has its own server code, keeps writing `svc_snapshot`.

`src/qcommon/plus_format.h` holds the offset and is vendored; each side has its
own field code, `MSG_WriteDeltaField` here and `MSG_ReadDeltaField` there.

## Version 123

Version 123 keeps the format and changes how the game plays: rules for bugs
that zPAM Plus used to fix from GSC, where a script fix fights the client's
prediction or relies on a client dvar the player can set. They apply only
between a Plus server and a Plus client: the server passes them to pmove for a
client whose slot gets Plus snapshots (`pmove_t.plusRules` in
`ClientThink_real`, `src/game/g_active_mp.cpp`, from
`plusVersion == PLUS_VERSION`), and the client predicts with them while its
snapshots are `svc_snapshotPlus`. Bots, other builds and the client against a
stock server play stock. A mod tells them apart with
`getCvarInt("sv_plus") >= 123`, and keeps its own fixes below that.

| Rule | Where | zPAM fix it replaces |
|---|---|---|
| Fast reload: a bolt-action's weapon switch taken back during the drop raises it again (it went straight back to ready; a drop for a ladder or a mantle that ends before the weapon is down does too), and a reload that cuts a bolt-action's shot keeps the shot's time left on the reload and its bolt | `PM_Weapon_FinishWeaponChange`, `PM_Weapon_CheckForReload` (`src/bgame/bg_weapons.cpp`) | `_fast_reload.gsc` (`cg_weaponCycleDelay`) |
| Prone peek: going prone while leaning, the lean comes back to the prone limit (half the crouch one) at the rate of a lean let go; it halved in one frame, so the head and hitbox jumped to the middle faster than the body went down | `PM_UpdateLean` (`src/bgame/bg_pmove.cpp`) | `_prone_peek_fix.gsc` (`linkto` for 0.4 s) |
| MG clip: leaving a turret keeps the player where using it put them, behind the gun, when a standing box fits there; they went back to where they stood when they took it, so a turret let them peek from behind cover. Not predicted: the server places them | `G_ClientStopUsingTurret` (`src/game/g_misc_mp.cpp`) | `_mg_fix.gsc` (`setOrigin` 40 units behind) |

| Climbing sound: going onto a ladder or into a mantle raises no weapon (`EV_RAISE_WEAPON` with weapon 0), which the climber's cgame played with its old weapon (`weap_raise`, as stock weapon files have no `raiseSound`) and others with nothing; the Plus client plays `weap_raise` for it, so everyone hears it. Client only: this server sends the same events | OpenCoD2-Plus's cgame | `_climbing_sound_fix.gsc` |

`scripts/plus_rules_test.py` checks each server rule against a minimal Plus
client; OpenCoD2-Plus checks the climbing sound with a real client.

## Where the format changes

- Server to client: `SV_SendMessageToClient` in
  `src/server/sv_snapshot_mp.cpp` compresses with `MSG_WriteBitsCompress` in
  one place, per client.
- Client to server: `SV_ExecuteClientMessage` in
  `src/server/sv_client_mp.cpp` decompresses with `MSG_ReadBitsCompress`.
- New format code goes in new files under `src/qcommon`, with no engine types
  in their interface, so that OpenCoD2-Plus can vendor and compile them
  unchanged. Today each side has its own message code (`src/qcommon/msg_mp.cpp`
  here, the engine's own `msg_mp.c` there); this avoids writing a format twice.
- A compression library counts as a vendored library: it is asked for first,
  under `src/`, and carries no runtime dependency.
- Each message decodes on its own, with no state between packets: packets get
  lost, and a demo can start at any moment.
- A demo recorded on a Plus server plays on the Plus client; whether stock
  clients can play it is left for milestone 3.
- Only the Plus format exists on a Plus server, but the stock path stays for
  every other build: Plus code goes behind `#ifdef COD2_PLUS` and leaves the
  stock code as it is.

## Milestones

| # | Work | Done when |
|---|---|---|
| 0 | Measure the network and the tick rate | Done, below |
| 1 | Script time and game logic independent of `sv_fps`, at 40 Hz first | The checks in [Tick rate](#tick-rate) pass at 20 and 40 |
| 2 | Handshake, refusal and notice, no format change | Done on 2026-11-01: a real 1.3 client and a real CoD2x client are refused with the notice, and the Plus client joins a Plus server and the original 1.3 executable run as a dedicated server |
| 3 | A format that carries the tick rate: the [offset](#format) | In; left to do, measured in a real match at 40 Hz |

The gate of the first version of this document (20% less, one point of a core)
is gone: at 60 Hz a client needs about 25 KB/s, right at the `rate` limit of
25000, so the question is what fits. Milestone 3 chose from
[its measurements](#milestone-3-measurements) at 40 Hz: the offset alone, as it
needs no library, and a shorter code can follow once real offsets are known.

Stability work that is not about the protocol goes to `master` when it is a
fix for stock clients too.

## Tick rate

Measured on 2026-10-31 with `sv_fps` alone, on the 1.3 build: 60 protocol
clients and 4 bots on `mp_toujane`, in tdm, over loopback.

| `sv_fps` | Real rate | CPU of one core | Per client | Total out | `wait 1` lasts |
|---|---|---|---|---|---|
| 20 | 20 Hz | 12.1% | 8.3 KB/s | 496 KB/s | 1.00 s |
| 40 | 40 Hz | 21.5% | 17.4 KB/s | 1,046 KB/s | 0.50 s |
| 60 | 62.5 Hz | 29.8% | 24.6 KB/s | 1,475 KB/s | 0.32 s |

The rate is `1000 / sv_fps` in whole milliseconds: 40 (25 ms) and 50 (20 ms) are
exact, 60 is not. The test clients only walk, so a real fight costs more.

`wait` now follows the frame rate, and `sv_fps` still defaults to 20. With 20
clients and 20 bots, 100 `wait 0.05` and 10 `wait 1` took:

| `sv_fps` | 100 × `wait 0.05` | 10 × `wait 1` |
|---|---|---|
| 20 | 5,000 ms | 10,000 ms |
| 40 | 5,000 ms | 10,000 ms |
| 60 | 4,800 ms | 10,080 ms |

40 Hz was the first target, because it divides the 50 ms steps that game code
still took per frame or per think. It did not hold for the turrets: a manned MG
took 50 ms off its time between shots every frame, so at 40 Hz it fired twice
as fast, and three times at 62.5 Hz (once a frame); the sound of its fire ended
as early. An unmanned turret thought every 50 ms, every 64 at 62.5 Hz, and
turned back 22% slower; a `trigger_hurt` hurt every 60 or 64 ms at 50 or 62.5 Hz.

In the `PLUS=1` build these follow the frame: the turrets think every frame and
step by `level.frameTime`, a manned MG keeps the time past its last shot so a
frame that does not divide `fireTime` keeps its rate, and a `trigger_hurt` that
is touched hurts on a 50 ms (or 1 s) grid (`src/game/g_misc_mp.cpp`,
`src/game/g_trigger_mp.cpp`). At 20 Hz they do what they did. Server code
only, so the Plus version stays 123. `plus_rules_test.py --only mg_rate --fps N`
checks the MG at 50 ms a shot and the turret at 200 degrees a second; other
builds fail it above 20 Hz. The stock maps' `trigger_hurt` are death zones,
where the rate does not show; its grid was not run.

What is left at 62.5 Hz: a `wait 0.05` lasts 48 ms, three frames, so a script
loop of `wait 0.05` runs 4% faster.

Checked and left alone: the 50 ms step in `SpectatorClientEndFrame` searches
back through the archive and does not set the killcam's speed;
`src/game/g_items_mp.cpp` scales its speed by its own 50 ms; `FRAMETIME` is
100 and is not a server frame. `NUM_ARCHIVED_FRAMES` holds 60 s at 20 Hz,
30 s at 40 and 19 s at 62.5.

The archive, which the antilag and the killcam read, counted `sv_fps` frames a
second (`SV_GetCachedSnapshot`, `src/server/sv_snapshot_mp.cpp`), while a frame
lasts `1000 / sv_fps` whole milliseconds: at 62.5 Hz a second back was 960 ms,
so the antilag put a player where they were up to two frames after the shot.
It now counts whole frames, in every build; at 20 and 40 Hz nothing changes.
`plus_rules_test.py --only archive_time --fps N` follows a moving bot a second
back.

Plus servers are named by their rate, 20, 40 or 60 Hz, and the admin sets it
for everyone: on a Plus server `sv_fps` alone is the setting. A stock client
asks for 30 snapshots a second at most and its `rate` stops at 25000, so the
server sets a Plus client's own (`SV_PlusRate`, `src/server/sv_snapshot_mp.cpp`):
a snapshot every frame, and 1,000 bytes a second per Hz, but no less than
25,000 (25,000 at 20 Hz, 40,000 at 40, 62,500 at 62.5). It ignores the
client's `rate` and `snaps` and `sv_maxRate`, which stops at 25000.
`g_forceSnaps` and `g_forceRate` still set them by hand. They are read for each
message, so a change by rcon takes effect at once; the stock code reads them
when the client connects or changes its userinfo. LAN clients still get every
frame with no rate unless `sv_lanForceRate` is 0 (ioquake3's name, `PLUS=1`
only). Server code only: the Plus version stays 123.

30 Hz is left out: a frame of 33 ms makes `wait 0.05` two frames, 66 ms, so
scripts that loop on it would run 32% slower. 50 Hz rounds it to 40 or 60 ms.

Before `SV_PlusRate`, 40 Hz took `g_forceSnaps 40` and `g_forceRate 40000`
with `sv_maxRate` at 0. A `rate` of 25000 keeps the average but delays the
largest messages: at 40 Hz it fits 577 bytes, and 10% of them reach about 770.

Measured with the LAN exemption of `SV_SendMessageToClient` removed, as a client
on the internet sees it, with 20 clients and 20 bots:

| Setting | Snapshots a second | Per client |
|---|---|---|
| 20 Hz, stock | 21.3 | 5.9 KB/s |
| 40 Hz, the client's settings | 21.2 | 7.3 KB/s |
| 40 Hz, `g_forceSnaps 40`, `g_forceRate 25000` | 41.5 | 11.7 KB/s |
| 40 Hz, `g_forceSnaps 40`, `g_forceRate 40000` | 41.2 | 14.9 KB/s |
| 40 Hz, `g_forceSnaps 40`, `g_forceRate 60000` | 42.2 | 14.6 KB/s |

The bytes vary with each match, so compare the snapshots.

The rest of milestone 1:

- Bots pass in tdm and sd at 40 Hz. The OpenCoD2-Plus client reported 0
  prediction misses at 60 fps and 1 at 125 fps. Its check that the client moves
  fails at 125 fps at 20 Hz too, because the moves are counted in client frames.
- The maintainer played on a public 1.0 build of this branch at 40 Hz on
  2026-11-01, with no difference from 20 Hz in the game's pace. That run came
  from close by, so it may have had the LAN exemption.
- Still to check: a player on the internet, and whether 40 Hz feels better.

## Milestone 0 results

Measured on 2026-10-31 with the 1.3 build: 20 protocol clients and 20 bots in
tdm, on `mp_toujane` and `mp_carentan`, about 90 s each with 65 to 113 kills.
Bytes are the server's output per message, without 28 bytes of IP and UDP. The
test clients only walk and all ran over loopback, so `rate` did not space the
snapshots.

Entities are 86–90% of a message and the playerstate 8–12%. Huffman takes off
only 4–7% of the raw bytes, because the data is already packed in bits.

The biggest saving needed no new format. `MSG_WriteDeltaField` in
`src/qcommon/msg_mp.cpp` compared the field pointers, not their values, so an
unchanged field was sent in full; 47–49% of the fields written were unchanged.
Fixed on `master`. Written both ways on the same snapshots:

| Map | Messages | Before | Comparing values | Largest 10% of messages |
|---|---|---|---|---|
| `mp_toujane` | 41,049 | 499 bytes | 396 (−20.5%) | 978 to 772 |
| `mp_carentan` | 42,658 | 386 bytes | 309 (−19.8%) | 853 to 679 |

What a new format would add on top, against Huffman with values compared.
Tables were trained on one map and tested on the other; the time is one
compression, on one core:

| Candidate | Saves | Time | Table |
|---|---|---|---|
| New order-0 Huffman table | 4.7–5.4% | none extra | 256 entries |
| zlib 6 | 6.1–7.8% | 18 µs | none |
| zlib 6 with a raw dictionary | 7.2–8.7% | 56 µs | 32 KB |
| lz4 | −1.5 to −2.8% (larger) | 0.7 µs | none |
| zstd 3 with a trained dictionary | 8.1–9.8% | 3 µs | 16 KB |
| zstd 9 with a trained dictionary | 12.5–14.4% | 9.6 µs | 16 KB |
| Order-1 entropy (a limit, not a codec) | 11.3–11.9% | — | 64 KB |

A recoding of the entity deltas (XOR for floats, variable length for integers)
is estimated from a bit-cost model of the same field stream, without Huffman:
26–30% below today's bytes, about 12–14% below comparing values.

No two candidates were tried together. At 64 clients and 20 snapshots a second
(1,280 messages), zstd 9 costs 1.2% of a core.

## Milestone 3 measurements

Measured on 2026-11-01 with the 1.3 build at `sv_fps` 40, `g_forceSnaps` 40 and
`g_forceRate` 40000: 20 protocol clients and 20 bots in tdm on `mp_toujane` and
`mp_carentan`, about 90 s each, over loopback. The candidates of the table above
save a little less at 40 Hz than at 20, because the messages are smaller:

| Candidate | 20 Hz | 40 Hz |
|---|---|---|
| New order-0 Huffman table | 5.3% | 4.8–5.5% |
| zstd 3 with a trained dictionary | 7.5–8.8% | 4.5–5.8% |
| zstd 9 with a trained dictionary | 11.8–13.4% | 10.1–11.2% |

| Rate | Bytes a message | 99th percentile | Over the 577 bytes of `rate` 25000 at 40 Hz |
|---|---|---|---|
| 20 Hz | 303–341 | 705–801 | not a limit at this rate |
| 40 Hz | 245–251 | 492–537 | 0.45–0.61% |

`pos.trTime` is the largest field: most entities change it in every snapshot,
and `MSG_WriteDeltaField` sends it as 32 bits, or 37–41% of the bytes that field
model counts. Written both ways on the same snapshots, sending the snapshot's
time minus `pos.trTime` in a flag and 11 bits, with no decoder behind it:

| Map | Messages | Today | With the offset | Largest 1% |
|---|---|---|---|---|
| `mp_toujane` | 127,768 | 262 bytes | 233 (−11.0%) | 539 to 498 |
| `mp_carentan` | 127,877 | 214 bytes | 187 (−12.6%) | 417 to 381 |

That matches zstd 9 with one field, no library and no dictionary. Of the offsets,
0.3–0.5% needed the escape, up to 123 s old, and none was negative. For a player
`pos.trTime` is `ps.commandTime`, so the common offsets of whole frames, 25 ms for
bots and about 1,025 ms for test clients, come from how those send commands: a
code shorter than 11 bits has to wait for a real match. The rest of the bytes are mostly the floats in
`pos.trBase`, `pos.trDelta` and `angles2`, which XOR barely shrinks.

The per-field bit model of `.fld` counts each field three times, because the
paired writes log too: its shares hold, and comparing them with bytes on the
wire does not.

## Two repositories

| Step | Where |
|---|---|
| A fix or a protocol change starts on `dev`; a protocol change comes with this file and stays behind `COD2_PLUS` | OpenCoD2-Plus Server |
| It is vendored into OpenCoD2-Plus, and `test/vendored_files.txt` records the revision | OpenCoD2-Plus |
| The client follows, and is tested against that server | OpenCoD2-Plus |
| A release is the same tag in both, the server first | Both |

- Code flows one way: from here to OpenCoD2-Plus, never back. Which of its
  branches vendor `dev` or `master` is decided there.
- A fix found while working on the client is made here first
  ([its vendoring guide](https://github.com/JotaJazz/OpenCoD2-Plus/blob/main/docs/development/vendored.md)).
- A release tags `master` once for every build, Plus included.

## Before a public release

A Plus server only takes the Plus client, and OpenCoD2-Plus cannot be
distributed yet: it has no license, and its docs exclude distributing binaries.
A release of this branch has to wait for that.

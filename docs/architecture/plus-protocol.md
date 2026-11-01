# CoD2 Plus protocol

The contract between the `plus` branches of CoD2rev-Plus and OpenCoD2-Plus.
This file is the source of truth; OpenCoD2-Plus follows it. The decision is
[ADR 0012](adr/0012-plus-leaves-1-3-out.md), which builds on
[ADR 0011](adr/0011-plus-protocol.md).

| Field | Value |
|---|---|
| Name | CoD2 Plus |
| Plus version | 121 |
| Base | The 1.3 build (`make PROTOCOL=118`) |
| State | Draft, second version: nothing is implemented; milestone 0 is measured |

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
drop info replies whose `protocol` is not 118 or 120, so a server announcing
121 would vanish from their browser. The number is therefore never announced:
`protocol` stays 118, and 121 only appears in the handshake.

## Handshake

The server still announces protocol 118 and version 1.3, so it stays in every
list, and no client needs to look at a server before connecting.

1. The Plus client always sends a `plus` key in the `connect` userinfo, with
   its Plus version, next to the usual `protocol\118`. Stock servers do not
   read it. The key is set for that packet only, not as a user variable.
2. The server compares it with its own Plus version.
   - Equal: it stores it in the client slot and answers `connectResponse 121`.
   - Anything else, or no key: it refuses the client with the update notice.
3. The client uses the Plus format only if the answer's argument equals its
   own version. A bare answer comes from a stock server, and means 1.3.

Every incompatible change raises the Plus version.

A client that lies gets a format it cannot read, and hurts nobody else. The
server's Plus decoder treats everything a client sends as hostile, like the
rest of the network code, and the value only ever selects a format.

## Update notice

The refusal is an `error` packet with the text, as the ban messages in
`SV_DirectConnect` (`src/server/sv_client_mp.cpp`), so stock clients show it on
screen and it needs nothing from them. The default text asks for the current
client, because it also reaches Plus clients of another version, and links to
the OpenCoD2-Plus releases.

`sv_plusNotice` holds the text, for admins who need another language or link,
and an empty value restores the default.

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
- Only the Plus format exists on a Plus server, so the 1.3 path can go when
  it gets in the way, as long as merges from `master` stay workable.

## Milestones

| # | Work | Done when |
|---|---|---|
| 0 | Measure the network and the tick rate | Done, below |
| 1 | Script time and game logic independent of `sv_fps`, at 40 Hz first | The checks in [Tick rate](#tick-rate) pass at 20 and 40 |
| 2 | Handshake, refusal and notice, no format change | A real 1.3 client and a real CoD2x client are refused with the notice, and the Plus client joins a Plus server and a stock 1.3 server |
| 3 | A format that carries the tick rate | Measured against milestone 0 at the chosen rate, with a real match |

Milestone 3 chooses from the table below. The gate of the first version of this
document (20% less, one point of a core) is gone: at 60 Hz a client needs about
25 KB/s, right at the `rate` limit of 25000, so the question is what fits, and
the measurements have to be repeated at that rate.

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

40 Hz is the first target, because it is exact for what still works in steps of
50 ms: at 62.5 Hz a `wait 0.05` lasts 48 ms, and the turrets, which think every
50 ms (`src/game/g_misc_mp.cpp`), would wait for the next frame and turn slower.
The same goes for 50 Hz, at 60 ms a think. Going past 40 means fixing those.

Checked and left alone: the 50 ms step in `SpectatorClientEndFrame` searches
back through the archive and does not set the killcam's speed;
`src/game/g_items_mp.cpp` scales its speed by its own 50 ms; `FRAMETIME` is
100 and is not a server frame; the archive and the antilag read `sv_fps`.
`NUM_ARCHIVED_FRAMES` holds 60 s at 20 Hz and 30 s at 40.

A client asks for 30 snapshots a second at most, and the server sends them on
frame boundaries, so at 40 Hz that is 20 a second. The 40 Hz setting is
`sv_fps 40`, `g_forceSnaps 40` and `g_forceRate 40000`, with `sv_maxRate` at 0,
because it stops at 25000. A `rate` of 25000 keeps the average but delays the largest
messages: at 40 Hz it fits 577 bytes, and 10% of them reach about 770.

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

## Two repositories

| Step | Where |
|---|---|
| A fix starts on `master` and is merged to `plus` | CoD2rev-Plus |
| A protocol change starts on `plus`, with this file | CoD2rev-Plus |
| It is vendored into OpenCoD2-Plus `plus`, and `test/vendored_files.txt` records the revision | OpenCoD2-Plus |
| The client follows, and is tested against that server | OpenCoD2-Plus |
| A release is the same tag in both, the server first | Both |

- Code flows one way: from here to OpenCoD2-Plus, never back. Its `main`
  vendors `master` and its `plus` vendors `plus`.
- A fix found while working on the client is made here first
  ([its vendoring guide](https://github.com/JotaJazz/OpenCoD2-Plus/blob/main/docs/development/vendored.md)).
- `plus` tags are `plus-vX.Y.Z`, separate from the `master` releases.
- Merges go from `master` to `plus`, never the reverse. The 1.0 code stays on
  `plus`, built as today, so those merges stay clean.

## Before a public release

A Plus server only takes the Plus client, and OpenCoD2-Plus cannot be
distributed yet: it has no license, and its docs exclude distributing binaries.
A release of this branch has to wait for that.

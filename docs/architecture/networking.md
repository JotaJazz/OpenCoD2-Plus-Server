# Networking

## Path of a packet

```
Com_EventLoop                    src/qcommon/common.cpp (sockets: src/unix/unix_net.cpp, src/win32/win_net.cpp)
└─ SV_PacketEvent                src/server/sv_main_mp.cpp
   ├─ SV_ConnectionlessPacket    getinfo, getstatus, getchallenge, connect, rcon, ipAuthorize…
   │  ├─ SV_DirectConnect        src/server/sv_client_mp.cpp
   │  └─ SVC_RemoteCommand       src/server/sv_main_pc_mp.cpp
   └─ Netchan_Process            sequence, fragments
      └─ SV_ExecuteClientMessage src/server/sv_client_mp.cpp: commands, usercmds, downloads
```

Outgoing: `SV_SendClientMessages` → `SV_BuildClientSnapshot`
(`src/server/sv_snapshot_mp.cpp`) → `Netchan_Transmit` /
`Netchan_TransmitNextFragment`. Bit and byte encoding, delta compression and
Huffman: `src/qcommon/msg_mp.cpp`.

## Protocols

| Protocol | Client | Build that accepts it |
|---|---|---|
| 115 | 1.0 | 1.0 build |
| 116, 117 | — | 1.0 build with libcod (range check only, untested) |
| 118 | 1.3, CoD2x 1.4 | 1.3 build; 1.0 build with libcod |
| 119 | Game Pass | 1.0 build with libcod (untested here) |

- The build's own version is `PROTOCOL_VERSION`; it is what the server
  announces to the master servers.
- The 1.0 build with libcod keeps the client's protocol in
  `netchan.protocol` and switches formats per client: fragment offsets are a
  long for 118 and a short otherwise (`Netchan_Process`,
  `Netchan_TransmitNextFragment`), and 119 has one stat less in the
  playerstate (`src/qcommon/msg_mp.cpp`).
- The `make PLUS=1` build serves only the Plus client
  ([plus-protocol.md](plus-protocol.md)).
- `net_altPort` (1.0 build) opens a second socket: `netadr_t.altPort` marks
  what came through it, so replies, challenges and netchans leave by the same
  socket with no other change. `getinfo` and `getstatus` there announce 118
  and 1.3, and heartbeats go out from both ports, so the masters list two
  servers for one game. Any accepted protocol joins through either port.
- A shared match needs data both clients have: run the server without
  `iw_15.iwd`. It overrides 33 stock files and is referenced on every map,
  and 1.0 clients do not have it nor can download it. `mp_rhine` and
  `mp_harbor` still work from a separate iwd with only their 15 files (the
  names with `rhine` or `harbor`). 1.3 clients fetch it over HTTP with
  `sv_wwwDownload`; the 1.0 client has no HTTP download, about 20 KB/s in game.
- Set `sv_wwwBaseURL` in a cfg, in quotes: on the command line or over rcon
  the `//` starts a comment and leaves `http:`.
- `make PLUS=1` on Linux: `sv_wwwBaseURL auto` makes the server itself the
  HTTP side, on TCP on the game port, for Plus clients only (open the port in
  TCP too in the router). Others get the UDP download. See
  [plus-protocol.md](plus-protocol.md#downloads).
- `MAX_MSGLEN` is `0x20000` in the 1.3 build and `0x4000` in the 1.0 build;
  packets are at most `MAX_PACKETLEN` (1400) bytes, fragments `FRAGMENT_SIZE`
  (1300).

## Hardening rules

The fixes are listed in [../CHANGES.md](../CHANGES.md#security-and-stability).
New code that reads from the network follows them:

- Every length read from a message is checked against the destination buffer
  before it is used (compressed sizes, fragment offsets and lengths, strings,
  voice packets).
- Connectionless commands that answer with data (`getinfo`, `getstatus`,
  `getchallenge`, `rcon`) go through `SVC_RateLimitAddress` (per address) and
  `SVC_RateLimit` (global: `getinfo` 100 a second, `getstatus` 10, each its
  own, and neither for the masters, which also get this server's status
  unasked whatever the limits); `connect` has the per-address one, on LAN too but
  for `127.0.0.1`, which is where a local proxy's players come from;
  `ipAuthorize` and `disconnect` have none. The global `getchallenge` limit
  keeps the 1024-slot table from turning over faster than a join takes, so an
  address that asks again within 10 seconds gets 20 a second of its own:
  otherwise a flood of made-up addresses keeps every player out.
- A challenge is signed for its address and port (`SV_ChallengeCookie`), so a
  `connect` whose slot is gone still gets one. Where no authorize step applies,
  or with `sv_challengeStateless 1`, `getchallenge` answers with the signature
  alone, takes no slot and skips the global limit; the `connect` takes the slot
  and asks the authorize server
  ([ADR 0018](adr/0018-signed-challenges.md)).
  rcon also counts wrong passwords per address (`sv_rconMaxAttempts`,
  `sv_rconLockTime`), and its global limit runs before the password check;
  `sv_rconWhitelist` skips both limits. A new connectionless command that
  answers gets the same rate limits.

- A gamestate a client can ask for (`donedl`, `wwwdl fail`, a dropped one) goes
  through `SV_SendRequestedGameState`: 5 at once, then 1 a second per slot. A
  refused one goes out from a later packet of the client, so a client that
  waits for it does not time out.
- Text from players never becomes a format string; `-Wformat` and the
  printf attributes catch it at build time.
- The `ip` userinfo key (real address behind a local proxy) is trusted only
  from `127.0.0.1`.
- Downloads refuse the stock `iw_*.iwd` and server-only `_svr_` files.

## Known gaps

- `sv_pure` only proves a client has the server's iwds: clients report just
  the iwds they have read from, and the pure checksums can be computed from
  the stock files, so it cannot detect extra iwds. Protocol 119 skips the
  check. See [../roadmap/debt.md](../roadmap/debt.md).
- The protocol 119 fragment offset format is not verified against a real
  client.

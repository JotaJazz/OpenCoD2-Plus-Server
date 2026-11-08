# Plus ID

A player identity that a client proves with a signature at connect, in every
build with libcod ([ADR 0019](adr/0019-plus-id.md)). The OpenCoD2-Plus client
keeps an ECDSA P-256 key pair and signs each connect; the server checks it and
gives the player an ID that no one else can take. No hardware data is sent.
The Plus version stays 123: the keys are optional, and servers that do not know
them ignore them.

| Field | Value |
|---|---|
| Curve, hash | P-256 (secp256r1), SHA-256 |
| Shared code | `src/libcod/plusid.hpp` (inline, no engine headers, no state); the client vendors it |
| Server code | `src/libcod/plusid.cpp`, hooks in `SV_DirectConnect` and `SV_FreeClient` |
| Test | `scripts/plusid_test.py` ([testing](../development/testing.md)) |

## Handshake

No new messages: after `getchallenge` → `challengeResponse <n>`, the client
adds three keys to the userinfo of `connect`, only in that packet:

| Key | Content |
|---|---|
| `pk` | public key, compressed point, 33 bytes as 66 lowercase hex characters |
| `ps` | signature, raw r‖s, 64 bytes as 128 lowercase hex characters |
| `pa` | the server address the client signed, `ip:port` as `NET_AdrToString` writes it |

The signed bytes are SHA-256 of the text

    cod2plus-id-v1|<challenge>|<pa>

where `<challenge>` is the decimal of the signed int in `challengeResponse`
(it may be negative). The challenge ties the signature to one connect attempt;
the address ties it to one server, so a server that passes it on to another
gets nothing.

The ID is `P-` and the base32 (RFC 4648, `A-Z2-7`, no padding) of the first 10
bytes of SHA-256 of the 33-byte `pk`, in four groups of four:
`P-XXXX-XXXX-XXXX-XXXX`.

## Server side

`PlusId_CheckConnect` runs in `SV_DirectConnect` after the challenge and the
ban check, so a forged source address costs no ECDSA work, and after
`SV_DirectConnect`'s limit of connects per address. It takes `pk`, `ps` and `pa`
out of the userinfo (scripts and `dumpuser` never see them), then:

1. `pa` must be a numeric `ip:port` in `NET_AdrToString`'s exact form, so it is
   never resolved and the text checked is the text signed.
2. The address rule below must accept `pa`.
3. At most 50 verifications a second for all addresses together.
4. The signature must verify.

A player who fails any step plays without an ID, and the log says why
(`plusid: invalid signature from <ip:port>`, `plusid: <ip:port> signed for
another address, <pa>`...). With `sv_requirePlusId 1` a player without an ID
is refused with `sv_plusIdNotice`. The server never refuses for how old an ID
is. Bots and local clients have no challenge and no ID.

### Address rule (`PlusId_AddressAccepted`)

In order, where "private" means 10/8, 127/8, 169.254/16, 172.16/12 or
192.168/16 (`PlusId_IsPrivate`):

1. The signed port must be the server's `net_port`.
2. A private signed IP with a connect from a public address: reject, even when
   it is `net_ip` or `sv_publicAddress`.
3. The signed IP is that of `sv_publicAddress`, or of `net_ip` when it names
   an address (not empty, `localhost` or `0.0.0.0`): accept.
4. The signed IP is private (and so, by step 2, is the source): accept.
5. Anything else: reject.

Step 2 stops a relay: a server on a VPN (Radmin, Hamachi) with the same
private IP as this one could otherwise pass on a signature from its public
address. The predicate is not `Sys_IsLANAddress`, which also takes anyone in
the /24 of one of the host's own IPs, so a neighbour there (a shared VPN's
26.x or 25.x) could relay from its own address. Local tests cannot show it
(every test address is private); `plusid_test.py`'s `address_rule` checks the
same table on a Python copy of the rule.

Without `sv_publicAddress` and a concrete `net_ip`, only LAN players can get an
ID, and the first map prints
`plusid: no sv_publicAddress, only LAN players get a Plus ID`. A server behind
NAT must set it to the address players dial.

### Dvars and commands

| Name | Default | Effect |
|---|---|---|
| `sv_publicAddress` | `""` | `ip:port` players reach the server at; a host name is resolved once, at the first connect after it changes |
| `sv_requirePlusId` | `0` | `1` refuses players without a valid ID |
| `sv_plusIdNotice` | `""` | refusal text; empty uses a default with the link to the client |
| `sv_plusIdSeenFile` | `plusid_seen.txt` | playtime file, relative to `fs_homepath` or an absolute path |
| `plusIdStatus` | command | one line per player: `num name id playtime first_seen_ago flags`, `-` without an ID or a flag |
| `banPlusId <id\|clientnum> <minutes> <reason...>` | command | bans an ID (`minutes` 0 is permanent) and drops it; a number is a client slot, whose guid and IP are kept in the ban; `by` is `rcon` |
| `unbanPlusId <id>` | command | lifts a local ban |

Scripts read a player's ID with `self getPlusId()` (`""` without one), the
seconds it has played with `getPlusIdPlaytime()` and the seconds since it was
first seen with `getPlusIdFirstSeen()` (both `0` without an ID).
`getPlusIdFlags()` is `""`, `"guid"`, `"ip"` or `"guid,ip"` (see Local bans).

### Local bans

`plusid_bans.json` in `fs_homepath`: `{"format": 1, "entries": [...]}`, each entry
`id`, `reason`, `by`, `evidence`, `date` and `expires` (Unix seconds, `null` is
permanent), plus `guid` (0 is none) and `ip` ("" is none), which only local bans
have. It is written through `<file>.tmp.<pid>` and a rename, and read again when
its size or time changed, so an edit applies at the next connect. The file is
read as hostile: an entry with a bad ID, type or length (reason 127, by 63,
evidence 255 characters) rejects the whole file, the bans in memory stay and the
log says `plusid: cannot read <file>`. An expired ban (`expires` passed) is
ignored, not deleted.

`PlusId_CheckConnect` looks the verified ID up (`PlusId_FindBan`) before the
`sv_requirePlusId` check and refuses with `You are banned from this server:
<reason>`; `banPlusId` also drops that ID when connected (`PlusId_KickBanned`).
Only slots in CS_CONNECTED or later count; a zombie keeps its ID until freed.
A player whose guid (non-zero) or IP equals that of a live ban of another ID gets
the flag `guid` and/or `ip`, kept for the slot and logged as `plusid: possible
evasion <new> matches <banned> by ip`. The player is not refused. The older
GUID/IP bans (`banUser`, `ban.txt`, `SV_IsBannedIp`) are separate and unchanged.

### Playtime

Players with an ID (never bots or players without one) are counted while the
slot is connected. The seen file has one line per ID, `id first_seen seconds`
(decimal integers, `first_seen` a Unix time). It is saved every 60 s, when a
player drops, at the end of the map and at shutdown. A save re-reads the file,
keeps the smallest `first_seen` and adds only the seconds this server counted
since its last save, then writes `<file>.tmp.<pid>` and renames it over the file. So
several servers can share one file (an absolute `sv_plusIdSeenFile`) and keep
each other's time; two saving in the same instant can lose one interval. Time that cannot be written stays pending and the next save retries it. A file
that exists but cannot be read is never overwritten: the server logs
`plusid: cannot read <file>, playtime not saved`. The server never refuses or
treats a player differently for how old an ID is.

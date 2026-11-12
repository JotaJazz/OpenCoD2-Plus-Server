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
| Server code | `src/libcod/plusid.cpp`, hooks in `SV_DirectConnect` and `SV_FreeClient`; shared ban lists in `src/libcod/plusid_lists.cpp` |
| Maintainers' tool | `scripts/banlist.py` (shared ban lists) |
| Test | `scripts/plusid_test.py`, `scripts/test_banlist.py` ([testing](../development/testing.md)) |

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

1. A private signed IP with a connect from a public address: reject, even when
   it is `net_ip` or `sv_publicAddress`.
2. The signed IP is that of `sv_publicAddress` and the signed port is the one
   that dvar names, or `net_port` when it names none: accept. A port there is
   the one players dial when it is not the server's own (`docker -p
   28961:28960`, a NAT remap).
3. The signed port is not `net_port`: reject.
4. The signed IP is that of `net_ip` when it names an address (not empty,
   `localhost` or `0.0.0.0`): accept.
5. The signed IP is private (and so, by step 1, is the source) and is this
   host's: 127/8 or one of its own IPs (`Sys_IsLocalIP`, the private IPv4s
   of its interfaces that `NET_GetLocalAddress` found at startup): accept.
6. Anything else: reject.

Step 1 stops a relay: a server on a VPN (Radmin, Hamachi) with the same
private IP as this one could otherwise pass on a signature from its public
address. Step 5 stops another host of the LAN from passing on a LAN player's
signature for its own address. The predicate is not `Sys_IsLANAddress`, which
also takes anyone in the /24 of one of the host's own IPs, so a neighbour there
(a shared VPN's 26.x or 25.x) could relay from its own address. Local tests
cannot show the relays (every test address is private); `plusid_test.py`'s
`address_rule` checks the same table on a Python copy of the rule.

Without `sv_publicAddress` and a concrete `net_ip`, only LAN players can get an
ID, and the first map prints
`plusid: no sv_publicAddress, only LAN players get a Plus ID`. A server behind
NAT must set it to the address players dial. In a container behind Docker's
bridge NAT the LAN IP players dial is the host's, not one of the container's,
so LAN players get an ID only when `sv_publicAddress` or `net_ip` is that LAN IP.

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
| `sv_banLists` | `""` | shared ban lists, `url|pubhex[;url|pubhex...]`, up to 8 (see Shared ban lists) |
| `sv_banListRefresh` | `30` | minutes between fetches of each list, 1 to 10080 |
| `banListStatus` | command | one line per list: `num url "name" entries updated status`, where status is `ok`, `fetching` or the last error |

Scripts read a player's ID with `self getPlusId()` (`""` without one), the
seconds it has played with `getPlusIdPlaytime()` and the seconds since it was
first seen with `getPlusIdFirstSeen()` (both `0` without an ID).
`getPlusIdFlags()` is `""`, `"guid"`, `"ip"` or `"guid,ip"` (see Local bans).

### Local bans

`plusid_bans.json` in `fs_homepath`: `{"format": 1, "entries": [...]}`, each entry
`id`, `reason`, `by`, `evidence`, `date` (`YYYY-MM-DD`, UTC) and `expires`
(`YYYY-MM-DDTHH:MM:SSZ`, or `null` for permanent; a date alone also reads, as
00:00 UTC; years 1970 to 9999, also on the 32-bit build; it must come after
`date`, absent as 1970-01-01), plus `guid` (0 is none) and `ip` ("" is none), which only local bans
have. It is written through `<file>.tmp.<pid>` and a rename, and read again when
its size or time changed, so an edit applies at the next connect. The file is
read as hostile: an entry with a bad ID, type or length (reason 127, by 63,
evidence 255 characters) rejects the whole file (any other date format too), the bans in memory stay and the
log says `plusid: cannot read <file>`; so does a file that is there but cannot
be stat'ed (a permission, a symlink loop), which is not a missing one. A `"` in
a text is read as `'`, so it cannot end the quoted refusal. While the file is bad, `banPlusId` and
`unbanPlusId` refuse (`plusid: cannot read <file>, fix it first`) and never
overwrite it; a file that reads again clears that. An expired ban (`expires` passed) is
ignored, not deleted.

`PlusId_CheckConnect` looks the verified ID up (`PlusId_FindBan`: local bans
first, then the shared lists) before the
`sv_requirePlusId` check and refuses with `You are banned from this server:
<reason>`; `banPlusId` also drops that ID when connected (`PlusId_KickBanned`).
Only slots in CS_CONNECTED or later count; a dropped player has no ID, which
`SV_DropClient` frees (`SV_FreeClient`) before the slot is a zombie.
A player whose guid (non-zero) or IP equals that of a live ban of another ID gets
the flag `guid` and/or `ip`, kept for the slot and logged as `plusid: possible
evasion <new> matches <banned> by ip`. The player is not refused. The older
GUID/IP bans (`banUser`, `ban.txt`, `SV_IsBannedIp`) are separate and unchanged.

### Playtime

Players with an ID (never bots or players without one) are counted while the
slot is connected. The seen file has one line per ID, `id first_seen seconds`
(decimal integers, `first_seen` a Unix time). The server keeps it in memory, a
table by ID: a connect takes the player's time from it (and from the time of
an earlier visit not saved yet) and a drop only marks its seconds pending,
with no file I/O. It is saved every 60 s, at the end of the map and at
shutdown, so a drop reaches the file within a minute. A save takes
`<file>.lock` (created exclusively; one older than 10 s is a crash's and is
taken over; a busy lock puts the save off 5 s, at shutdown up to 2 s), reads the
file again only when its size or time (nanoseconds on Linux) changed, keeps the
smallest `first_seen` and adds only the seconds this server counted since its
last save, then writes `<file>.tmp.<pid>` and renames it over the file. So
several servers can share one file (an absolute `sv_plusIdSeenFile`) and keep
each other's time, also when they save at the same moment; on Windows, where
the time has whole seconds, another server's write in the same second with
the same size can be missed. Time that cannot be written stays pending and the
next save retries it. A file that exists but cannot be read is never
overwritten: the server logs `plusid: cannot read <file>, playtime not saved`.
The server never refuses or treats a player differently for how old an ID is.

### Shared ban lists

A community can keep one ban list for many servers. Each list is a JSON file
at a URL and its signature at `<url>.sig`: the base64 of the raw r‖s (64
bytes) of an ECDSA P-256 signature over SHA-256 of the file's exact bytes,
made by the list's maintainer. Servers name the lists they trust with
`sv_banLists "url|pubhex;url|pubhex"`, where `pubhex` is the maintainer's
compressed public key (66 hex characters); the quotes are needed in a config
and on the command line, where `;` ends a command and `//` starts a comment.

```json
{
  "format": 1,
  "name": "CoD2 Community",
  "appeal": "https://github.com/<org>/<repo>/issues",
  "updated": "2026-11-08T12:00:00Z",
  "entries": [
    { "id": "P-ABCD-EFGH-IJKL-MNOP", "reason": "aimbot", "date": "2026-11-01",
      "expires": null, "by": "admin_handle", "evidence": "https://..." }
  ]
}
```

Entries are those of the local bans, with the same dates and lengths, but a
list never publishes `guid` or `ip`: an entry with either rejects the list,
since publishing them exposes players and would let someone with a shared CD
key frame another. `name` (up to 63 bytes) is required, `appeal` (up to 255) is
optional, `updated` uses the date format of the entries. A `"` in `name` or
`appeal` is read as `'`.

Each list is fetched on its own thread every `sv_banListRefresh` minutes, and
at once when `sv_banLists` changes; the thread never touches the engine, the
main thread takes the result in the next frame. A version is taken only whole:
a body over 4 MB, more than 100 000 entries, a bad signature, a broken or
hostile JSON, a field out of range, a network error or an `updated` older than
the copy in use (a replayed old list) all keep the last good copy, show in
`banListStatus` and log `plusid: list <url> not updated: <error>; keeping the
copy of <updated>`. An equal `updated` is accepted (the same file served
again). A good version replaces the copy in memory, is written to
`plusid_lists/<sha256 of the url in hex>.json` and `.sig` in `fs_homepath`
through `<file>.tmp.<pid>`, and drops the connected players it bans.

At startup the cached copy is verified again and applies (`plusid: list <name>
(<url>) from the cache`) until a fetch brings a newer one, so a list host that
is down does not lift its bans. A list with no good copy yet does not apply,
and the log says so at startup and at each failure; nobody is locked out.
Local bans come first; a list ban refuses with `You are banned by <name>:
<reason>. Appeal: <appeal>` (without the appeal part when the list has none).
An entry with a malformed key in `sv_banLists` is skipped with a log line.
Lists use the HTTP client of `httpFetch` (`sv_httpCaFile` for https,
`sv_httpAllowPrivate 1` for a list on a private address), but not
`sv_httpAllowedHosts`, which is for scripts.

Maintainers use `scripts/banlist.py` (the `openssl` CLI):

| Command | Does |
|---|---|
| `keygen OUT` | writes `OUT.key` (private PEM, keep it secret) and `OUT.pub` (the hex for `sv_banLists`) |
| `sign LIST KEY` | writes `LIST.sig` |
| `verify LIST PUBHEX` | exit 0 when `LIST.sig` is good for the key, 1 otherwise |
| `check LIST` | exit 0 when servers take the list's format and limits; also 1 when `updated` is more than a day in the future, which would keep servers from taking any later version |

The recommended workflow: the list lives in a GitHub repository, additions and
appeals come as pull requests (with evidence), and the maintainer runs
`banlist.py check`, signs on merge and commits the `.sig` with the list; the
raw URLs of both files go into `sv_banLists`. Only the key holder can publish a
version servers take, so the hosting can be anywhere.

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

In order:

1. The signed port must be the server's `net_port`.
2. The signed IP is that of `sv_publicAddress`, or of `net_ip` when it names
   an address (not empty, `localhost` or `0.0.0.0`): accept.
3. The signed IP is private or loopback (`Sys_IsLANAddress`) **and** the
   connect comes from a private or loopback address too: accept.
4. Anything else: reject.

Step 3's second half stops a relay: a server on a VPN (Radmin, Hamachi) with
the same private IP as this one could otherwise pass on a signature from its
public address. Local tests cannot show it (every test address is private);
`plusid_test.py`'s `address_rule` checks the same table on a Python copy of the
rule.

Without `sv_publicAddress` and a concrete `net_ip`, only LAN players can get an
ID, and the first map prints
`plusid: no sv_publicAddress, only LAN players get a Plus ID`. A server behind
NAT must set it to the address players dial.

### Dvars and commands

| Name | Default | Effect |
|---|---|---|
| `sv_publicAddress` | `""` | `ip:port` players reach the server at; a host name is resolved on each connect |
| `sv_requirePlusId` | `0` | `1` refuses players without a valid ID |
| `sv_plusIdNotice` | `""` | refusal text; empty uses a default with the link to the client |
| `plusIdStatus` | command | one line per player: `num name id`, `-` without an ID |

Scripts read a player's ID with `self getPlusId()` (`""` without one).

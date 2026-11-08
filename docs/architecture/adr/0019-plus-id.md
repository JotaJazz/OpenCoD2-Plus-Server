# 0019. A player identity proven by a signature, not by hardware

- Status: Accepted
- Date: 2026-11-08

## Context

Servers want to know a returning player: for playtime, local bans and ban
lists shared between servers. The CD key GUID is shared or cracked on most
servers, names are free text and IPs change. Identities built from hardware
data (a HWID) can be spoofed by the client that computes them, and send personal
data to every server.

## Decision

The OpenCoD2-Plus client keeps an ECDSA P-256 key pair and, at each connect,
signs the server's challenge and the address it dials; the server verifies it
and derives the Plus ID from the public key
([plus-id.md](../plus-id.md)). The keys (`pk`, `ps`, `pa`) are optional userinfo
keys of `connect`, so the Plus version stays 123 and every build with libcod
checks them, not only `make PLUS=1`. The signing code is a header with no
engine dependencies that the client vendors.

## Consequences

- No one can take another player's ID without their private key, and a server
  cannot pass a signature on to another: it names the challenge and the address.
- No hardware data leaves the client. A player can make a new key and a new ID
  at will, so an ID proves continuity, not uniqueness: ban lists and playtime
  must weigh how long an ID has been seen.
- A server behind NAT must set `sv_publicAddress`; without it only LAN players
  get an ID.
- Each connect with an ID costs an ECDSA verification, capped at 50 a second.

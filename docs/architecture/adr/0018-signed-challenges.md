# 0018. Signed challenges, and a stateless mode for floods

- Status: Accepted
- Date: 2026-11-03

## Context

Every `getchallenge` took one of 1024 challenge slots, and on the internet it
also sent a request to the authorize server. A global limit (100 a second, and
20 for addresses that ask again) kept a flood of made-up addresses from turning
the table over faster than a join takes, but during such a flood it also
dropped the requests of real players, who then got no challenge at all.

The authorize step is why `getchallenge` keeps state: the authorize server's
reply names the challenge, not the player's address, so the server has to
remember where to send `challengeResponse`. A client that has its challenge
sends `connect` again every 3 seconds until it gets an answer
(`CL_CheckForResend`, in OpenCoD2-Plus's reconstruction).

## Decision

A challenge is an HMAC-SHA256 of the address, the port and a 30-second window
under a key drawn at startup (`SV_ChallengeCookie`, in `src/libcod/libcod.cpp`),
valid for the current and the previous window. A `connect` whose challenge is
not in the table but carries a valid signature gets a slot then; if the address
needs authorizing, the server asks the authorize server and answers the next
`connect` once the reply came, or once `sv_authorizeTimeout` passed, as
`getchallenge` does.

When no authorize step applies (LAN, `sv_noAuthorize`) `getchallenge` answers
with the signature alone and takes no slot, so it needs no global limit.
`sv_challengeStateless 1` does the same on the internet: authorizing moves to
the `connect`, so a flood cannot keep players out, and each join waits about
3 seconds more. It is off by default.

## Consequences

- Without the dvar a public server behaves as before, and a player whose slot a
  flood took still joins.
- With it, an admin under a flood trades 3 seconds per join for joins that
  keep working. Made-up addresses no longer reach the authorize server: only a
  `connect` with a valid signature, from an address that got it, does.
- A slot made from a signature has no measured ping, so `sv_minPing` and
  `sv_maxPing` do not apply to that player.
- Mbed TLS is built whenever libcod is, not only with `WITH_HTTP`; the rate
  limiter's seed already needed it, and `WITH_HTTP=false` builds link again.
- The per-address limit of `getchallenge` stays on every path.

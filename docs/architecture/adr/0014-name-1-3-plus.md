# 0014. The player-facing name is "1.3 Plus"

- Status: Accepted
- Date: 2026-11-02

## Context

Players should see that CoD2 Plus is a patch that comes after 1.3, as CoD2x
shows with its 1.4.x releases. A bare number cannot say it here:

- "1.4" means CoD2x to players, and CoD2x clients sort servers by version.
  [ADR 0011](0011-plus-protocol.md) already left the name out.
- Mods read "1.4" from zk_libcod's `getProtocolString()`, which returns it for
  protocol 119 (Game Pass).
- The client keeps `shortversion` at "1.3" and the server keeps announcing
  118 ([ADR 0012](0012-plus-leaves-1-3-out.md)), or the Plus client could no
  longer join 1.3 servers.

## Decision

Text that players read calls the project "1.3 Plus" (in full, "CoD2 1.3
Plus"): the server's notice to other clients, the client's menus and console,
release names and the READMEs. The technical values stay as they are:
`shortversion` "1.3", protocol 118 in announcements, and the Plus version
number of the handshake (`plus\122`, `connectResponse 122`), which keeps
counting each incompatible change. A release can add its own number after the
name ("1.3 Plus 1"), apart from the protocol's.

## Consequences

- The name says both things: it is built on 1.3, and it is not 1.3 or CoD2x.
- No network value changes, so nothing breaks for stock clients, CoD2x
  clients or mods.
- Text still to rename: `PLUS_NOTICE` in `src/server/sv_client_mp.cpp` and
  its `sv_plusNotice` description, and in OpenCoD2-Plus the console line
  "CoD2 Plus server, version". Code names (`plus_format.h`, `COD2_PLUS_*`,
  `sv_plus*`) stay.
- OpenCoD2-Plus records the same decision in its own ADR.

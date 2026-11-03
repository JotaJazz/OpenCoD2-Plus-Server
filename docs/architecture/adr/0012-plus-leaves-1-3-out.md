# 0012. Plus leaves 1.3 clients out and raises the tick rate

- Status: Accepted; its branch superseded by [0015](0015-plus-as-a-build-variant.md)
- Date: 2026-10-31

## Context

[ADR 0011](0011-plus-protocol.md) kept 1.3 clients on a Plus server, which held
the branch to fewer bytes. Once the snapshot writer stopped resending unchanged
fields, a new format alone saves 12–14% more, and that fix went to every client
through `master`. Plus needs something stock clients cannot have. A test at
40 and 60 Hz showed the server has the CPU for it.

## Decision

A Plus server refuses clients that do not speak CoD2 Plus, with a message that
tells them to update, and runs at 40–60 Hz. It keeps announcing 118, so it
stays in the lists and a stock client gets that message instead of nothing.
The handshake and the number of ADR 0011 stay. The Plus client keeps joining
stock 1.3 servers. `master` is the line for stock clients.

## Consequences

- Fairness stops being a limit: everyone on a Plus server has the same client.
- The server keeps one format to test.
- Nobody plays on a Plus server until the client can be distributed, which
  waits for that project's license.
- Script time has to stop assuming 20 frames a second, and mods with their own
  timing need testing.
- A rejected alternative: a mode inside a mixed server. It would keep two
  formats and two game speeds in one branch for clients that `master` serves.

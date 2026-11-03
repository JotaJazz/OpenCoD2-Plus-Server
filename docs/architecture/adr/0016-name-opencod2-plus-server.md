# 0016. The project is named OpenCoD2-Plus Server

- Status: Accepted
- Date: 2026-11-02

## Context

"CoD2rev-Plus" only meant something to people who knew voron00's
CoD2rev_Server; "rev" told an admin looking for a CoD2 server nothing. The
maintainer's client is OpenCoD2-Plus, and the protocol they share is CoD2 1.3
Plus ([ADR 0014](0014-name-1-3-plus.md)).

## Decision

The project is named **OpenCoD2-Plus Server** (in full, OpenCoD2-Plus
Dedicated Server), and the GitHub repository is `JotaJazz/OpenCoD2-Plus-Server`.
The READMEs say it was called CoD2rev-Plus until November 2026, and the fork
of voron00/CoD2rev_Server stays credited. The binaries (`cod2rev_lnxded`,
`cod2rev_win32.exe`), the launchers, the systemd unit and `/var/lib/cod2rev`
keep their names, so existing installs and scripts go on working.

## Consequences

- The server and the client read as one family; each README links the other.
- GitHub redirects the old repository URLs, clones and badges.
- Past stages of the project memory and old commits keep the old name.
- Renaming the binaries is left for a release, if ever.
- OpenCoD2-Plus names this repository in its own documents; it follows in
  that repository.

# CoD2rev-Plus

<p align="center"><img src="docs/banner.svg" alt="CoD2rev-Plus" width="100%"></p>

[![Build](https://github.com/JotaJazz/CoD2rev-Plus/actions/workflows/build.yml/badge.svg)](https://github.com/JotaJazz/CoD2rev-Plus/actions/workflows/build.yml)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue)](LICENSE)
![Platforms: Linux | Windows](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-lightgrey)
![CoD2 1.0 | 1.3 | 1.3 Plus](https://img.shields.io/badge/CoD2-1.0%20%7C%201.3%20%7C%201.3%20Plus-c9b37e)
[![Fork of voron00/CoD2rev_Server](https://img.shields.io/badge/fork%20of-voron00%2FCoD2rev__Server-555)](https://github.com/voron00/CoD2rev_Server)
[![Last commit](https://img.shields.io/github/last-commit/JotaJazz/CoD2rev-Plus/dev)](https://github.com/JotaJazz/CoD2rev-Plus/commits/dev)

[Español](README.es.md) · [English](README.md) · [Português](README.pt.md) · [Français](README.fr.md) · **Deutsch** · [Русский](README.ru.md)

**Dein eigener Call-of-Duty-2-Server, auch heute noch.** CoD2rev-Plus ist der dedizierte Mehrspielerserver von Call of Duty 2, aus seinem Quellcode neu aufgebaut, für die Versionen 1.0 und 1.3, unter Windows und Linux. Spieler verbinden sich mit dem Spiel, das sie bereits haben; er behebt viele Fehler des Originalservers und ergänzt, was Serveradministratoren und Moddern bisher gefehlt hat. Ein einziger Serverprozess kann Spieler von 1.0 und 1.3 im selben Match aufnehmen.

Er ist ein Fork von [voron00/CoD2rev_Server](https://github.com/voron00/CoD2rev_Server), wo das Reverse Engineering des Servers geleistet wurde. Er ist außerdem der Server von **CoD2 1.3 Plus**, einem neueren Protokoll für den Client [OpenCoD2-Plus](https://github.com/JotaJazz/OpenCoD2-Plus), der sich noch in Entwicklung befindet.

## Was es heute kann

- **Builds für Windows und Linux:** ein MinGW-Build für Windows, `make` für 64-Bit-Linux, ein 32-Bit-Linux-Build, ein experimenteller Build für 64-Bit-ARM wie einen Raspberry Pi, die Spielversion (1.0, 1.3 oder 1.3 Plus) beim Bauen wählbar, automatische Builds bei jedem Push, Startskripte, eine systemd-Unit und eine Beispiel-`server.cfg`.
- **Ein Server für 1.0 und 1.3:** Der 1.0-Build spielt mit Clients von 1.0, 1.3, Game Pass und CoD2x, und `net_altPort` führt dasselbe Match in den Serverlisten beider Versionen auf.
- **Sicherheit und Stabilität:** Netzwerkeingaben, die den Server abstürzen ließen oder seinen Speicher überschrieben, werden jetzt geprüft; Fluten von Anfragen, Verbindungen und Client-Befehlen werden gedrosselt; rcon sperrt IPs nach falschen Passwörtern; Downloads liefern die Originaldateien des Spiels nicht mehr aus; Sperren werden bei jeder Verbindung geprüft; und ein Absturz hinterlässt einen Bericht in `crash.log`.
- **Kompatibilität:** etwa 20 % weniger Datenverkehr zu den Clients, große Nachrichten von 1.3-Clients, Masterserver als `host:port`, `dedicated 1`, Spieldateien auf Windows-Laufwerken unter WSL, eine gleichmäßige Spieluhr auch bei langen Laufzeiten und Bots, die nach einem Kartenwechsel zurückkommen.
- **Administration:** Passwörter nicht im Log, Name, Rotation und Zeitstempel des Logs, erzwungene Rate und Snapshot-Rate, ein einstellbarer CD-Key-Autorisierungsserver, abschaltbare Kick- und Timeout-Meldungen, Schalter für die Kartenatmosphäre und ein sauberes Beenden bei SIGTERM.
- **Skripting (libcod):** die meisten Skriptfunktionen und Callbacks von [zk_libcod](https://github.com/ibuddieat/zk_libcod) mit denselben Namen: Skriptfehler mit Datei und Zeile, Tastendrücke, Rcon-Befehle, Spieler- und Waffensteuerung, Admin-Werkzeuge, Wegpunkt-Graphen mit A\*, was jeder Spieler sieht, hört und womit er kollidiert, Physik, JSON, SQLite, HTTP- und WebSocket-Clients, Sounds über den Sprachchat und mehr, wobei mehrere ihrer Fehler unterwegs behoben wurden.
- **Bots-Mod:** `mods/bots`, Bots, die sich über Wegpunkt-Graphen orientieren, Visier, Granaten und Messer benutzen und die Ziele von SD, CTF und HQ spielen.
- **CoD2 1.3 Plus (in Entwicklung):** `make PLUS=1` baut einen Server nur für den Plus-Client, mit einem Handshake, der anderen Clients sagt, dass sie aktualisieren sollen, und kleineren Snapshots, auf dem Weg zu 40–60 Hz. Alle anderen Builds behalten das ursprüngliche Netzwerkformat.
- **Tests:** ein Smoke-Test mit einem minimalen Client, der die Snapshots des Servers liest, ein Bot-Test auf echten Karten sowie ein HTTP- und WebSocket-Test.

Er betreibt außerdem die lokalen Spiele von [OpenCoD2-Plus](https://github.com/JotaJazz/OpenCoD2-Plus), einem neu aufgebauten CoD2-Client. Jede Änderung im Detail, mit ihren Funktionen, Variablen und Korrekturen, steht in [docs/CHANGES.md](docs/CHANGES.md) (auf Englisch).

> [!NOTE]
> **Wird noch verbessert.** Wenn etwas kaputtgeht oder sich anders verhält als beim Originalserver, melde es bitte in den [Issues](https://github.com/JotaJazz/CoD2rev-Plus/issues).

> [!IMPORTANT]
> **Es sind keine Spieldateien enthalten.** Dieses Repository enthält nur Quellcode. Der Server braucht den Ordner `main` mit den `.iwd`-Dateien aus einer Kopie von Call of Duty 2, die **dir gehört**.

## Server starten

Fertige Builds findest du auf der Seite [**Releases**](https://github.com/JotaJazz/CoD2rev-Plus/releases), beginnend mit dem Release Candidate `v1.0.0-rc1`; du kannst den Server auch selbst bauen (siehe [Kompilieren](#kompilieren)). Kopiere ihn in deinen Call-of-Duty-2-Ordner, neben `main`, mit einer `server.cfg` in `main` ([`scripts/server.cfg.example`](scripts/server.cfg.example) ist ein guter Ausgangspunkt).

**Windows:** `cod2rev_win32.exe` und [`scripts/windows/iniciar_cod2rev.bat`](scripts/windows/iniciar_cod2rev.bat) kopieren, dann ausführen:

```bat
iniciar_cod2rev.bat            :: LAN oder direkte IP
iniciar_cod2rev.bat internet   :: auch in der öffentlichen Serverliste
```

**Linux:** `cod2rev_lnxded` und [`scripts/linux/iniciar_cod2rev.sh`](scripts/linux/iniciar_cod2rev.sh) kopieren, dann ausführen:

```sh
./iniciar_cod2rev.sh            # LAN oder direkte IP
./iniciar_cod2rev.sh internet   # auch in der öffentlichen Serverliste
```

Beide starten auf Port `28960` mit der Karte `mp_toujane`. Läuft das Spiel auf demselben PC, starte zuerst den Server: Das Spiel benutzt ebenfalls `28960`. Weitere Optionen, die CD-Key-Prüfung und systemd stehen unter [Ausführen](#ausführen). Auf einem Raspberry Pi 3, 4 oder 5 mit einem 64-Bit-System baust du ihn dort mit `make ARCH=arm64`.

## Spielversionen

| Build | Wer beitreten kann | Serverliste |
| --- | --- | --- |
| `make` (1.0, Standard) | Clients von 1.0, 1.3, Game Pass und CoD2x (Protokolle 115 bis 119) | 1.0; mit `net_altPort` auch 1.3 und CoD2x |
| `make PROTOCOL=118` (1.3) | Clients von 1.3 und CoD2x (Protokoll 118) | 1.3 und CoD2x |
| `make PLUS=1` (1.3 Plus) | Nur der Client OpenCoD2-Plus; jedem anderen Client wird gesagt, dass er aktualisieren soll | 1.3, damit Spieler mit dem Originalspiel den Hinweis sehen statt gar nichts |

- **Ein Match für 1.0 und 1.3:** Starte den 1.0-Build mit `+set net_altPort 28961`, dann antwortet er auf einem zweiten Port als 1.3, mit eigenen Heartbeats, sodass dasselbe Match für beide Versionen aufgeführt wird. Echte 1.0- und 1.3-Clients haben auf diese Weise gemeinsam ein Match gespielt. Betreibe ihn mit den Spieldateien von 1.0, ohne `iw_15.iwd`, dessen Skripte und Menüs 1.0-Clients fehlen.
- **CoD2x:** [CoD2x](https://github.com/callofduty2x/CoD2x)-1.4-Clients verbinden sich mit Protokoll 118, und ihre Serverliste zeigt nur Server an, die Protokoll 118 oder 120 melden; sie sehen also den 1.3-Build und den `net_altPort` des 1.0-Builds. Ein CoD2x-Client hat auf beiden gespielt.
- **CoD2 1.3 Plus** ist für einen Client gedacht, der noch nicht verbreitet werden kann; ein öffentlicher Plus-Server muss also auf ihn warten. Sein Protokoll steht in [docs/architecture/plus-protocol.md](docs/architecture/plus-protocol.md) (auf Englisch).

## Für Mitwirkende

Jede Art von Hilfe zählt: einen Server betreiben und melden, was schiefgeht, auf anderen Systemen testen, Mods, die die neuen Skriptfunktionen nutzen, oder Code. Gearbeitet wird im Branch `dev`, der mit jedem Release in `master` übernommen wird. Die technische Dokumentation, auf Englisch, beginnt bei [docs/README.md](docs/README.md); [AGENTS.md](AGENTS.md) ist der Einstiegspunkt für KI-Programmieragenten.

## Kompilieren

Das Ergebnis landet in `bin/`, die Zwischenobjekte in `obj/`.

### Linux

Der Server ist standardmäßig eine 64-Bit-Binärdatei und braucht nur `gcc` und `g++`:

```bash
make                 # 1.0 -> bin/cod2rev_lnxded
make PROTOCOL=118    # 1.3, gleicher Name
make PLUS=1          # 1.3 Plus, gleicher Name
make ARCH=x86        # 32 Bit, gleicher Name
make ARCH=arm64      # 64-Bit-ARM (experimentell), auf dem ARM-Rechner gebaut
```

Der 32-Bit-Build benötigt auf einem 64-Bit-System die 32-Bit-Unterstützung von GCC (unter Debian und Ubuntu die Pakete `gcc-multilib` und `g++-multilib`). Der ARM-Build rundet seine Berechnungen nicht so wie der Originalserver und ist daher noch nicht für kompetitives Spielen gedacht.

### Windows (Cross-Kompilierung unter Linux mit MinGW)

Benötigt den 32-Bit-Compiler von MinGW-w64 mit POSIX-Threads (unter Debian und Ubuntu `gcc-mingw-w64-i686-posix` und `g++-mingw-w64-i686-posix`):

```bash
make windows                 # 1.0 -> bin/cod2rev_win32.exe
make windows PROTOCOL=118    # 1.3, gleicher Name
```

<details>
<summary><b>Spielversion, automatische Builds und Makefile-Optionen</b></summary>

Ohne `PROTOCOL` oder mit `PROTOCOL=115` wird der Server als 1.0 gebaut. `PLUS=1` ist ein 1.3-Build und lässt sich mit `ARCH` und `windows` kombinieren. Jede Plattform und Version behält ihre eigenen Objekte unter `obj/`, du kannst also ohne `make clean` zwischen ihnen wechseln; alle Versionen schreiben denselben Dateinamen, und `BIN_DIR=<ordner>` baut in einen anderen Ordner, um mehrere zu behalten.

Jeder Push auf `master` oder `dev`, der den Code ändert, baut 1.0 und 1.3 für Linux (32 und 64 Bit) und Windows sowie 1.3 Plus für 64-Bit-Linux in GitHub Actions ([`.github/workflows/build.yml`](.github/workflows/build.yml)). Die fertigen Binärdateien lassen sich als Artefakte im Tab [Actions](https://github.com/JotaJazz/CoD2rev-Plus/actions) des Repositorys herunterladen.

| Option | Standard | Beschreibung |
| --- | --- | --- |
| `PROTOCOL` | `115` | `115` baut 1.0, `118` baut 1.3. |
| `PLUS` | `0` | `1` baut CoD2 1.3 Plus, nur für den Plus-Client. |
| `ARCH` | `x64` | `x86` für 32-Bit-Linux, `arm64` für 64-Bit-ARM. Windows ist immer 32 Bit. |
| `WITH_LIBCOD` | `true` | Bindet die Skript-Erweiterungen von libcod ein (Bots, Spieler, Entitäten, Waffen, Hilfsfunktionen usw.). |
| `WITH_SQLITE` | `true` | Skriptfunktionen für SQLite. |
| `WITH_MYSQL` | `false` | Skriptfunktionen für MySQL. Benötigt die Client-Bibliothek von MySQL oder MariaDB. |
| `WITH_SPEEX` | `true` | `loadSoundFile`, `playSoundFile` und die übrigen Soundfunktionen, mit Speex (`src/libcod/speex`). |
| `WITH_HTTP` | `true` | `httpFetch` und `webSocket*`, mit Mbed TLS (`src/libcod/mbedtls`) für `https://` und `wss://`. |

`make clean` löscht die Binärdatei und die Objekte.

</details>

## Ausführen

<details>
<summary><b>Startskripte, CD-Key-Autorisierung und systemd</b></summary>

Die Startskripte starten standardmäßig im LAN-Modus (`dedicated 1`: LAN oder direkte IP); mit `internet` kündigen sie den Server in der öffentlichen Liste an (`dedicated 2`). Sie setzen ihre Werte vor `+exec server.cfg`, sodass `server.cfg` sie ändern kann. Läuft das Spiel bereits auf demselben PC, weicht ein danach gestarteter Server auf den nächsten freien Port aus; mit `net_strictPort 1` bricht er stattdessen ab.

**Schlüsselautorisierung:** Der Server fragt bei `cod2master.activision.com` an, um den Schlüssel jedes Clients zu prüfen, der sich nicht im lokalen Netz befindet. Mit `sv_cracked 1` schickt er die Anfrage weiterhin, akzeptiert den Client aber unabhängig von der Antwort. Die Startskripte schalten das nur im LAN-Modus ein; im Internet-Modus wird ein gültiger Schlüssel verlangt, außer `server.cfg` schaltet es ein.

**systemd:** `scripts/linux/cod2rev@.service` betreibt Server mit systemd, einen pro Instanz: `systemctl enable --now cod2rev@public` führt `public.cfg` mit einem eigenen Ordner in `/var/lib/cod2rev/public` aus, startet den Server nach einem Absturz neu und beendet ihn mit SIGTERM sauber (letzte Meldung, Flatline-Heartbeat, Logs geschlossen). Die Kommentare in der Datei erklären die Installation.

`run_bin.sh` ist das Testskript des Originalprojekts: Es startet `bin/cod2rev_lnxded` im Entwicklermodus mit aktivierten Cheats und Test-Bots. Es dient als Beispiel für Parameter, nicht als Konfiguration für einen echten Server.

</details>

## Tests

<details>
<summary><b>Die Testskripte</b></summary>

`scripts/smoke_test.py` braucht einen gebauten Server und einen Spielordner:

```bash
python3 scripts/smoke_test.py /pfad/zu/CoD2
make PROTOCOL=118 && python3 scripts/smoke_test.py /pfad/zu/CoD2 --protocol 118
make PLUS=1 && python3 scripts/smoke_test.py /pfad/zu/CoD2 --plus
```

Es startet den Server im LAN-Modus mit einem temporären Benutzerordner, der Spielordner wird also nur gelesen. Es prüft, dass der Server eine Karte lädt und auf `getinfo`, `getstatus` und rcon antwortet, und dass `scripts/cod2client.py`, ein minimaler Client, sich verbinden, den Gamestate empfangen, ins Spiel kommen, Snapshots lesen und Befehle senden kann, auch in einer in Fragmente aufgeteilten Nachricht; außerdem probiert es die Angriffe aus, die der Server abweisen muss. Verwende einen Spielordner mit den originalen `.iwd`-Dateien: Mods in `main`, die die Skripte der Spielmodi ersetzen, können das Laden der Karte verhindern.

`scripts/bots_test.py` installiert den Bots-Mod in einem temporären Ordner, spielt eine Karte mit sechs Bots und prüft, dass der Wegpunkt-Graph erzeugt, gespeichert und wieder gelesen wird, dass die Bots Wegen folgen und Visier, Granaten und Messer benutzen und dass keine Skriptfehler auftreten:

```bash
python3 scripts/bots_test.py /pfad/zu/CoD2 --map mp_carentan
```

Mit `--gametype sd`, `--gametype ctf` oder `--gametype hq` prüft er stattdessen, dass die Bots das Spielziel verfolgen. `--bombmode 1` spielt SD im Modus mit nur einer Bombenzone. `--corrupt-cache` startet mit einer beschädigten Wegpunktdatei, die die Bots durch einen neuen Graphen ersetzen müssen.

`scripts/http_test.py` prüft `httpFetch` und `webSocket*` gegen lokale HTTP-, HTTPS-, WS- und WSS-Server, und `scripts/check_docs.py` prüft die Links und Pfade der Dokumentation.

Um Speicherfehler zu finden, baue den Server mit AddressSanitizer in einem eigenen Ordner und übergib dieses Binary mit `--binary`:

```bash
make OBJ_ROOT=/tmp/asan/obj BIN_DIR=/tmp/asan/bin \
  CFLAGS="-fno-pie -O1 -g -fno-omit-frame-pointer -mfpmath=387 -DNDEBUG -DPROTOCOL_VERSION=115 -MMD -MP -m64 -D_FILE_OFFSET_BITS=64 -fsanitize=address" \
  LFLAGS="-no-pie -m64 -fsanitize=address"
```

Ein auf der Kommandozeile angegebenes `CFLAGS` ersetzt das des Makefiles, daher müssen `-m64` und `-D_FILE_OFFSET_BITS=64` wiederholt werden. Lässt man diesen Build eine Weile mit dem Bots-Mod und einer kurzen `sv_mapRotation` laufen, sind auch Kartenwechsel und das Spiel abgedeckt.

</details>

## Aufbau des Repositorys

<details>
<summary><b>Was wo liegt</b></summary>

| Pfad | Inhalt |
| --- | --- |
| `src/server` | Serverlogik: Clients, Netzwerk, rcon, Master-Server. |
| `src/game`, `src/bgame` | Spiellogik. |
| `src/script` | Virtuelle Maschine für GSC-Skripte. |
| `src/qcommon`, `src/universal` | Gemeinsamer Code: Befehle, Variablen (dvars), Dateisystem, Netzwerk, das Plus-Format. |
| `src/xanim` | Modelle und Animationen. |
| `src/stringed` | Lokalisierte Texte. |
| `src/libcod` | Skript-Erweiterungen von libcod, mit den Bibliotheken, die sie nutzen: SQLite, yyjson, Speex, Mbed TLS und die MySQL-Header. |
| `src/win32`, `src/unix` | Plattformspezifischer Code. |
| `src/zlib` | Kopie von zlib. |
| `docs` | Technische Dokumentation für Mitwirkende und KI-Agenten (Index in [docs/README.md](docs/README.md)), die Änderungsliste und das Protokoll von CoD2 1.3 Plus. |
| `scripts` | Startskripte für Windows und Linux, die systemd-Unit, die Beispiel-`server.cfg` und ihr Generator, das Installationsskript der Bots, der Smoke-Test mit seinem minimalen Client, der Bots-Test, der HTTP- und WebSocket-Test sowie die Prüfung der Dokumentation. |
| `mods/bots` | Der Skript-Mod der Bots. |

</details>

## Transparenz

- **Wer das hier pflegt:** Ich bin JotaJazz. Ich mag alte Spiele, und deshalb gibt es diesen Fork: Ich möchte auch weiterhin einen CoD2-Server auf meinen eigenen Rechnern betreiben können.
- **Wie hier gearbeitet wird:** Ich arbeite mit [Claude Code](https://claude.com/claude-code), dem Programmierassistenten von Anthropic. Die Änderungen in diesem Fork, einschließlich dieses README und seiner Übersetzungen, sind mit seiner Hilfe geschrieben. So entstandene Commits tragen die Zeile `Co-Authored-By: Claude` in der Commit-Nachricht und lassen sich daher mit `git log` im Verlauf erkennen.
- **Verhältnis zum Original:** Dieser Fork übernimmt Änderungen aus dem Original-Repository, wenn es welche gibt, schickt seine eigenen aber nicht zurück. Er wird sich mit der Zeit wahrscheinlich davon entfernen.
- **Was es nicht ist:** Es ist kein offizielles Projekt und steht in keiner Verbindung zu Activision, Infinity Ward oder dem Autor des Original-Repositorys. Es enthält keine Spieldateien.

## Hinweis

Dies ist eine unabhängige Rekonstruktion des dedizierten Servers von Call of Duty 2 auf Quellcodeebene. Sie steht in keiner Verbindung zu Activision Publishing, Inc., Infinity Ward oder einem ihrer verbundenen Unternehmen und wird von diesen weder autorisiert noch gesponsert oder unterstützt.

„Call of Duty“ und „Call of Duty 2“ sind Marken von Activision Publishing, Inc. Sie werden in diesem Repository nur zur Identifikation und für die Interoperabilität verwendet, um zu beschreiben, was der Code rekonstruiert. Es werden keine Ansprüche auf diese Marken erhoben.

Dieses Projekt stellt keine urheberrechtlich geschützten Spieldaten bereit und hilft nicht, sie zu beschaffen. Um es mit echten Spielinhalten zu verwenden, musst du die Datendateien aus einer Kopie von Call of Duty 2 bereitstellen, die du rechtmäßig besitzt.

Wenn du Rechteinhaber bist und meinst, dass etwas hier nicht verbreitet werden sollte, öffne bitte ein Issue oder kontaktiere den Maintainer; das Anliegen wird umgehend bearbeitet.

## Lizenz

[GNU Affero General Public License v3.0](LICENSE), dieselbe wie beim Originalprojekt. Die mitgelieferten Bibliotheken behalten ihre eigenen Lizenzen: SQLite (Public Domain), Mbed TLS (Apache-2.0, `src/libcod/mbedtls/LICENSE`), yyjson (MIT), Speex (BSD, `src/libcod/speex/COPYING`) und zlib (zlib-Lizenz).

## Danksagungen

- [voron00](https://github.com/voron00/CoD2rev_Server), Autor des Originalprojekts
- id Software
- Activision / Infinity Ward
- [CoD4x Server](https://github.com/callofduty4x/CoD4x_Server)
- [OpenBO2](https://github.com/builtbyxeno/OpenBO2)
- [zk_libcod](https://github.com/ibuddieat/zk_libcod) (ibuddieat), wo mehrere der Korrekturen dieses Forks gefunden wurden

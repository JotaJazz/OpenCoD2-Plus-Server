# libcod

The fork's script extensions, in `src/libcod`, built when `WITH_LIBCOD=true`
(the default). Origin: libcod for the stock binaries, extended with a port of
[zk_libcod](https://github.com/ibuddieat/zk_libcod) (MIT). zk_libcod hooks the
stock 1.3 binary through `LD_PRELOAD`; here the same behaviour is written
directly into our functions. The user-facing list is in
[../CHANGES.md](../CHANGES.md).

## Files

| File | Contents |
|---|---|
| `src/libcod/gsc.cpp` | Builtin tables (`scriptFunctions`, `scriptMethods`), `Scr_GetCustomFunction`/`Scr_GetCustomMethod` |
| `src/libcod/libcod.cpp` | Callbacks (`InitLibcodCallbacks`), per-client/per-entity state, level init, bot movement (`SV_BotUserMove_libcod`), engine helpers |
| `src/libcod/libcod_client.h` | `libcodClient_t`, `libcodEntity_t` |
| `src/libcod/gsc_player.cpp`, `gsc_entity.cpp`, `gsc_weapons.cpp`, `gsc_level.cpp`, `gsc_utils.cpp` | Player, entity, weapon, level and utility builtins |
| `src/libcod/gsc_bots.cpp` | Bot control builtins |
| `src/libcod/gsc_graph.cpp` | Waypoint graphs and A\* (`graph*`) |
| `src/libcod/libcod_physics.cpp` | Script model gravity/bounce, bullet drop |
| `src/libcod/libcod_callbacks.cpp` | zk_libcod callbacks for events, notifies, movers, map weapons/turrets, debug prints and request spam |
| `src/libcod/libcod_sound.cpp` | WAV loading and Speex sounds sent as voice packets |
| `src/libcod/gsc_json.cpp` | JSON (yyjson) |
| `src/libcod/net_http.cpp`, `gsc_http.cpp` | HTTP/HTTPS client and WebSocket (Mbed TLS) |
| `src/libcod/gsc_sqlite.cpp`, `gsc_exec.cpp`, `gsc_mysql.cpp` | SQLite, `exec`/`exec_async`, MySQL (off by default) |
| `src/libcod/gsc_memory.cpp` | Raw memory builtins |

## How it attaches to the engine

- Builtins: `Scr_GetFunction`/`Scr_GetMethod` in `src/game/g_scr_main_mp.cpp`
  ask libcod first (`Scr_GetCustomFunction`, `Scr_GetCustomMethod`).
- Callbacks: `InitLibcodCallbacks` looks up the `CodeCallback_*` functions
  in `maps/mp/gametypes/_callbacksetup` only (`CodeCallback_PlayerCommand`,
  `CodeCallback_RemoteCommand`, `CodeCallback_Error`, button callbacks…);
  a mod that wants them overrides that file.
- State reset: `SV_FreeClient` calls `Libcod_ResetClient`; `G_FreeEntity`
  calls `Libcod_FreeEntity`; `G_InitGame` calls `Libcod_InitLevel` on every
  level start, including `map_restart`, and bumps `libcodLevelGeneration`.
- Per-player visibility: `SV_BuildClientSnapshot` builds an entity state per
  recipient (hide, fx, objectives, collision team).

## State rules

- Per-client state lives in `libcodClients[MAX_CLIENTS]`, per-entity state in
  `libcodEntities[MAX_GENTITIES]` (types in `src/libcod/libcod_client.h`,
  arrays in `src/libcod/libcod.cpp`). Add new fields there, never as statics
  in a `gsc_*.cpp`, so the resets above clear them.
- `libcodClient_t.generation` counts players in a slot: anything that
  outlives a player checks it (today, bullets in flight in
  `src/libcod/libcod_physics.cpp`).
- Async work (SQLite, exec, HTTP, WebSocket) keeps references to the script
  values it will pass to its callback, and checks `libcodLevelGeneration`
  before running it. Never use `scrVarPub.levelId` for this: a freed level
  id is often reused.
- Player events reach other clients through two copies
  (`BG_PlayerStateToEntityState` and a second loop in
  `src/game/g_active_mp.cpp`); a filter must cover both.

## VM facts

- Type names: zk_libcod names them after the 1.3 binary. Its `VAR_OBJECT` is our
  `VAR_POINTER`, its `VAR_STRUCT` is our `VAR_OBJECT`; our enum also has
  `VAR_INT64` (upstream's), which holds libcod's handles (MySQL, SQLite,
  files, memory). An `int` meeting an `int64` in an operator becomes `int64`
  (`Scr_CastWeakerPair`, `Scr_CastWeakerStringPair`), so `handle == 0` works.
- Callback arguments: the last value pushed is the first parameter.
- A runtime error ends the script thread. Outside developer mode, execution
  continues with `undefined`, which can cascade.
- `CodeCallback_Error(critical, function, message, position)` gets the
  position only with `developer` set (`developer 2` does not abort);
  `developer_script` is not enough. `critical` is always 0: errors that stop
  the map never reach the callback.
- Map commands (`map`, `map_restart`…) run from a script with
  `cmd_executestring` or `processRemoteCommand` are deferred until the script
  returns: changing the map frees the VM the script is running in.

## Unsafe builtins

Builtins that reach the shell, raw memory, files by raw path or any network
address are wrapped with `gsc_unsafe<>` in `src/libcod/gsc.cpp` and fail
unless the server starts with `+set sv_libcodUnsafe 1`; file functions that
are safe for any mod resolve paths under `fs_homepath` instead. See
[ADR 0008](adr/0008-unsafe-builtins-behind-a-dvar.md).

With the variable on, these builtins take their strings as they are: a mod
that builds a command, a path or an address from player text (a name, a chat
line, a menu response) gives that player the shell or the files of the server
user. Never pass player text to them; check it against a fixed list instead.

## Not ported on purpose

See [ADR 0003](adr/0003-zk-libcod-names.md).

Also left out after the ADR, for the same reasons:

| Left out | Why |
|---|---|
| `setWeaponFuseTime`, `setWeaponRaiseTime` | `PM_Weapon` predicts both on the client |
| `net_noFragmentationDelay` | The libcod send loop already sends all pending fragments at once |
| `sv_disconnectMessages` | The disconnect message is already not shown |
| `sv_botReconnectMode` | Bots come back after a map change; `sv_kickbots` drops them |

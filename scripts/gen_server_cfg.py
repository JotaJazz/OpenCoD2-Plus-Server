#!/usr/bin/env python3
"""Regenerates scripts/server.cfg.example from the dvars registered in src/.

Run it from anywhere after adding, removing or changing a dvar:

    python3 scripts/gen_server_cfg.py

The "Common settings" block and the descriptions are kept in this file; names,
types, defaults, ranges and flags are read from the Dvar_Register* calls.
"""
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, 'scripts', 'server.cfg.example')


def read_dvars():
    pat = re.compile(r'Dvar_Register(Bool|Int|Float|String|Enum|Vec2|Vec3|Vec4|Color)\s*\(')
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, 'src/**/*.cpp'), recursive=True)):
        rel = os.path.relpath(path, ROOT).replace(os.sep, '/')
        # dvar.cpp and dvar_cmds.cpp define the register functions themselves
        if rel in ('src/universal/dvar.cpp', 'src/universal/dvar_cmds.cpp'):
            continue
        text = open(path, encoding='latin-1').read()
        for m in pat.finditer(text):
            i = m.end(); depth = 1; args = []; cur = ''; instr = False
            while depth and i < len(text):
                c = text[i]
                if instr:
                    cur += c
                    if c == '\\': cur += text[i+1]; i += 1
                    elif c == '"': instr = False
                elif c == '"': instr = True; cur += c
                elif c == '(': depth += 1; cur += c
                elif c == ')':
                    depth -= 1
                    if depth: cur += c
                elif c == ',' and depth == 1: args.append(cur.strip()); cur = ''
                else: cur += c
                i += 1
            args.append(cur.strip())
            args = [re.sub(r'\s+', ' ', a) for a in args]
            line = text.count('\n', 0, m.start()) + 1
            out.append(dict(type=m.group(1), file=rel, line=line, args=args))
    return out


d = read_dvars()
MAC = {'PROTOCOL_VERSION':'115','MAX_CLIENTS':'64','DEFAULT_GRAVITY':'800','PORT_SERVER':'28960','ENTITYNUM_NONE':'1023',
       'MAX_LANGUAGES - 1':'13','UINT16_MAX':'65535','0x7FFFFFFF':'2147483647',
       'MASTER_SERVER_NAME':'"cod2master.activision.com"','AUTHORIZE_SERVER_NAME':'"cod2master.activision.com"','PORT_AUTHORIZE':'20700','COMMUNITY_MASTER_SERVER_NAME':'"master.cod2x.me"',
       'GAMEVERSION':'"Call of Duty 2"',
       'JSON_DEF_MAX_LOAD_BYTES':'8388608','JSON_HARD_MAX_LOAD_BYTES':'33554432','JSON_DEF_SLOW_WARN_MS':'25','JSON_DEF_ASYNC_MAX_JOBS':'64'}
UNB = {'INT_MAX','INT_MIN','FLT_MAX','-FLT_MAX'}

COMMON = '''// --- Identity ---
set sv_hostname "My CoD2 server"
set sv_maxclients 20            // 1-64, takes effect on the next map load
set sv_privateClients 0         // slots reserved for sv_privatePassword
set sv_privatePassword ""
set g_password ""               // password to join; empty = public

// --- Remote console ---
// Leave rcon_password empty to keep rcon unusable.
set rcon_password ""
set sv_allowRcon 1              // 0 = ignore every rcon packet
set sv_rconMaxAttempts 5        // wrong passwords per IP before the lockout, 0 = no lockout
set sv_rconLockTime 600         // lockout length in seconds
set sv_rconWhitelist ""          // admin IPs never locked out or rate limited, e.g. "203.0.113.5 198.51.100.7"

// --- Master servers (only used with dedicated 2) ---
// sv_master1 defaults to cod2master.activision.com and sv_master2 to master.cod2x.me.
// sv_master2 is set here because the server saves it in config_mp_server.cfg, and a
// file saved by an older build can hold an empty value that overrides the default.
// sv_master3 to sv_master5 are free; host:port is accepted.
set sv_master2 "master.cod2x.me"
set sv_master3 ""
set sv_master4 ""
set sv_master5 ""

// --- Network ---
set sv_fps 20
set sv_maxRate 25000
set sv_minPing 0
set sv_maxPing 0                // 0 = no limit
set sv_timeout 240
set sv_floodProtect 1
set g_antilag 1

// --- Files and downloads ---
set sv_pure 1                   // clients must use the same .iwd files as the server
set sv_allowDownload 1
set sv_wwwDownload 0            // 1 = send clients to sv_wwwBaseURL for downloads
set sv_wwwBaseURL ""

// --- Game ---
set g_gametype "tdm"            // dm, tdm, sd, ctf, hq
set g_allowVote 0
set sv_kickBanTime 300          // seconds a kicked player stays banned
set sv_disableClientConsole 0

// --- Logging ---
set g_log "games_mp.log"
set g_logSync 0

// --- Map rotation ---
// The launcher starts the first map itself; the rotation is used from then on.
set sv_mapRotation "gametype tdm map mp_toujane gametype tdm map mp_carentan gametype tdm map mp_dawnville"
'''
common_names = set(re.findall(r'^set (\S+)', COMMON, re.M))

DESC = {
 'sv_zombietime':'seconds a disconnected client slot is kept before it is freed',
 'sv_reconnectlimit':'minimum seconds between reconnects from the same address',
 'sv_allowAnonymous':'allow clients flagged as anonymous',
 'sv_voice':'enable in-game voice chat',
 'sv_voiceQuality':'voice chat codec quality',
 'sv_showCommands':'print every client command to the console',
 'sv_padPackets':'add padding bytes to outgoing packets (debugging)',
 'sv_mapRotationCurrent':'remaining part of the rotation, managed by the server',
 'sv_keywords':'free text shown to server browsers',
 'sv_wwwDlDisconnected':'disconnect clients while they download over HTTP',
 'sv_downloadMessage':'if set, downloads are refused and this text is shown instead',
 'sv_fastDownload':'send in-game downloads faster',
 'g_safePrecache':'warn and show a default model or effect instead of stopping the map on precache overflows',
 'g_reservedModels':'model slots kept for script precaches, out of reach of map entities',
 'logErrors':'write script runtime errors to the log without developer mode',
 'g_noMoverBlockage':'let movers go on when an entity blocks them',
 'g_spawnMapWeapons':'spawn the map\'s weapons; 0 hands them to CodeCallback_MapWeaponsLoad',
 'g_spawnMapTurrets':'spawn the map\'s turrets; 0 hands them to CodeCallback_MapTurretsLoad',
 'g_corpseHit':'bullets hit corpses with blood; 0 = as the surface under them',
 'g_spectateBots':'let spectators follow bots',
 'g_logPickup':'write weapon and item pickups to the game log',
 'sv_botKickMessages':'tell everyone when a bot is kicked',
 'sv_noAuthorize':'skip the CD key authorization server (players get GUID 0)',
 'sv_authorizeTimeout':'milliseconds a connecting player waits for the authorization server',
 'sv_limitLocalRcon':'apply the rcon rate limit to LAN addresses too',
 'sv_isLookingAtOnDemand':'trace what players look at only for isLookingAt (no crosshair names or trigger_lookat)',
 'sv_fastDownloadSpeed':'messages a frame sv_fastDownload sends a downloading client',
 'g_ambientSound':'play the map\'s distant battle sounds (ambientPlay)',
 'g_fireFx':'send the map\'s looped fx/fire/ effects and fire sounds',
 'g_smokeFx':'send the map\'s looped fx/smoke/ effects',
 'g_weatherFx':'send the map\'s looped dust, snow and fog bank effects',
 'g_fog':'let map scripts set fog (setExpFog, setCullFog)',
 'sv_minimizeSysteminfo':'move some dvars from the systeminfo to the gamestate, to make room for more iwds',
 'fs_callbacks':'script with the CodeCallback_* functions; empty = maps/mp/gametypes/_callbacksetup',
 'fs_gametypes':'folder of the gametype scripts; empty = maps/mp/gametypes',
 'fs_mapScriptDirectories':'where a map\'s main is: 0 maps/mp/<map>, 1 maps/mp/<map>/<map>, 2 that first',
 'fs_replaceStockMaps':'let manymaps replace a stock map with a library iwd of the same name',
 'loc_loadLocalizedMods':'list the mod\'s localized iwds for pure clients too',
 'sv_kickbots':'drop bots when the map restarts or changes',
 'jump_bounceEnable':'keep speed when landing on slopes (bouncing)',
 'sv_cracked':'accept clients whatever the key authorization server answers',
 'sv_master1':'first master server',
 'sv_master2':'second master server',
 'fs_library':'folder used by the libcod manymaps map download',
 'g_playerCollision':'players collide with each other',
 'g_playerEject':'push apart players stuck inside each other',
 'g_fixedWeaponSpreads':'use a fixed spread pattern instead of random spread',
 'g_dropGrenadeOnDeath':'a player killed while holding a primed grenade drops it',
 'g_speed':'player movement speed',
 'g_gravity':'world gravity',
 'g_knockback':'knockback applied by damage',
 'g_inactivity':'seconds before an inactive player is kicked, 0 = never',
 'g_motd':'message of the day',
 'g_banIPs':'list of banned addresses',
 'g_deadChat':'dead players can chat with living ones',
 'voice_deadChat':'dead players can voice chat with living ones',
 'voice_global':'voice chat is heard by both teams',
 'voice_localEcho':'players hear their own voice',
 'g_smoothClients':'smooth other players between snapshots',
 'g_synchronousClients':'force clients to wait for the server each frame (for demo recording)',
 'g_maxDroppedWeapons':'maximum dropped weapons kept on the map',
 'g_TeamName_Allies':'name shown for the allied team',
 'g_TeamName_Axis':'name shown for the axis team',
 'g_TeamColor_Allies':'colour of the allied team (red green blue alpha)',
 'g_TeamColor_Axis':'colour of the axis team (red green blue alpha)',
 'player_meleeRange':'reach of the melee attack',
 'jump_height':'jump height',
 'jump_slowdownEnable':'slow players down after a jump',
 'mantle_enable':'allow climbing over obstacles',
 'friction':'ground friction',
 'stopspeed':'speed below which a player stops',
 'bg_fallDamageMinHeight':'fall height at which damage starts',
 'bg_fallDamageMaxHeight':'fall height that kills',
 'player_breath_hold_time':'seconds a sniper can hold breath',
 'player_strafeSpeedScale':'speed multiplier when strafing',
 'player_backSpeedScale':'speed multiplier when moving backwards',
 'player_spectateSpeedScale':'speed multiplier for spectators',
 'dedicated':'1 = LAN or direct IP only, 2 = internet (announced to the master servers)',
 'sv_cheats':'allow cheat-protected variables and commands',
 'net_ip':'local address to bind to',
 'net_port':'UDP port',
 'net_noudp':'disable UDP networking',
 'sv_plusNotice':'make PLUS=1 build only: text shown to a client that is not CoD2 1.3 Plus; empty = the default, with the link to the client',
 'net_altPort':'second UDP port of the 1.0 build, announced as 1.3 so the server is listed for both versions; 0 = closed (set it on the command line)',
 'net_strictPort':'1 = a busy net_port stops the server instead of moving it to one of the next 9 ports (set it on the command line)',
 'net_lanauthorize':'also check the keys of clients on the local network',
 'showpackets':'print every packet',
 'showdrop':'print dropped packets',
 'fs_game':'mod folder',
 'fs_basepath':'folder where the game is installed',
 'fs_homepath':'folder where logs and downloaded files are written',
 'fs_cdpath':'extra read-only game folder',
 'fs_debug':'print file system activity',
 'fs_restrict':'restrict the server to demo content',
 'fs_ignoreLocalized':'ignore localized .iwd files',
 'developer':'developer mode: extra console output',
 'developer_script':'enable script debugging features',
 'logfile':'write the console to logfileName: 0 = off, 1 = buffered, 2 = flushed on every line',
 'logfileName':'console log file in fs_homepath/<mod>; empty = console_mp_server.log',
 'logfileRotate':'older console logs kept as <name>.1 to <name>.N when the server starts',
 'logTimestamps':'start each console log line with the date and time',
 'g_logRotate':'older game logs kept as <g_log>.1 to <g_log>.N when g_logRotateSize rotates it',
 'g_logRotateSize':'MB the game log reaches before it is rotated at the next map start; 0 = never',
 'sv_logRcon':'log the address and command of every accepted rcon command',
 'sv_authorizeServer':'server that checks CD keys and gives players their GUID',
 'sv_authorizePort':'port of sv_authorizeServer',
 'g_forceRate':'rate given to every client, overriding theirs; 0 = their own',
 'g_forceSnaps':'snapshots per second given to every client; 0 = their own',
 'sv_kickMessages':'tell everyone when a player is kicked',
 'sv_timeoutMessages':'tell everyone when a player times out',
 'sv_botUseTriggerUse':'send bots a "bot_trigger" notify for the use triggers they stand in',
 'scr_json_max_load_bytes':'largest JSON file json_load and json_load_async read, in bytes',
 'scr_json_slow_warn_ms':'a JSON call slower than this many milliseconds prints a warning',
 'scr_json_async_max_jobs':'JSON jobs that can run in the background at once',
 'g_bulletDrop':'let enableBulletDrop give a player\'s bullets travel time and drop',
 'g_bulletDropMaxTime':'milliseconds a dropping bullet flies before it is dropped',
 'sv_httpAllowedHosts':'hosts httpFetch and webSocketConnect may reach (spaces or commas, *.example.com for subdomains); empty = all',
 'sv_libcodUnsafe':'let scripts use the libcod functions that reach the shell, raw memory, any file or any address',
 'sv_httpAllowPrivate':'let httpFetch and webSocketConnect reach loopback and private addresses',
 'sv_httpCaFile':'PEM file with the certificates https and wss trust; empty = the system\'s',
 'g_debugGraph':'print debug messages from the graph (A*) script functions',
 'sv_graphAstarMaxIterations':'maximum nodes expanded by one graphFindPath; 0 = no limit',
 'sv_graphAstarWeight':'A* heuristic weight; above 1 finds paths faster but less short',
 'sv_graphMaxGraphs':'maximum number of graphs scripts can create',
 'sv_graphMaxNodes':'maximum nodes in one graph',
 'com_maxfps':'frame rate cap',
 'com_hunkMegs':'megabytes of memory reserved for game data',
 'timescale':'game speed multiplier',
 'loc_language':'language index: 0 English, 1 French, 2 German, 3 Italian, 4 Spanish, 5 British, 6 Russian, 7 Polish',
 'loc_forceEnglish':'always use English strings',
 'ttycon':'enable the terminal console',
 'viewlog':'show the console window',
 'protocol':'network protocol of this build: 115 = 1.0, 118 = 1.3',
 'shortversion':'game version of this build',
 'version':'full version string of this build',
 'mapname':'map currently loaded',
 'sv_mapname':'map currently loaded',
 'nextmap':'command run when the map ends',
 'sv_running':'1 while a map is loaded',
 'sv_serverid':'changes on every map load',
 'sv_iwds':'checksums of the loaded .iwd files',
 'sv_iwdNames':'names of the loaded .iwd files',
 'sv_referencedIwds':'checksums of the .iwd files the map uses',
 'sv_referencedIwdNames':'names of the .iwd files the map uses',
 'gamename':'game name reported to browsers',
}

GROUPS = [
 ('Server', lambda f: f.startswith('src/server/sv_init')),
 ('libcod extensions', lambda f: 'libcod' in f),
 ('Game rules', lambda f: f.startswith('src/game/')),
 ('Player movement and physics', lambda f: f.startswith('src/bgame/')),
 ('Network', lambda f: 'net_chan' in f or f.endswith('_net.cpp')),
 ('File system', lambda f: 'com_files' in f or 'sv_client' in f),
 ('Engine', lambda f: f.startswith('src/qcommon/') or 'com_memory' in f or 'stringed' in f),
 ('Platform', lambda f: f.startswith('src/unix/') or f.startswith('src/win32/')),
]

seen = {}
for x in d:
    n = x['args'][0]
    if not n.startswith('"'): continue
    n = n.strip('"')
    seen.setdefault(n, []).append(x)
# the engine registers some dvars before the game does; its registration is the one that counts
for xs in seen.values():
    xs.sort(key=lambda x: x['file'] != 'src/qcommon/common.cpp')

def val(v):
    v = MAC.get(v, v)
    if v in ('true','qtrue'): return '1'
    if v in ('false','qfalse'): return '0'
    if re.fullmatch(r'-?[0-9.]+f?', v): return v.rstrip('f') if '.' in v else v
    if v.startswith('"'): return v
    return None

def rng(lo, hi, kind):
    lo = MAC.get(lo, lo); hi = MAC.get(hi, hi)
    lo = lo.rstrip('f') if '.' in lo else lo
    hi = hi.rstrip('f') if '.' in hi else hi
    if lo in UNB and hi in UNB: return kind
    if lo == hi: return kind
    if hi in UNB: return f'{kind}, {lo} or more'
    if lo in UNB: return f'{kind}, {hi} or less'
    return f'{kind}, {lo} to {hi}'

def entry(n):
    xs = seen[n]; x = xs[0]; a = x['args']; t = x['type']; flags = a[-1]
    plats = {('Windows' if e['file'].startswith('src/win32/') else 'Linux' if e['file'].startswith('src/unix/') else 'all') for e in xs}
    if t == 'Bool': v, info = val(a[1]), 'bool'
    elif t == 'Int': v, info = val(a[1]), rng(a[2], a[3], 'int')
    elif t == 'Float': v, info = val(a[1]), rng(a[2], a[3], 'float')
    elif t == 'String': v, info = val(a[1]), 'string'
    elif t == 'Color': v, info = '"' + ' '.join(val(c) for c in a[1:5]) + '"', 'colour'
    else: raise SystemExit('unhandled type ' + t)
    tags = []
    if 'DVAR_ROM' in flags: tags.append('read-only')
    if 'DVAR_INIT' in flags: tags.append('command line only')
    if 'DVAR_CHEAT' in flags: tags.append('needs sv_cheats 1')
    if 'DVAR_LATCH' in flags: tags.append('applies on the next map or restart')
    if plats == {'Windows'}: tags.append('Windows only')
    if plats == {'Linux'}: tags.append('Linux only')
    note = info + (', ' + ', '.join(tags) if tags else '')
    if n in DESC: note += ': ' + DESC[n]
    if 'DVAR_ROM' in flags:
        left = f'// {n}' + (f' = {v}' if v is not None and v != '""' else '')
    else:
        left = f'// set {n} ' + (v if v is not None else '<set at startup>')
    return left.ljust(46) + ' // ' + note

out = []
out.append('''// Example server configuration for CoD2rev-Plus.
// Copy it to the "main" folder of the game as server.cfg and edit it.
// Do not commit your real server.cfg: it holds passwords.
//
// The first part sets the variables most servers change.
// The second part lists every other variable the server registers, commented
// out and with its default value, so copying this file changes nothing else.
// Remove the leading "//" to use one.
//
// Not listed here: the scr_* variables of each gametype, which are defined by
// the game scripts inside the .iwd files and not by the server.

// =============================================================================
// Common settings
// =============================================================================

''')
out.append(COMMON)
out.append('''
// =============================================================================
// Every other variable (defaults shown)
// =============================================================================
// Notes after each variable:
//   read-only             set by the server, cannot be changed
//   command line only     must be given as "+set name value" when starting
//   needs sv_cheats 1     ignored unless cheats are enabled
''')
listed = set()
for title, pred in GROUPS:
    names = [n for n in seen if n not in common_names and n not in listed and pred(seen[n][0]['file'])]
    listed.update(names)
    out.append(f'\n// --- {title} ---\n')
    for n in names: out.append(entry(n) + '\n')
missing = [n for n in seen if n not in common_names and n not in listed]
assert not missing, missing
unknown = common_names - set(seen)
assert not unknown, unknown
open(OUTPUT, 'w', encoding='utf-8', newline='\n').write(''.join(out))
print(f'{OUTPUT}: {len(seen)} dvars, {len(common_names)} set, {len(listed)} listed with their defaults')

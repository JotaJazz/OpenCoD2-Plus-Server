#include "gsc.hpp"
#include "plusid.hpp"

#include <errno.h>
#include <vector>
#ifdef _WIN32
#include <windows.h>
#endif

#ifdef LIBCOD

// The Plus ID check at connect (docs/architecture/plus-id.md): the key
// proof is in plusid.hpp, the server's side (which address a signature may
// name, the dvars, the ID of each client) here.

#define PLUSID_NOTICE "This server requires a Plus ID: play with the OpenCoD2-Plus client, https://github.com/JotaJazz/OpenCoD2-Plus/releases"

static dvar_t *sv_publicAddress;
static dvar_t *sv_requirePlusId;
static dvar_t *sv_plusIdNotice;
static dvar_t *sv_plusIdSeenFile;
static char plusIds[MAX_CLIENTS][22];

// Playtime per ID (docs/architecture/plus-id.md): the file has one line per
// ID, "id first_seen seconds". A slot keeps what the file said when its player
// connected (seen, stored) and the seconds only this server counted since
// (unsaved); a save adds only those to whatever the file holds then, so two
// servers sharing the file do not lose each other's time.
struct PlusId_Seen
{
	char id[22];
	long long first, seconds;
};

static struct { long long first, stored, unsaved; } slots[MAX_CLIENTS];
static time_t lastTick, lastSave;

// A dvar's address, resolved only when its text changes: a host name would
// block the frame on every connect. False when the dvar is empty, not an
// address, 0.0.0.0 or the "localhost" of net_ip, which binds every interface.
struct PlusId_CachedAddress
{
	const char *name;
	char text[256];
	bool valid;
	netadr_t adr;
};

static PlusId_CachedAddress publicAddress = { "sv_publicAddress" }, netIp = { "net_ip" };

static bool PlusId_DvarAddress(PlusId_CachedAddress *cache, netadr_t *adr)
{
	const dvar_t *dvar = Dvar_FindVar(cache->name);
	const char *text = dvar ? dvar->current.string : "";

	if ( !cache->text[0] || strncmp(cache->text + 1, text, sizeof(cache->text) - 2) )
	{
		// a leading '+' keeps an empty dvar from looking unresolved
		Com_sprintf(cache->text, sizeof(cache->text), "+%s", text);
		cache->valid = *text && Q_stricmp(text, "localhost") && NET_StringToAdr(text, &cache->adr)
		               && cache->adr.type == NA_IP && ( cache->adr.ip[0] | cache->adr.ip[1] | cache->adr.ip[2] | cache->adr.ip[3] );
	}

	*adr = cache->adr;
	return cache->valid;
}

// RFC 1918, loopback and link-local only; not Sys_IsLANAddress, which also
// takes anyone in the /24 of one of the host's own IPs (a VPN neighbour)
static bool PlusId_IsPrivate(netadr_t adr)
{
	const unsigned char *ip = adr.ip;

	return adr.type == NA_IP && ( ip[0] == 10 || ip[0] == 127 || ( ip[0] == 169 && ip[1] == 254 )
	                              || ( ip[0] == 172 && ( ip[1] & 0xF0 ) == 16 ) || ( ip[0] == 192 && ip[1] == 168 ) );
}

bool PlusId_AddressAccepted(netadr_t signedAdr, netadr_t from)
{
	const dvar_t *port = Dvar_FindVar("net_port");
	netadr_t own;

	if ( signedAdr.type != NA_IP || !port || (unsigned short)BigShort(signedAdr.port) != port->current.integer )
		return false;

	// a private address names this server only for a packet that comes from a
	// private network too, even when it is net_ip: from a public one it may be
	// another server's relay
	if ( PlusId_IsPrivate(signedAdr) && !PlusId_IsPrivate(from) )
		return false;

	if ( PlusId_DvarAddress(&publicAddress, &own) && !memcmp(own.ip, signedAdr.ip, 4) )
		return true;

	if ( PlusId_DvarAddress(&netIp, &own) && !memcmp(own.ip, signedAdr.ip, 4) )
		return true;

	return PlusId_IsPrivate(signedAdr);
}

// the ip:port the client signed, only in the form NET_AdrToString writes, so
// that it is never resolved and the server checks the same text
static bool PlusId_SignedAddress(const char *text, netadr_t *adr)
{
	return *text && strspn(text, "0123456789.:") == strlen(text) && NET_StringToAdr(text, adr)
	       && adr->type == NA_IP && !strcmp(NET_AdrToString(*adr), text);
}

const char *PlusId_CheckConnect(netadr_t from, char *userinfo, int challenge, char idOut[22])
{
	static leakyBucket_t bucket;
	char pk[PLUSID_PK_HEX + 2], ps[PLUSID_PS_HEX + 2], pa[64];
	netadr_t signedAdr;

	idOut[0] = '\0';
	Q_strncpyz(pk, Info_ValueForKey(userinfo, "pk"), sizeof(pk));
	Q_strncpyz(ps, Info_ValueForKey(userinfo, "ps"), sizeof(ps));
	Q_strncpyz(pa, Info_ValueForKey(userinfo, "pa"), sizeof(pa));
	// only for this check: not kept in the userinfo nor shown to scripts
	Info_RemoveKey(userinfo, "pk");
	Info_RemoveKey(userinfo, "ps");
	Info_RemoveKey(userinfo, "pa");

	if ( *pk || *ps || *pa )
	{
		if ( !PlusId_SignedAddress(pa, &signedAdr) )
			Com_Printf("plusid: malformed signed address from %s\n", NET_AdrToString(from));
		else if ( !PlusId_AddressAccepted(signedAdr, from) )
			Com_Printf("plusid: %s signed for another address, %s\n", NET_AdrToString(from), pa);
		// the challenge and SV_DirectConnect's limit per address already
		// passed; this caps the CPU all addresses together can take
		else if ( SVC_RateLimit(&bucket, 50, 20) )
			Com_Printf("plusid: too many verifications, %s connects without a Plus ID\n", NET_AdrToString(from));
		else if ( !PlusId_Verify(pk, ps, challenge, pa, idOut) )
		{
			idOut[0] = '\0';
			Com_Printf("plusid: invalid signature from %s\n", NET_AdrToString(from));
		}
	}

	if ( !idOut[0] && sv_requirePlusId->current.boolean )
		return *sv_plusIdNotice->current.string ? sv_plusIdNotice->current.string : PLUSID_NOTICE;

	return NULL;
}

static void PlusId_SeenPath(char *path, size_t size)
{
	const char *name = sv_plusIdSeenFile->current.string, *home = Dvar_FindVar("fs_homepath") ? Dvar_FindVar("fs_homepath")->current.string : "";

	if ( name[0] == '/' || name[0] == '\\' || name[1] == ':' || !*home )
		Q_strncpyz(path, name, size);
	else
		Com_sprintf(path, size, "%s/%s", home, name);
}

// False when the file exists and cannot be read whole: it is then never
// overwritten. A missing file is an empty list.
static bool PlusId_ReadSeen(const char *path, std::vector<PlusId_Seen> &list)
{
	FILE *f = fopen(path, "r");
	PlusId_Seen e;
	char id[64];
	long long first, seconds;
	int n;

	if ( !f )
		return errno == ENOENT;

	while ( ( n = fscanf(f, "%63s %lld %lld", id, &first, &seconds) ) == 3 )
	{
		if ( strlen(id) >= sizeof(e.id) )
			break;
		strcpy(e.id, id);
		e.first = first;
		e.seconds = seconds;
		list.push_back(e);
	}

	bool ok = n == EOF && !ferror(f);
	fclose(f);
	return ok;
}

// the time of dropped players that a save has not written yet: kept until one does
static std::vector<PlusId_Seen> pending;

static PlusId_Seen *PlusId_Find(std::vector<PlusId_Seen> &list, const char *id, long long first)
{
	for ( size_t k = 0; k < list.size(); k++ )
	{
		if ( !strcmp(list[k].id, id) )
			return &list[k];
	}

	PlusId_Seen e = { "", first, 0 };
	strcpy(e.id, id);
	list.push_back(e);
	return &list.back();
}

static void PlusId_Save()
{
	std::vector<PlusId_Seen> list;
	char path[MAX_OSPATH * 2], tmp[MAX_OSPATH * 2 + 24];
	bool any = !pending.empty();

	lastSave = time(NULL);
	for ( int i = 0; i < MAX_CLIENTS; i++ )
		any = any || ( plusIds[i][0] && slots[i].unsaved > 0 );
	if ( !any )
		return;

	PlusId_SeenPath(path, sizeof(path));
	if ( !PlusId_ReadSeen(path, list) )
	{
		Com_Printf("plusid: cannot read %s, playtime not saved\n", path);
		return;
	}

	// the file is only changed in memory here; the slots are marked saved after the rename
	for ( size_t k = 0; k < pending.size(); k++ )
	{
		PlusId_Seen *e = PlusId_Find(list, pending[k].id, pending[k].first);
		e->first = e->first < pending[k].first ? e->first : pending[k].first;
		e->seconds += pending[k].seconds;
	}
	for ( int i = 0; i < MAX_CLIENTS; i++ )
	{
		if ( !plusIds[i][0] || slots[i].unsaved <= 0 )
			continue;

		PlusId_Seen *e = PlusId_Find(list, plusIds[i], slots[i].first);
		e->first = e->first < slots[i].first ? e->first : slots[i].first;
		e->seconds += slots[i].unsaved;
	}

	// a name of its own: servers sharing the file never write the same temporary file
	// shortcut: two servers saving in the same instant can lose one interval; add a lock if groups report it
	Com_sprintf(tmp, sizeof(tmp), "%s.tmp.%d", path, (int)getpid());
	FILE *f = fopen(tmp, "w");
	bool ok = f != NULL;
	for ( size_t k = 0; ok && k < list.size(); k++ )
		ok = fprintf(f, "%s %lld %lld\n", list[k].id, list[k].first, list[k].seconds) > 0;
	ok = f && fclose(f) == 0 && ok;
#ifdef _WIN32
	ok = ok && MoveFileExA(tmp, path, MOVEFILE_REPLACE_EXISTING);
#else
	ok = ok && rename(tmp, path) == 0;
#endif
	if ( !ok )
	{
		Com_Printf("plusid: cannot write %s, playtime not saved\n", path);
		return;
	}

	pending.clear();
	for ( int i = 0; i < MAX_CLIENTS; i++ )
	{
		if ( !plusIds[i][0] || slots[i].unsaved <= 0 )
			continue;

		PlusId_Seen *e = PlusId_Find(list, plusIds[i], 0);
		slots[i].first = e->first;
		slots[i].stored = e->seconds;
		slots[i].unsaved = 0;
	}
}

// adds the seconds that passed to every connected player with an ID; a
// zombie slot keeps its ID until freed but is not playing
static void PlusId_Tick()
{
	time_t now = time(NULL);

	if ( !lastTick || now < lastTick )
		lastTick = now;
	for ( int i = 0; i < MAX_CLIENTS; i++ )
	{
		if ( plusIds[i][0] && svs.clients[i].state >= CS_CONNECTED )
			slots[i].unsaved += now - lastTick;
	}
	lastTick = now;
}

void PlusId_Frame()
{
	PlusId_Tick();
	if ( time(NULL) - lastSave >= 60 )
		PlusId_Save();
}

// at the end of the map and at shutdown
void PlusId_Shutdown()
{
	PlusId_Tick();
	PlusId_Save();
}

void PlusId_ClientConnected(int clientNum, const char *id)
{
	std::vector<PlusId_Seen> list;
	char path[MAX_OSPATH * 2];

	Q_strncpyz(plusIds[clientNum], id, sizeof(plusIds[clientNum]));
	slots[clientNum].first = time(NULL);
	slots[clientNum].stored = slots[clientNum].unsaved = 0;
	if ( !*id )
		return;

	PlusId_Tick();
	PlusId_SeenPath(path, sizeof(path));
	PlusId_ReadSeen(path, list);
	for ( size_t k = 0; k < list.size(); k++ )
	{
		if ( !strcmp(list[k].id, id) )
		{
			slots[clientNum].first = list[k].first;
			slots[clientNum].stored = list[k].seconds;
		}
	}
}

void PlusId_ClientDropped(int clientNum)
{
	if ( plusIds[clientNum][0] )
	{
		PlusId_Tick();
		if ( slots[clientNum].unsaved > 0 )
		{
			PlusId_Seen *e = PlusId_Find(pending, plusIds[clientNum], slots[clientNum].first);
			e->seconds += slots[clientNum].unsaved;
			// now pending only: the save must not write them again from the slot
			slots[clientNum].unsaved = 0;
		}
		PlusId_Save();
	}
	plusIds[clientNum][0] = '\0';
	slots[clientNum].unsaved = 0;
}

int PlusId_Playtime(int clientNum)
{
	return plusIds[clientNum][0] ? (int)( slots[clientNum].stored + slots[clientNum].unsaved ) : 0;
}

int PlusId_FirstSeenAgo(int clientNum)
{
	return plusIds[clientNum][0] ? (int)( time(NULL) - slots[clientNum].first ) : 0;
}

const char *PlusId_ForClient(int clientNum)
{
	return plusIds[clientNum];
}

void PlusId_RegisterDvars()
{
	sv_publicAddress = Dvar_RegisterString("sv_publicAddress", "", DVAR_ARCHIVE | DVAR_CHANGEABLE_RESET);
	sv_requirePlusId = Dvar_RegisterBool("sv_requirePlusId", false, DVAR_ARCHIVE | DVAR_CHANGEABLE_RESET);
	sv_plusIdNotice = Dvar_RegisterString("sv_plusIdNotice", "", DVAR_ARCHIVE | DVAR_CHANGEABLE_RESET);
	sv_plusIdSeenFile = Dvar_RegisterString("sv_plusIdSeenFile", "plusid_seen.txt", DVAR_ARCHIVE | DVAR_CHANGEABLE_RESET);
}

// at the first map, when the config has run and net_ip is set
void PlusId_SpawnServer()
{
	static bool warned;
	netadr_t own;

	if ( !warned && !PlusId_DvarAddress(&publicAddress, &own) && !PlusId_DvarAddress(&netIp, &own) )
		Com_Printf("plusid: no sv_publicAddress, only LAN players get a Plus ID\n");
	warned = true;
}

static void PlusId_Status_f()
{
	if ( !com_sv_running->current.boolean )
	{
		Com_Printf("Server is not running.\n");
		return;
	}

	PlusId_Tick();
	Com_Printf("num name id playtime first_seen_ago\n");
	for ( int i = 0; i < sv_maxclients->current.integer; i++ )
	{
		if ( svs.clients[i].state >= CS_CONNECTED )
			Com_Printf("%i %s %s %i %i\n", i, svs.clients[i].name, plusIds[i][0] ? plusIds[i] : "-", PlusId_Playtime(i), PlusId_FirstSeenAgo(i));
	}
}

void PlusId_AddCommands()
{
	Cmd_AddCommand("plusIdStatus", PlusId_Status_f);
}

#endif

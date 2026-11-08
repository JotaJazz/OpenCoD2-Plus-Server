#include "gsc.hpp"
#include "plusid.hpp"

#ifdef LIBCOD

// The Plus ID check at connect (docs/architecture/plus-id.md): the key
// proof is in plusid.hpp, the server's side (which address a signature may
// name, the dvars, the ID of each client) here.

#define PLUSID_NOTICE "This server requires a Plus ID: play with the OpenCoD2-Plus client, https://github.com/JotaJazz/OpenCoD2-Plus/releases"

static dvar_t *sv_publicAddress;
static dvar_t *sv_requirePlusId;
static dvar_t *sv_plusIdNotice;
static char plusIds[MAX_CLIENTS][22];

// 0.0.0.0 when the dvar is empty, not an address or the "localhost" of net_ip,
// which binds every interface
static bool PlusId_DvarAddress(const char *name, netadr_t *adr)
{
	const dvar_t *dvar = Dvar_FindVar(name);

	// shortcut: a host name is resolved on each connect, an IP is cheap; cache it if admins use names
	return dvar && *dvar->current.string && Q_stricmp(dvar->current.string, "localhost")
	       && NET_StringToAdr(dvar->current.string, adr) && adr->type == NA_IP && ( adr->ip[0] | adr->ip[1] | adr->ip[2] | adr->ip[3] );
}

bool PlusId_AddressAccepted(netadr_t signedAdr, netadr_t from)
{
	const dvar_t *port = Dvar_FindVar("net_port");
	netadr_t own;

	if ( signedAdr.type != NA_IP || !port || (unsigned short)BigShort(signedAdr.port) != port->current.integer )
		return false;

	if ( PlusId_DvarAddress("sv_publicAddress", &own) && !memcmp(own.ip, signedAdr.ip, 4) )
		return true;

	if ( PlusId_DvarAddress("net_ip", &own) && !memcmp(own.ip, signedAdr.ip, 4) )
		return true;

	// a private address names this server only for a packet that comes from a
	// private network too: from a public one it may be another server's relay
	return Sys_IsLANAddress(signedAdr) && Sys_IsLANAddress(from);
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

void PlusId_ClientConnected(int clientNum, const char *id)
{
	Q_strncpyz(plusIds[clientNum], id, sizeof(plusIds[clientNum]));
}

void PlusId_ClientDropped(int clientNum)
{
	plusIds[clientNum][0] = '\0';
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
}

// at the first map, when the config has run and net_ip is set
void PlusId_SpawnServer()
{
	static bool warned;
	netadr_t own;

	if ( !warned && !PlusId_DvarAddress("sv_publicAddress", &own) && !PlusId_DvarAddress("net_ip", &own) )
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

	Com_Printf("num name id\n");
	for ( int i = 0; i < sv_maxclients->current.integer; i++ )
	{
		if ( svs.clients[i].state >= CS_CONNECTED )
			Com_Printf("%i %s %s\n", i, svs.clients[i].name, plusIds[i][0] ? plusIds[i] : "-");
	}
}

void PlusId_AddCommands()
{
	Cmd_AddCommand("plusIdStatus", PlusId_Status_f);
}

#endif

#include "../qcommon/qcommon.h"
#include "server.h"

#if defined(COD2_PLUS) && !defined(_WIN32)

#include "sv_www_plus.h"

#include <pthread.h>
#include <stdio.h>
#include <string.h>

extern dvar_t *fs_homepath;
extern dvar_t *fs_basepath;
extern dvar_t *fs_cdpath;
void FS_BuildOSPath(const char *base, const char *game, const char *qpath, char *ospath);

typedef struct
{
	bool used;
	uint32_t ip;
	char name[MAX_QPATH];
	char ospath[MAX_OSPATH];
	int size;
	int expires;
} wwwGrant_t;

static wwwGrant_t www_grants[MAX_CLIENTS * 2];
static pthread_mutex_t www_mutex = PTHREAD_MUTEX_INITIALIZER;

bool SV_WwwPlus_IsAuto(void)
{
	return !I_stricmp(sv_wwwBaseURL->current.string, "auto");
}

// The path FS_SV_FOpenFileRead would open, in its order, without keeping the file open
static bool WwwPlus_ResolvePath(const char *name, char *ospath)
{
	const char *bases[3] = { fs_homepath->current.string, fs_basepath->current.string, fs_cdpath->current.string };

	for (int i = 0; i < 3; i++)
	{
		// FS_BuildOSPath is fatal on overflow
		if (strlen(bases[i]) + strlen(name) + 3 >= MAX_OSPATH)
			continue;
		FS_BuildOSPath(bases[i], name, "", ospath);
		ospath[strlen(ospath) - 1] = '\0'; // trailing slash
		FILE *f = fopen(ospath, "rb");
		if (f)
		{
			fclose(f);
			return true;
		}
	}
	return false;
}

bool SV_WwwPlus_Grant(netadr_t adr, const char *downloadName, int size)
{
	char ospath[MAX_OSPATH];
	uint32_t ip;
	int now = Sys_Milliseconds();
	wwwGrant_t *slot = NULL;

	if (adr.type != NA_IP || strlen(downloadName) >= MAX_QPATH || !WwwPlus_ResolvePath(downloadName, ospath))
		return false;
	memcpy(&ip, adr.ip, 4);

	pthread_mutex_lock(&www_mutex);
	for (wwwGrant_t *g = www_grants; g < www_grants + MAX_CLIENTS * 2; g++)
	{
		if (g->used && g->ip == ip && !strcmp(g->name, downloadName))
		{
			slot = g; // renew
			break;
		}
		if (!slot && (!g->used || g->expires - now <= 0))
			slot = g;
	}
	if (slot)
	{
		slot->used = true;
		slot->ip = ip;
		I_strncpyz(slot->name, downloadName, sizeof(slot->name));
		I_strncpyz(slot->ospath, ospath, sizeof(slot->ospath));
		slot->size = size;
		slot->expires = now + WWW_PLUS_GRANT_MS;
	}
	pthread_mutex_unlock(&www_mutex);
	return slot != NULL;
}

bool SV_WwwPlus_FindGrant(uint32_t ip, const char *name, char *ospath, int ospathSize, int *size)
{
	bool found = false;
	int now = Sys_Milliseconds();

	pthread_mutex_lock(&www_mutex);
	for (wwwGrant_t *g = www_grants; g < www_grants + MAX_CLIENTS * 2; g++)
	{
		if (g->used && g->ip == ip && g->expires - now > 0 && !strcmp(g->name, name))
		{
			I_strncpyz(ospath, g->ospath, ospathSize);
			*size = g->size;
			found = true;
			break;
		}
	}
	pthread_mutex_unlock(&www_mutex);
	return found;
}

void SV_WwwPlus_Frame(void)
{
}

#endif

#include "../qcommon/qcommon.h"
#include "server.h"

#if defined(COD2_PLUS) && !defined(_WIN32)

#include "sv_www_plus.h"

#include <arpa/inet.h>
#include <atomic>
#include <ctype.h>
#include <errno.h>
#include <limits.h>
#include <netinet/in.h>
#include <poll.h>
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>

extern dvar_t *fs_homepath;
extern dvar_t *fs_basepath;
extern dvar_t *fs_cdpath;
void FS_BuildOSPath(const char *base, const char *game, const char *qpath, char *ospath);
qboolean Sys_StringToSockaddr(const char *s, struct sockaddr *sadr);

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
static pthread_mutex_t www_mutex = PTHREAD_MUTEX_INITIALIZER; // the grants and the log
static std::atomic<bool> www_listening(false);

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

	// no listener: nothing to redirect to, the UDP download follows
	if (!www_listening.load() || adr.type != NA_IP || strlen(downloadName) >= MAX_QPATH || !WwwPlus_ResolvePath(downloadName, ospath))
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

/*
The worker: one thread, a poll loop over the listener and the connections.
Everything from a socket is hostile; it serves only a live grant's file, to
its IP, under its exact name. It never calls FS_*, Dvar_* or Com_Printf.
*/

#define WWW_CONNS 64 // the most sv_wwwMaxConnections allows
#define WWW_HEAD_MAX 4096
#define WWW_HEAD_MS 10000 // the request head must arrive within this of the accept
#define WWW_STALL_MS 30000 // a transfer with no bytes moving for this is closed
#define WWW_SLICE_MS 100
#define WWW_CHUNK 65536
#define WWW_LOG_LINES 16

typedef struct
{
	int fd; // -1 free
	uint32_t ip;
	int accepted;
	int moved; // last time bytes moved
	int headLen;
	char head[WWW_HEAD_MAX + 1];
	char reply[256]; // the response head, sent before the body
	int replyLen;
	int replySent;
	FILE *file; // NULL: no body
	int size;
	int sent; // body bytes
	char name[MAX_QPATH];
} wwwConn_t;

static int www_listener = -1;
static pthread_t www_thread;
static std::atomic<bool> www_quit(false);
static std::atomic<int> www_maxRate(1024);
static std::atomic<int> www_maxConns(4);
static std::atomic<int> www_maxPerIP(2);

static wwwConn_t www_conns[WWW_CONNS];
static char www_chunk[WWW_CHUNK];

// finished downloads, printed by SV_WwwPlus_Frame on the main thread
static char www_log[WWW_LOG_LINES][MAX_QPATH + 96];
static int www_logCount;

static void WwwPlus_Log(const wwwConn_t *c, int now)
{
	const unsigned char *b = (const unsigned char *)&c->ip;

	pthread_mutex_lock(&www_mutex);
	if (www_logCount < WWW_LOG_LINES)
	{
		Com_sprintf(www_log[www_logCount++], sizeof(www_log[0]), "www: %u.%u.%u.%u %s %i bytes in %.1f s\n",
		            b[0], b[1], b[2], b[3], c->name, c->size, (now - c->accepted) / 1000.0f);
	}
	pthread_mutex_unlock(&www_mutex);
}

static void WwwPlus_Close(wwwConn_t *c)
{
	if (c->file)
		fclose(c->file);
	close(c->fd);
	c->fd = -1;
	c->file = NULL;
}

static void WwwPlus_Reply(wwwConn_t *c, const char *status)
{
	c->replyLen = Com_sprintf(c->reply, sizeof(c->reply),
	                          "HTTP/1.1 %s\r\nContent-Length: 0\r\nConnection: close\r\n\r\n", status);
}

// The request target as a grant name: percent-decoded, one leading slash
// stripped, no query, fragment, empty, . or .. segment, or control byte
static bool WwwPlus_DecodePath(const char *target, char *name, int nameSize)
{
	int len = 0;

	if (*target++ != '/')
		return false;
	while (*target)
	{
		int ch = (unsigned char)*target++;
		if (ch == '?' || ch == '#')
			return false;
		if (ch == '%')
		{
			char hex[3] = { target[0], target[1], 0 };
			if (!isxdigit((unsigned char)hex[0]) || !isxdigit((unsigned char)hex[1]))
				return false;
			ch = (int)strtol(hex, NULL, 16);
			target += 2;
		}
		if (ch < 0x20 || ch == 0x7f || ch == '\\' || len + 1 >= nameSize)
			return false;
		name[len++] = (char)ch;
	}
	name[len] = '\0';

	for (const char *seg = name;; )
	{
		const char *slash = strchr(seg, '/');
		int segLen = slash ? (int)(slash - seg) : (int)strlen(seg);
		if (!segLen || (segLen == 1 && seg[0] == '.') || (segLen == 2 && seg[0] == '.' && seg[1] == '.'))
			return false;
		if (!slash)
			return true;
		seg = slash + 1;
	}
}

// A whole head arrived: decide the response
static void WwwPlus_Request(wwwConn_t *c)
{
	char *method = c->head;
	char *target = strchr(method, ' ');
	char *version = target ? strchr(target + 1, ' ') : NULL;
	char *eol = strpbrk(c->head, "\r\n");
	char ospath[MAX_OSPATH];
	struct stat st;
	bool head;

	if (!target || !version || version > eol || strncmp(version + 1, "HTTP/", 5))
	{
		WwwPlus_Reply(c, "400 Bad Request");
		return;
	}
	*target++ = '\0';
	*version = '\0';
	head = !strcmp(method, "HEAD");
	if (!head && strcmp(method, "GET"))
	{
		c->replyLen = Com_sprintf(c->reply, sizeof(c->reply),
		                          "HTTP/1.1 405 Method Not Allowed\r\nAllow: GET, HEAD\r\nContent-Length: 0\r\nConnection: close\r\n\r\n");
		return;
	}
	if (!WwwPlus_DecodePath(target, c->name, sizeof(c->name)) || !SV_WwwPlus_FindGrant(c->ip, c->name, ospath, sizeof(ospath), &c->size))
	{
		WwwPlus_Reply(c, "404 Not Found");
		return;
	}
	c->file = fopen(ospath, "rb");
	// the file changed since the grant: the size the client was told is wrong
	if (!c->file || fstat(fileno(c->file), &st) || !S_ISREG(st.st_mode) || st.st_size != c->size)
	{
		if (c->file)
			fclose(c->file);
		c->file = NULL;
		WwwPlus_Reply(c, "404 Not Found");
		return;
	}
	c->replyLen = Com_sprintf(c->reply, sizeof(c->reply),
	                          "HTTP/1.1 200 OK\r\nContent-Length: %i\r\nContent-Type: application/octet-stream\r\nConnection: close\r\n\r\n", c->size);
	if (head)
	{
		fclose(c->file);
		c->file = NULL;
	}
}

static void WwwPlus_Accept(int now)
{
	for (int n = 0; n < 16; n++)
	{
		struct sockaddr_in from;
		socklen_t fromLen = sizeof(from);
		int fd = accept4(www_listener, (struct sockaddr *)&from, &fromLen, SOCK_NONBLOCK | SOCK_CLOEXEC);
		wwwConn_t *slot = NULL;
		int open = 0, fromIP = 0;
		uint32_t ip;

		if (fd < 0)
			return;
		memcpy(&ip, &from.sin_addr, 4); // network order, as the grants
		for (int i = 0; i < WWW_CONNS; i++)
		{
			if (www_conns[i].fd < 0)
			{
				if (!slot)
					slot = &www_conns[i];
				continue;
			}
			open++;
			if (www_conns[i].ip == ip)
				fromIP++;
		}
		// over a limit: closed at once, the client falls back to the UDP download
		if (!slot || open >= www_maxConns.load() || fromIP >= www_maxPerIP.load())
		{
			close(fd);
			continue;
		}
		memset(slot, 0, sizeof(*slot));
		slot->fd = fd;
		slot->ip = ip;
		slot->accepted = slot->moved = now;
	}
}

// Reads the head; true while the connection stays open
static bool WwwPlus_ReadHead(wwwConn_t *c, int now)
{
	int got = recv(c->fd, c->head + c->headLen, WWW_HEAD_MAX - c->headLen, 0);

	if (got == 0 || (got < 0 && errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR))
		return false;
	if (got < 0)
		return true;
	c->headLen += got;
	c->head[c->headLen] = '\0';
	c->moved = now;
	if (strlen(c->head) != (size_t)c->headLen)
		return false; // a NUL in the head
	if (strstr(c->head, "\r\n\r\n") || strstr(c->head, "\n\n"))
	{
		WwwPlus_Request(c);
		return true;
	}
	return c->headLen < WWW_HEAD_MAX;
}

// Sends the response head, then up to budget body bytes; true while open
static bool WwwPlus_Send(wwwConn_t *c, int now, int *budget)
{
	if (c->replySent < c->replyLen)
	{
		int put = send(c->fd, c->reply + c->replySent, c->replyLen - c->replySent, MSG_NOSIGNAL);
		if (put < 0)
			return errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR;
		c->replySent += put;
		c->moved = now;
		if (c->replySent < c->replyLen)
			return true;
	}
	if (!c->file)
		return false; // a reply without a body: done
	if (c->sent < c->size && *budget > 0)
	{
		int want = c->size - c->sent;
		if (want > WWW_CHUNK)
			want = WWW_CHUNK;
		if (want > *budget)
			want = *budget;
		int got = pread(fileno(c->file), www_chunk, want, c->sent);
		if (got <= 0)
			return false;
		int put = send(c->fd, www_chunk, got, MSG_NOSIGNAL);
		if (put < 0)
			return errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR;
		c->sent += put;
		*budget -= put;
		c->moved = now;
	}
	if (c->sent < c->size)
		return true;
	WwwPlus_Log(c, now);
	return false;
}

static void *WwwPlus_Worker(void *)
{
	struct pollfd fds[WWW_CONNS + 1];
	int map[WWW_CONNS + 1];
	int last = Sys_Milliseconds();
	double tokens = 0;
	int turn = 0;

	for (int i = 0; i < WWW_CONNS; i++)
		www_conns[i].fd = -1;

	while (!www_quit.load())
	{
		int rate = www_maxRate.load();
		int now = Sys_Milliseconds();
		int budget, n = 0;

		// the token bucket: rate KB/s for all transfers, at most two slices saved
		tokens += (double)rate * 1024 * (now - last) / 1000;
		if (tokens > rate * 1024.0 * 2 * WWW_SLICE_MS / 1000)
			tokens = rate * 1024.0 * 2 * WWW_SLICE_MS / 1000;
		last = now;

		fds[n].fd = www_listener;
		fds[n].events = POLLIN;
		map[n++] = -1;
		for (int i = 0; i < WWW_CONNS; i++)
		{
			wwwConn_t *c = &www_conns[i];
			if (c->fd < 0)
				continue;
			fds[n].fd = c->fd;
			if (!c->replyLen)
				fds[n].events = POLLIN;
			else if (c->replySent < c->replyLen || !rate || tokens >= 1)
				fds[n].events = POLLOUT;
			else
				fds[n].events = 0; // waits for tokens; errors still wake it
			map[n++] = i;
		}
		if (poll(fds, n, WWW_SLICE_MS) < 0 && errno != EINTR)
			break;
		now = Sys_Milliseconds();

		if (fds[0].revents & POLLIN)
			WwwPlus_Accept(now);

		budget = rate ? (int)tokens : INT_MAX;
		// in turn, so one transfer cannot take every slice's tokens
		turn++;
		for (int k = 1; k < n; k++)
		{
			int j = 1 + (k - 1 + turn) % (n - 1);
			wwwConn_t *c = &www_conns[map[j]];
			bool open = true;

			if (fds[j].revents & (POLLERR | POLLHUP | POLLNVAL))
				open = false;
			else if (!c->replyLen)
				open = !(fds[j].revents & POLLIN) || WwwPlus_ReadHead(c, now);
			else if (fds[j].revents & POLLOUT)
				open = WwwPlus_Send(c, now, &budget);

			if (open && !c->replyLen && now - c->accepted >= WWW_HEAD_MS)
				open = false;
			if (open && now - c->moved >= WWW_STALL_MS)
				open = false;
			if (!open)
				WwwPlus_Close(c);
		}
		if (rate)
			tokens -= (int)tokens - budget;
	}

	for (int i = 0; i < WWW_CONNS; i++)
	{
		if (www_conns[i].fd >= 0)
			WwwPlus_Close(&www_conns[i]);
	}
	return NULL;
}

void SV_WwwPlus_Start(void)
{
	struct sockaddr_in address;
	dvar_t *ip = Dvar_FindVar("net_ip");
	dvar_t *port = Dvar_FindVar("net_port");
	int one = 1;
	int fd;

	if (www_listening.load() || !SV_WwwPlus_IsAuto() || !ip || !port)
		return;

	memset(&address, 0, sizeof(address));
	// the address the UDP socket took (NET_IPSocket), on the port it got
	if (!ip->current.string[0] || !I_stricmp(ip->current.string, "localhost"))
		address.sin_addr.s_addr = INADDR_ANY;
	else if (!Sys_StringToSockaddr(ip->current.string, (struct sockaddr *)&address))
	{
		Com_Printf("WARNING: sv_wwwBaseURL auto: can't resolve net_ip %s; Plus clients get the UDP download\n", ip->current.string);
		return;
	}
	address.sin_family = AF_INET;
	address.sin_port = htons((unsigned short)port->current.integer);

	fd = socket(AF_INET, SOCK_STREAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0);
	if (fd < 0 || setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one))
	        || bind(fd, (struct sockaddr *)&address, sizeof(address)) || listen(fd, 16))
	{
		Com_Printf("WARNING: sv_wwwBaseURL auto: can't open TCP port %i (%s); Plus clients get the UDP download\n",
		           port->current.integer, strerror(errno));
		if (fd >= 0)
			close(fd);
		return;
	}

	www_listener = fd;
	www_quit = false;
	SV_WwwPlus_Frame(); // the limits, before the first connection
	// the engine's signal handlers stay on the main thread
	sigset_t all, old;
	sigfillset(&all);
	pthread_sigmask(SIG_SETMASK, &all, &old);
	int err = pthread_create(&www_thread, NULL, WwwPlus_Worker, NULL);
	pthread_sigmask(SIG_SETMASK, &old, NULL);
	if (err)
	{
		Com_Printf("WARNING: sv_wwwBaseURL auto: can't start the HTTP thread; Plus clients get the UDP download\n");
		close(fd);
		www_listener = -1;
		return;
	}
	www_listening = true;
	Com_Printf("Serving sv_wwwBaseURL auto downloads on TCP port %i\n", port->current.integer);
}

void SV_WwwPlus_Stop(void)
{
	if (!www_listening.load())
		return;
	www_listening = false;
	www_quit = true;
	pthread_join(www_thread, NULL);
	close(www_listener);
	www_listener = -1;
	SV_WwwPlus_Frame(); // the last log lines
}

void SV_WwwPlus_Frame(void)
{
	char lines[WWW_LOG_LINES][sizeof(www_log[0])];
	int count;

	www_maxRate = sv_wwwMaxRate->current.integer;
	www_maxConns = sv_wwwMaxConnections->current.integer;
	www_maxPerIP = sv_wwwMaxPerIP->current.integer;

	pthread_mutex_lock(&www_mutex);
	count = www_logCount;
	memcpy(lines, www_log, sizeof(lines[0]) * count);
	www_logCount = 0;
	pthread_mutex_unlock(&www_mutex);

	for (int i = 0; i < count; i++)
		Com_Printf("%s", lines[i]);
}

#endif

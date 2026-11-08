#!/bin/sh
# Starts the OpenCoD2-Plus Server using the game files in this folder.
# Usage: [CFG=plus.cfg] ./iniciar_cod2rev.sh [lan|internet]
#   lan       (default) LAN or direct IP only; accepts clients without a valid CD key
#   internet  also announces the server to the master servers
# The +set values come before +exec, so server.cfg can change them, except
# logfileRotate: the log has already rotated when server.cfg runs.
# CFG picks another config in main, e.g. plus.cfg for a 60 Hz Plus server.
cd "$(dirname "$0")" || exit 1

PORT=28960
CFG=${CFG:-server.cfg}
MODE=1
CRACKED="+set sv_cracked 1"
if [ "$1" = "internet" ]; then
	MODE=2
	CRACKED=
fi

exec ./cod2rev_lnxded +set dedicated "$MODE" +set net_port "$PORT" +set logfile 2 +set logfileRotate 5 $CRACKED +exec "$CFG" +map mp_toujane

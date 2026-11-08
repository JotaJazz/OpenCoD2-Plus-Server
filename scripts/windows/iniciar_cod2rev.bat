@echo off
rem Starts the OpenCoD2-Plus Server using the game files in this folder.
rem Usage: iniciar_cod2rev.bat [lan|internet] [config]
rem   lan       (default) LAN or direct IP only; accepts clients without a valid CD key
rem   internet  also announces the server to the master servers
rem The +set values come before +exec, so server.cfg can change them, except
rem logfileRotate: the log has already rotated when server.cfg runs.
rem config picks another cfg in main instead of server.cfg, e.g. 20hz.cfg;
rem the name cannot have spaces: the server takes no quotes after +exec.
rem If the game runs on this PC, start the server first, or the game takes port 28960
rem and the server moves to the next free one.
cd /d "%~dp0"
set PORT=28960
set MODE=1
set CFG=server.cfg
if not "%~2"=="" set "CFG=%~2"
set CRACKED=+set sv_cracked 1
if /i "%~1"=="internet" (
	set MODE=2
	set CRACKED=
)
start "" cod2rev_win32.exe +set dedicated %MODE% +set net_port %PORT% +set logfile 2 +set logfileRotate 5 %CRACKED% +exec %CFG% +map mp_toujane

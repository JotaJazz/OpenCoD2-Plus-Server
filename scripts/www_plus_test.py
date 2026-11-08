#!/usr/bin/env python3
"""Checks the Plus server's own HTTP downloads (sv_wwwBaseURL auto) on a make PLUS=1 build.

    python3 scripts/www_plus_test.py /path/to/CoD2 [--binary bin/cod2rev_lnxded]

A minimal Plus client asks for mod iwds and the redirect it gets is checked;
the folder must hold only the stock iwds. Exits with 0 when every check passes.
"""
import argparse, os, secrets, subprocess, sys, tempfile, zipfile

import cod2client, smoke_test

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RCON = 'wwwplus_rcon'
MOD = 'main/zz_www_plus.iwd'
REFUSED = b'EXE_CANTAUTODLGAMEIWD'


def ask(port, server_id, name):
    """Connects a Plus client, asks for name and returns (reply bytes, redirects)."""
    client = cod2client.Client(port)
    try:
        refused = client.connect(118, 'wwwplus')
        assert refused is None, refused
        assert client.request_gamestate(server_id)
        reply = client.download(server_id, name)
        return reply, client.redirects
    finally:
        client.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('game_dir')
    ap.add_argument('--binary', default=os.path.join(ROOT, 'bin', 'cod2rev_lnxded'))
    ap.add_argument('--map', default='mp_toujane')
    args = ap.parse_args()
    port = smoke_test.free_port()
    failures = []

    def check(name, ok, detail=''):
        print(f'{"ok  " if ok else "FAIL"} {name}' + (f' ({detail})' if detail else ''), flush=True)
        if not ok:
            failures.append(name)

    with tempfile.TemporaryDirectory(prefix='cod2_wwwplus_') as home:
        os.makedirs(os.path.join(home, 'main'))
        with zipfile.ZipFile(os.path.join(home, MOD), 'w', zipfile.ZIP_STORED) as z:
            z.writestr('www/blob.bin', secrets.token_bytes(1 << 20))
        with zipfile.ZipFile(os.path.join(home, 'main', 'zz_svr_www.iwd'), 'w') as z:
            z.writestr('www/svr.txt', 'server only\n')
        size = os.path.getsize(os.path.join(home, MOD))
        command = [os.path.abspath(args.binary), '+set', 'fs_basepath', os.path.abspath(args.game_dir),
                   '+set', 'fs_homepath', home, '+set', 'net_port', str(port), '+set', 'sv_cracked', '1',
                   '+set', 'rcon_password', RCON, '+set', 'dedicated', '1', '+set', 'sv_wwwDownload', '1',
                   '+set', 'sv_wwwBaseURL', 'auto', '+map', args.map]
        log_path = os.path.join(home, 'out.log')
        with open(log_path, 'wb') as log:
            server = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, cwd=home)
        try:
            smoke_test.wait_for(lambda: server.poll() is not None or smoke_test.query(port, 'getinfo x'), 150)
            up = server.poll() is None and smoke_test.query(port, 'getinfo x') is not None
            check('the server runs the map', up)
            if up:
                import re
                m = re.search(r'"sv_serverid" is: ?"(-?\d+)', smoke_test.rcon(port, RCON, 'sv_serverid'))
                sid = int(m.group(1))
                reply, red = ask(port, sid, MOD)
                check('plus redirect', red == [{'url': 'plus:' + MOD, 'flags': 0, 'size': size}] and b'PK' not in reply, str(red))
                for name in ('main/zz_svr_www.iwd', 'main/iw_00.iwd'):
                    reply, red = ask(port, sid, name)
                    check('svr refused ' + name, REFUSED in reply and not red, str(red))
                smoke_test.rcon(port, RCON, 'set sv_wwwBaseURL "example.invalid/dl"')
                reply, red = ask(port, sid, MOD)
                check('real url kept', [r['url'] for r in red] == ['example.invalid/dl/' + MOD], str(red))
                smoke_test.rcon(port, RCON, 'set sv_wwwBaseURL auto')
                smoke_test.rcon(port, RCON, 'set sv_wwwDlDisconnected 1')
                reply, red = ask(port, sid, MOD)
                check('disconnected flag', [r['flags'] for r in red] == [1], str(red))
            check('the server still runs', server.poll() is None, f'exit code {server.poll()}')
        finally:
            if server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    server.kill()
        if failures:
            print('\n--- last lines of the server log ---')
            print(open(log_path, encoding='latin-1').read()[-3000:])
    print('\n' + ('FAILED: ' + ', '.join(failures) if failures else 'All checks passed'))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

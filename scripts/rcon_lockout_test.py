#!/usr/bin/env python3
"""Checks that the rcon lockout survives a full table of tracked addresses.

    python3 scripts/rcon_lockout_test.py /path/to/CoD2 [--binary bin/cod2rev_lnxded]

The lockout exempts 127.x, so the test re-runs itself in a network namespace of
its own (`unshare -rn`, no root needed) with 70 addresses 10.9.0.x on its
loopback, and sends rcon from them. The server tracks 64 addresses: a locked
one must stay locked when 65 others fail once, the oldest of those must be the
one recycled, and a recent one must keep its count. The global rcon limit lets
one request a second through, so the run takes about 80 s.
"""
import argparse, os, secrets, socket, subprocess, sys, tempfile, time

from smoke_test import PREFIX, ROOT, free_port, query

TRACKED = 64  # MAX_RCON_TRACKED in src/server/sv_main_pc_mp.cpp


def rcon_from(source, port, password, command='sv_serverid'):
    """The reply to an rcon sent from `source`, or '' without one."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((source, 0))
        s.settimeout(1.0)
        s.sendto(PREFIX + f'rcon {password} {command}'.encode(), ('127.0.0.1', port))
        try:
            data, _ = s.recvfrom(65535)
        except OSError:
            return ''
    return data[len(PREFIX):].decode('latin-1')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('game_dir', help='game folder that contains "main" with the .iwd files')
    ap.add_argument('--binary', default=os.path.join(ROOT, 'bin', 'cod2rev_lnxded'))
    ap.add_argument('--map', default='mp_toujane')
    args = ap.parse_args()

    if os.environ.get('RCON_LOCKOUT_NS') != '1':
        env = dict(os.environ, RCON_LOCKOUT_NS='1')
        sys.exit(subprocess.call(['unshare', '-rn', sys.executable] + sys.argv, env=env))

    subprocess.check_call(['ip', 'link', 'set', 'lo', 'up'])
    addresses = [f'10.9.0.{i}' for i in range(1, 71)]
    for a in addresses:
        subprocess.check_call(['ip', 'addr', 'add', a + '/32', 'dev', 'lo'])

    port = free_port()
    password = secrets.token_hex(8)
    failures = []

    def check(name, ok, detail=''):
        print(f'{"ok  " if ok else "FAIL"} {name}' + (f' ({detail})' if detail else ''), flush=True)
        if not ok:
            failures.append(name)

    with tempfile.TemporaryDirectory(prefix='cod2rev_rcon_') as home:
        with open(os.path.join(home, 'server.log'), 'wb') as log:
            server = subprocess.Popen(
                [args.binary,
                 '+set', 'fs_basepath', os.path.abspath(args.game_dir),
                 '+set', 'fs_homepath', home,
                 '+set', 'dedicated', '1',
                 '+set', 'net_port', str(port),
                 '+set', 'rcon_password', password,
                 '+set', 'sv_rconMaxAttempts', '2',
                 '+set', 'sv_rconLockTime', '600',
                 '+map', args.map],
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.time() + 120
            while time.time() < deadline and server.poll() is None:
                info = query(port, 'getinfo rcon')
                if info and info[1].get('mapname') == args.map:
                    break
                time.sleep(1)
            else:
                check('server started', False, f'exit code {server.poll()}')
                return 1

            def paced(source, pw):
                time.sleep(1.1)  # the global rcon limit refills one a second
                return rcon_from(source, port, pw)

            locked, first, last = addresses[0], addresses[1], addresses[TRACKED + 1]
            check('right password answers', 'sv_serverid' in paced(locked, password))
            paced(locked, 'wrong')
            paced(locked, 'wrong')
            check('two wrong passwords lock', paced(locked, password) == '')

            # 65 more addresses fail once: the table holds 64, so two are recycled
            for a in addresses[1:TRACKED + 2]:
                paced(a, 'wrong')

            check('a locked address stays locked when the table is full', paced(locked, password) == '')
            paced(first, 'wrong')
            check('the least recently seen address was recycled', 'sv_serverid' in paced(first, password))
            paced(last, 'wrong')
            check('a recent address keeps its count', paced(last, password) == '')
        finally:
            server.terminate()
            server.wait(10)

    print('all checks passed' if not failures else f'{len(failures)} failed: {", ".join(failures)}')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

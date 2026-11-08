#!/usr/bin/env python3
"""Checks the Plus server's own HTTP downloads (sv_wwwBaseURL auto) on a make PLUS=1 build.

    python3 scripts/www_plus_test.py /path/to/CoD2 [--binary bin/cod2rev_lnxded]

A minimal Plus client asks for mod iwds and the redirect it gets is checked;
the folder must hold only the stock iwds. Exits with 0 when every check passes.
"""
import argparse, os, re, secrets, socket, subprocess, sys, tempfile, threading, time, zipfile

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


def fail_then_udp(port, server_id, name):
    """A client that refuses the redirect (the Plus 123 client refuses plus:) sends
    wwwdl fail with no ack; returns (redirects, what a second download gets)."""
    client = cod2client.Client(port)
    try:
        assert client.connect(118, 'wwwold') is None
        assert client.request_gamestate(server_id)
        client.download(server_id, name)
        redirects = client.redirects
        client.command(server_id, 'wwwdl fail')
        return redirects, client.download(server_id, name, 3.0)
    finally:
        client.close()


def http(port, request, source='127.0.0.1', timeout=15.0):
    """Sends a raw request over TCP and returns all the server sent, or None if refused."""
    try:
        s = socket.create_connection(('127.0.0.1', port), timeout, source_address=(source, 0))
    except OSError:
        return None
    with s:
        try:
            s.sendall(request)
            data = b''
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    return data
                data += chunk
        except OSError:
            return data


def get(port, path, method='GET', source='127.0.0.1'):
    """Returns (status, headers dict, body) of a request for path; status None if no reply."""
    data = http(port, f'{method} {path} HTTP/1.1\r\nHost: x\r\n\r\n'.encode(), source)
    if not data or b'\r\n\r\n' not in data:
        return None, {}, data
    head, body = data.split(b'\r\n\r\n', 1)
    lines = head.decode('latin-1').split('\r\n')
    headers = dict(l.split(': ', 1) for l in lines[1:] if ': ' in l)
    return int(lines[0].split(' ')[1]), headers, body


def open_get(port, path):
    s = socket.create_connection(('127.0.0.1', port), 5)
    s.sendall(f'GET {path} HTTP/1.1\r\nHost: x\r\n\r\n'.encode())
    return s


def read_all(s, rate=None):
    """Reads s to its end, at rate bytes a second if given; returns the bytes."""
    data, start = b'', time.monotonic()
    s.settimeout(40)
    while True:
        if rate:
            ahead = len(data) / rate - (time.monotonic() - start)
            if ahead > 0:
                time.sleep(ahead)
        try:
            chunk = s.recv(8192)
        except OSError:
            return data
        if not chunk:
            return data
        data += chunk


def timed_get(port, path):
    """Reads a GET's whole reply; returns (body, the most bytes seen in any 100 ms and any 20 ms)."""
    s = open_get(port, path)
    s.settimeout(40)
    arrivals, data = [], b''
    with s:
        while True:
            try:
                chunk = s.recv(4096)
            except OSError:
                break
            if not chunk:
                break
            arrivals.append((time.monotonic(), len(chunk)))
            data += chunk

    def most(window):
        best = total = first = 0
        for last in range(len(arrivals)):
            total += arrivals[last][1]
            while arrivals[last][0] - arrivals[first][0] >= window:
                total -= arrivals[first][1]
                first += 1
            best = max(best, total)
        return best
    return data.split(b'\r\n\r\n', 1)[-1], most(0.1), most(0.02)


def closed_within(s, seconds):
    """True if the server closes s (EOF or reset) within seconds."""
    s.settimeout(seconds)
    try:
        while s.recv(65536):
            pass
        return True
    except socket.timeout:
        return False
    except OSError:
        return True


def server_id(port):
    return int(re.search(r'"sv_serverid" is: ?"(-?\d+)', smoke_test.rcon(port, RCON, 'sv_serverid')).group(1))


def check_http(port, sid, data, check):
    status, headers, body = get(port, '/' + MOD)
    check('http get', status == 200 and headers.get('Content-Length') == str(len(data))
          and headers.get('Connection') == 'close' and body == data, f'{status} {headers} {len(body or b"")}')
    status, headers, body = get(port, '/' + MOD, 'HEAD')
    check('http head', status == 200 and headers.get('Content-Length') == str(len(data)) and body == b'',
          f'{status} {headers} {len(body or b"")}')
    for path in ('/main/zz_svr_www.iwd', '/main/iw_00.iwd'):
        status = get(port, path)[0]
        check('no grant ' + path, status == 404, str(status))
    # an IP with no grant at all is closed at accept, and holds no slot
    start = time.monotonic()
    reply = http(port, b'GET /' + MOD.encode() + b' HTTP/1.1\r\n\r\n', source='127.0.0.2', timeout=3)
    took = time.monotonic() - start
    check('no grant other ip', reply == b'' and took < 0.5, f'{reply!r:.40} {took:.2f} s')
    others = [socket.create_connection(('127.0.0.1', port), 5, source_address=('127.0.0.2', 0)) for _ in range(2)]
    status, _, body = get(port, '/' + MOD)
    closed = [closed_within(o, 0.5) for o in others]
    for o in others:
        o.close()
    check('no grant other ip holds no slot', status == 200 and body == data and all(closed), f'{status} {closed}')
    for path in ('/main//zz_www_plus.iwd', '/main/%2e%2e/main/zz_www_plus.iwd', '/main/zz_www_plus.iwd?x',
                 '/../main/zz_www_plus.iwd', '//main/zz_www_plus.iwd', '/main/zz_www_plus.iwd%00',
                 '/main/zz_www_plus.iwd#', '/main/zz_www_plus.iwd%'):
        status = get(port, path)[0]
        check('paths ' + path, status == 404, str(status))
    status, _, body = get(port, '/main/zz_www%5Fplus.iwd')
    check('paths percent-decoded', status == 200 and body == data, str(status))
    status = get(port, '/' + MOD, 'POST')[0]
    check('method POST', status == 405, str(status))
    reply = http(port, b'GET /' + MOD.encode() + b' HTTP/1.1\r\n' + b'X-Pad: ' + b'a' * 5000 + b'\r\n\r\n')
    check('head over 4 KB', reply == b'', repr((reply or b'')[:40]))

    start = time.monotonic()
    s = socket.create_connection(('127.0.0.1', port), 5)
    closed = closed_within(s, 15)
    took = time.monotonic() - start
    s.close()
    check('slow client', closed and 9 <= took <= 12, f'{took:.1f} s')
    start = time.monotonic()
    s = socket.create_connection(('127.0.0.1', port), 5)
    closed = False
    try:
        while not closed and time.monotonic() - start < 15:
            s.send(b'G')
            closed = closed_within(s, 1)
    except OSError:
        closed = True
    took = time.monotonic() - start
    s.close()
    check('one byte a second', closed and 9 <= took <= 12, f'{took:.1f} s')

    # the connection cap with room per IP, then the per-IP cap with room in all
    for name, settings in (('connection cap', ('sv_wwwMaxConnections 2', 'sv_wwwMaxPerIP 8')),
                           ('per ip cap', ('sv_wwwMaxConnections 4', 'sv_wwwMaxPerIP 2'))):
        for setting in settings:
            smoke_test.rcon(port, RCON, 'set ' + setting)
        time.sleep(0.3)
        slow = [open_get(port, '/' + MOD) for _ in range(2)]
        time.sleep(0.3)
        third = socket.create_connection(('127.0.0.1', port), 5)
        start = time.monotonic()
        closed = closed_within(third, 3)
        took = time.monotonic() - start
        third.close()
        for s in slow:
            s.close()
        check(name, closed and took < 1, f'{took:.1f} s')
    time.sleep(0.5)

    smoke_test.rcon(port, RCON, 'set sv_wwwMaxRate 256')
    time.sleep(0.5)
    start = time.monotonic()
    body, per100, per20 = timed_get(port, '/' + MOD)
    took = time.monotonic() - start
    check('rate cap', body == data and 3.5 <= took <= 5, f'{took:.1f} s')
    # no bursts ahead of the game's packets: 2x the rate in any 100 ms, 5x in any 20 ms
    check('rate cap smooth', per100 <= 2 * 256 * 1024 / 10 and per20 <= 5 * 256 * 1024 / 50,
          f'{per100} bytes in 100 ms, {per20} in 20 ms')
    smoke_test.rcon(port, RCON, 'set sv_wwwMaxRate 1024')
    time.sleep(0.3)

    s = open_get(port, '/' + MOD)
    got = []
    reader = threading.Thread(target=lambda: got.append(read_all(s, 64 * 1024)))
    reader.start()
    time.sleep(2)
    smoke_test.rcon(port, RCON, 'map_restart')
    smoke_test.wait_for(lambda: smoke_test.query(port, 'getinfo x'), 60)
    smoke_test.rcon(port, RCON, 'map mp_toujane')
    smoke_test.wait_for(lambda: smoke_test.query(port, 'getinfo x'), 60)
    reader.join(60)
    s.close()
    body = got[0].split(b'\r\n\r\n', 1)[-1] if got else b''
    check('map change transfer', body == data, f'{len(body)} of {len(data)} bytes')
    sid = server_id(port)
    reply, red = ask(port, sid, MOD)
    status, _, body = get(port, '/' + MOD)
    check('map change new get', len(red) == 1 and status == 200 and body == data, f'{red} {status}')


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
        data = open(os.path.join(home, MOD), 'rb').read()
        command = [os.path.abspath(args.binary), '+set', 'fs_basepath', os.path.abspath(args.game_dir),
                   '+set', 'fs_homepath', home, '+set', 'net_ip', '127.0.0.1', '+set', 'net_port', str(port), '+set', 'sv_cracked', '1',
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
                sid = server_id(port)
                reply, red = ask(port, sid, MOD)
                check('plus redirect', red == [{'url': 'plus:' + MOD, 'flags': 0, 'size': size}] and b'PK' not in reply, str(red))
                red, reply = fail_then_udp(port, sid, MOD)
                check('fail without ack falls back to udp', len(red) == 1 and b'PK\x03\x04' in reply
                      and b'UNEXPECTEDDOWLOADMESSAGE' not in open(log_path, 'rb').read(), f'{red} {len(reply)} bytes')
                for name in ('main/zz_svr_www.iwd', 'main/iw_00.iwd'):
                    reply, red = ask(port, sid, name)
                    check('svr refused ' + name, REFUSED in reply and not red, str(red))
                # no scheme: the console reads // as a comment, even in quotes
                smoke_test.rcon(port, RCON, 'set sv_wwwBaseURL "example.invalid/dl"')
                reply, red = ask(port, sid, MOD)
                check('real url kept', [r['url'] for r in red] == ['example.invalid/dl/' + MOD], str(red))
                smoke_test.rcon(port, RCON, 'set sv_wwwBaseURL auto')
                smoke_test.rcon(port, RCON, 'set sv_wwwDlDisconnected 1')
                reply, red = ask(port, sid, MOD)
                check('disconnected flag', [r['flags'] for r in red] == [1], str(red))
                smoke_test.rcon(port, RCON, 'set sv_wwwDlDisconnected 0')
                check_http(port, sid, data, check)
            check('the server still runs', server.poll() is None, f'exit code {server.poll()}')
            if up:
                logged = re.findall(r'www: 127\.0\.0\.1 main/zz_www_plus\.iwd \d+ bytes in [\d.]+ s', open(log_path, encoding='latin-1').read())
                check('download logged', len(logged) >= 4, str(len(logged)))
                # quit joins the worker, with a transfer open
                stuck = open_get(port, '/' + MOD)
                smoke_test.rcon(port, RCON, 'quit')
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pass
                stuck.close()
                check('quit with a transfer open', server.poll() is not None, f'exit code {server.poll()}')
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

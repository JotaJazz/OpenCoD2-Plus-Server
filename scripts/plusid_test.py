#!/usr/bin/env python3
"""Checks the Plus ID: the connect key pair proof (docs/architecture/plus-id.md).

    python3 scripts/plusid_test.py /path/to/CoD2 [--binary bin/cod2rev_lnxded] [--protocol 118]

Minimal clients sign the connect challenge with keys made by the openssl CLI
and the server's verdict is read back with rcon plusIdStatus. The folder must
hold only the stock iwds. Exits with 0 when every check passes. The helpers
(make_key, sign, connect_with_id...) are for the other Plus ID tests.
"""
import argparse, base64, hashlib, os, re, secrets, subprocess, sys, tempfile, zipfile

import cod2client, smoke_test

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RCON = 'plusid_rcon'
# the P-256 group order: a private key is 1..N-1
N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
NOTICE = 'This server requires a Plus ID'
GAMETYPE = r"""main()
{
	maps\mp\gametypes\tdm::main();
	level.plusidConnect = level.callbackPlayerConnect;
	level.callbackPlayerConnect = ::connected;
}

connected()
{
	logPrint("plusid " + self getPlusId() + "\n");
	self [[level.plusidConnect]]();
}
"""


def make_key():
    """A random private key, 32 bytes big-endian."""
    while True:
        d = int.from_bytes(secrets.token_bytes(32), 'big')
        if 0 < d < N:
            return d.to_bytes(32, 'big')


def _der_key(priv):
    """priv as an SEC1 ECPrivateKey on prime256v1, which openssl reads."""
    return bytes.fromhex('30310201010420') + priv + bytes.fromhex('a00a06082a8648ce3d030107')


def _openssl(args, priv, data=b''):
    with tempfile.TemporaryDirectory(prefix='plusid_key_') as tmp:
        key = os.path.join(tmp, 'key.der')
        with open(key, 'wb') as f:
            f.write(_der_key(priv))
        return subprocess.run(['openssl'] + args + [key], input=data, capture_output=True, check=True).stdout


def public_key(priv):
    """The compressed public point, 33 bytes."""
    spki = _openssl(['pkey', '-inform', 'DER', '-pubout', '-outform', 'DER', '-ec_conv_form', 'compressed', '-in'], priv)
    return spki[-33:]


def plus_id(pk):
    """P- and the base32 of the first 10 bytes of SHA-256(pk), in groups of 4."""
    b = base64.b32encode(hashlib.sha256(pk).digest()[:10]).decode()
    return 'P-' + '-'.join(b[i:i + 4] for i in range(0, 16, 4))


def signed_text(challenge, adr):
    return f'cod2plus-id-v1|{challenge}|{adr}'.encode()


def _der_int(der, i):
    assert der[i] == 2
    n = der[i + 1]
    return int.from_bytes(der[i + 2:i + 2 + n], 'big'), i + 2 + n


def sign(priv, challenge, adr):
    """(pk hex, ps hex): the public key and the raw r||s signature of the signed text."""
    der = _openssl(['dgst', '-sha256', '-keyform', 'DER', '-sign'], priv, signed_text(challenge, adr))
    # SEQUENCE { INTEGER r, INTEGER s }, short lengths for P-256
    r, i = _der_int(der, 2)
    s, _ = _der_int(der, i)
    return public_key(priv).hex(), (r.to_bytes(32, 'big') + s.to_bytes(32, 'big')).hex()


def _private(ip):
    """PlusId_IsPrivate: RFC 1918, loopback and link-local only (not the host's
    own /24, which Sys_IsLANAddress also takes)."""
    a = [int(x) for x in ip.split('.')]
    return (a[0] in (10, 127) or a[:2] in ([169, 254], [192, 168])
            or (a[0] == 172 and a[1] & 0xF0 == 16))


def address_accepted(signed_ip, from_ip, public, net_ip='', signed_port=28960, net_port=28960):
    """The server's rule (PlusId_AddressAccepted) for the address the client
    signed, branch for branch: the server's port; a private address only from
    a private source, even when it is net_ip; then the public address or net_ip;
    then any private address."""
    if signed_port != net_port:
        return False
    if _private(signed_ip) and not _private(from_ip):
        return False
    if signed_ip in (public, net_ip) and signed_ip not in ('', '0.0.0.0'):
        return True
    return _private(signed_ip)


def id_keys(pk_hex, ps_hex, adr):
    return f'\\pk\\{pk_hex}\\ps\\{ps_hex}\\pa\\{adr}'


def connect_with_id(port, priv, adr=None, name='plusid', protocol=115, plus=123):
    """Connects a client that signs adr (by default 127.0.0.1:port) with priv;
    returns (client, None or the server's reply). The caller closes the client."""
    adr = adr or f'127.0.0.1:{port}'
    client = cod2client.Client(port)
    reply = client.connect(protocol, name, plus, lambda challenge: id_keys(*sign(priv, challenge, adr), adr))
    return client, reply


def status(port):
    """{name: id} from rcon plusIdStatus, whose lines are "num name id"."""
    lines = smoke_test.rcon(port, RCON, 'plusIdStatus').splitlines()
    return {m.group(1): m.group(2) for m in (re.match(r'\s*\d+ (.*) (\S+)$', l) for l in lines[1:]) if m}


def check_address_rule(check):
    # (signed, from, sv_publicAddress, net_ip, signed port, expected)
    table = [('10.0.0.5', '203.0.113.9', '203.0.113.7', '', 28960, False),  # relay from a public address
             ('10.0.0.5', '192.168.1.2', '', '', 28960, True),
             ('127.0.0.1', '127.0.0.1', '', '', 28960, True),
             ('203.0.113.7', '198.51.100.1', '203.0.113.7', '', 28960, True),
             ('203.0.113.7', '198.51.100.1', '', '203.0.113.7', 28960, True),
             ('203.0.113.8', '198.51.100.1', '203.0.113.7', '', 28960, False),
             ('203.0.113.8', '127.0.0.1', '203.0.113.7', '', 28960, False),
             ('203.0.113.7', '198.51.100.1', '203.0.113.7', '', 28961, False),  # another port
             # private net_ip relayed from a public address
             ('192.168.1.5', '198.51.100.1', '', '192.168.1.5', 28960, False),
             # a public neighbour in the server's /24 (a shared VPN) relaying its own signed IP
             ('203.0.113.50', '203.0.113.50', '', '203.0.113.7', 28960, False),
             ('26.10.0.9', '26.10.0.20', '', '26.10.0.5', 28960, False)]
    bad = [row for row in table if address_accepted(*row[:4], signed_port=row[4]) != row[5]]
    check('address_rule', not bad, str(bad))


def run_cases(port, protocol, log_path, game_log, check):
    clients = []

    def join(name, priv=None, adr=None, extra=None):
        if priv:
            client, reply = connect_with_id(port, priv, adr, name, protocol)
        else:
            client = cod2client.Client(port)
            reply = client.connect(protocol, name, 123, extra)
        clients.append(client)
        return reply

    try:
        priv = make_key()
        want = plus_id(public_key(priv))
        reply = join('valid', priv)
        got = status(port).get('valid')
        check('valid_id', reply is None and got == want, f'{reply} {got} {want}')
        smoke_test.wait_for(lambda: any(l == 'plusid ' + want for l in smoke_test.log_lines(game_log)))
        check('getplusid', 'plusid ' + want in smoke_test.log_lines(game_log))

        reply = join('noid')
        check('no_id', reply is None and status(port).get('noid') == '-', f'{reply} {status(port)}')

        def tampered(challenge):
            adr = f'127.0.0.1:{port}'
            pk, ps = sign(make_key(), challenge, adr)
            return id_keys(pk, ps[:-1] + '%x' % (int(ps[-1], 16) ^ 1), adr)
        reply = join('badsig', extra=tampered)
        logged = 'plusid: invalid signature' in open(log_path, encoding='latin-1').read()
        check('bad_signature', reply is None and status(port).get('badsig') == '-' and logged, f'{reply} {logged}')

        dump = smoke_test.rcon(port, RCON, 'dumpuser valid')
        check('stripped', re.search(r'^name +valid$', dump, re.M) and not re.search(r'^(pk|ps|pa) ', dump, re.M), dump[-300:])

        smoke_test.rcon(port, RCON, f'set sv_publicAddress 203.0.113.7:{port}')
        # both private: accepted; the real relay (from a public address) is in address_rule
        priv = make_key()
        reply = join('relay', priv, f'10.9.9.9:{port}')
        check('relay', reply is None and status(port).get('relay') == plus_id(public_key(priv)), f'{reply} {status(port)}')

        # the new sv_publicAddress is resolved on the first connect after it changed
        priv = make_key()
        reply = join('public', priv, f'203.0.113.7:{port}')
        check('public_match', reply is None and status(port).get('public') == plus_id(public_key(priv)), f'{reply} {status(port)}')

        reply = join('mismatch', make_key(), f'203.0.113.8:{port}')
        logged = f'signed for another address, 203.0.113.8:{port}' in open(log_path, encoding='latin-1').read()
        check('public_mismatch', reply is None and status(port).get('mismatch') == '-' and logged,
              f'{reply} {logged} {status(port)}')
        smoke_test.rcon(port, RCON, 'set sv_publicAddress ""')

        smoke_test.rcon(port, RCON, 'set sv_requirePlusId 1')
        reply = join('required')
        check('require', reply is not None and reply.startswith('error') and NOTICE in reply, str(reply))
        reply = join('requiredok', make_key())
        check('require with id', reply is None, str(reply))
        smoke_test.rcon(port, RCON, 'set sv_requirePlusId 0')
    finally:
        for client in clients:
            client.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('game_dir')
    ap.add_argument('--binary', default=os.path.join(ROOT, 'bin', 'cod2rev_lnxded'))
    ap.add_argument('--protocol', type=int, default=115)
    ap.add_argument('--map', default='mp_toujane')
    args = ap.parse_args()
    port = smoke_test.free_port()
    failures = []

    def check(name, ok, detail=''):
        print(f'{"ok  " if ok else "FAIL"} {name}' + (f' ({detail})' if detail else ''), flush=True)
        if not ok:
            failures.append(name)

    check_address_rule(check)
    with tempfile.TemporaryDirectory(prefix='cod2_plusid_') as home:
        os.makedirs(os.path.join(home, 'main'))
        with zipfile.ZipFile(os.path.join(home, 'main', 'zz_svr_plusid.iwd'), 'w') as z:
            z.writestr('maps/mp/gametypes/plusid.gsc', GAMETYPE)
        command = [os.path.abspath(args.binary), '+set', 'fs_basepath', os.path.abspath(args.game_dir),
                   '+set', 'fs_homepath', home, '+set', 'net_port', str(port), '+set', 'sv_cracked', '1',
                   '+set', 'rcon_password', RCON, '+set', 'dedicated', '1', '+set', 'sv_maxclients', '16',
                   '+set', 'g_gametype', 'plusid', '+set', 'g_log', 'games_mp.log', '+set', 'g_logSync', '1',
                   '+map', args.map]
        log_path = os.path.join(home, 'out.log')
        with open(log_path, 'wb') as log:
            server = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, cwd=home)
        try:
            smoke_test.wait_for(lambda: server.poll() is not None or smoke_test.query(port, 'getinfo x'), 150)
            up = server.poll() is None and smoke_test.query(port, 'getinfo x') is not None
            check('the server runs the map', up)
            if up:
                check('lan warning', 'plusid: no sv_publicAddress, only LAN players get a Plus ID'
                      in open(log_path, encoding='latin-1').read())
                run_cases(port, args.protocol, log_path, os.path.join(home, 'main', 'games_mp.log'), check)
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

import socket
import time
import argparse
import statistics

# Karena masih 1 device/laptop
PROXY_HOST = '192.168.18.101'
PROXY_PORT = 8080

SERVER_HOST = '192.168.18.96'
SERVER_UDP_PORT = 8001


# =========================
# MODE TCP (HTTP CLIENT)
# =========================
def http_get(path='/index.html'):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        s.connect((PROXY_HOST, PROXY_PORT))

        # WAJIB pakai \r\n
        req = (
            f'GET {path} HTTP/1.1\r\n'
            f'Host: {PROXY_HOST}:{PROXY_PORT}\r\n'
            f'Connection: close\r\n'
            f'\r\n'
        )

        s.sendall(req.encode())

        resp = b''

        while True:
            chunk = s.recv(65536)

            if not chunk:
                break

            resp += chunk

        s.close()

        if b'\r\n\r\n' in resp:
            header, body = resp.split(b'\r\n\r\n', 1)

            print('=' * 60)
            print('HEADER:')
            print(header.decode(errors='ignore'))

            print('-' * 60)

            print(f'BODY ({len(body)} bytes, preview 300 karakter):')

            print(body.decode(errors='ignore')[:300])

            print('=' * 60)

        else:
            print(resp.decode(errors='ignore'))

    except ConnectionRefusedError:
        print(f'[ERROR] Proxy {PROXY_HOST}:{PROXY_PORT} tidak bisa dihubungi.')
        print('Pastikan proxy.py sudah berjalan!')


# =========================
# MODE UDP (QoS PINGER)
# =========================
def udp_ping(count=10):

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    s.settimeout(1)

    rtts = []

    sent = 0
    received = 0

    print(f'\nQoS Ping ke {SERVER_HOST}:{SERVER_UDP_PORT} — {count} paket')

    print('-' * 50)

    for seq in range(1, count + 1):

        payload = f'Ping {seq} {time.time()}'

        try:
            t_send = time.time()

            s.sendto(payload.encode(), (SERVER_HOST, SERVER_UDP_PORT))

            sent += 1

            s.recvfrom(1024)

            rtt = (time.time() - t_send) * 1000

            rtts.append(rtt)

            received += 1

            print(f'  Paket {seq:2d}: RTT = {rtt:.2f} ms')

        except socket.timeout:

            sent += 1

            print(f'  Paket {seq:2d}: Request timed out')

        time.sleep(0.2)

    s.close()

    # =========================
    # Statistik QoS
    # =========================

    loss = ((sent - received) / sent * 100) if sent else 0

    rmin = min(rtts) if rtts else 0
    ravg = sum(rtts) / len(rtts) if rtts else 0
    rmax = max(rtts) if rtts else 0

    diffs = [
        abs(rtts[i] - rtts[i - 1])
        for i in range(1, len(rtts))
    ]

    jitter = statistics.stdev(diffs) if len(diffs) > 1 else 0

    total_bytes = received * len(payload.encode())

    duration = count * 1.2

    throughput = (total_bytes * 8) / (duration * 1000)

    print('\n' + '=' * 50)

    print('STATISTIK QoS:')

    print(f'  Dikirim/Diterima : {sent}/{received}')

    print(f'  Packet Loss      : {loss:.1f}%')

    print(f'  RTT Min/Avg/Max  : {rmin:.2f}/{ravg:.2f}/{rmax:.2f} ms')

    print(f'  Jitter           : {jitter:.2f} ms')

    print(f'  Throughput       : {throughput:.2f} kbps')

    print('=' * 50)


# =========================
# MAIN
# =========================
def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--mode',
        choices=['tcp', 'udp'],
        required=True
    )

    parser.add_argument(
        '--path',
        default='/index.html'
    )

    parser.add_argument(
        '--count',
        type=int,
        default=10
    )

    args = parser.parse_args()

    if args.mode == 'tcp':
        http_get(args.path)

    else:
        udp_ping(args.count)


if __name__ == '__main__':
    main()
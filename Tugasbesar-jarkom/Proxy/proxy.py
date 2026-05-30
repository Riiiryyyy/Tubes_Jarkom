import socket, threading, os
from datetime import datetime

HOST        = '0.0.0.0'
PROXY_PORT  = 8080
SERVER_HOST = '192.168.18.96'  # ← ganti IP Laptop A (atau 127.0.0.1 jika 1 device)
SERVER_PORT = 8000
CACHE_DIR   = './cache/'

os.makedirs(CACHE_DIR, exist_ok=True)
cache_lock = threading.Lock()

def path_to_cache_file(path):
    safe = path.replace('/', '_').replace('..','').strip('_') or 'root'
    return os.path.join(CACHE_DIR, safe)

def forward_to_server(raw_request):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect((SERVER_HOST, SERVER_PORT))
        if not raw_request.endswith('\r\n\r\n'):
            raw_request = raw_request.rstrip() + '\r\n\r\n'
        s.sendall(raw_request.encode())
        resp = b''
        while True:
            chunk = s.recv(65536)  # buffer besar untuk file besar (video)
            if not chunk: break
            resp += chunk
        s.close()
        return resp if resp else None
    except socket.timeout:
        return None  # akan jadi 504
    except ConnectionRefusedError:
        return False  # akan jadi 502
    except Exception as e:
        print(f'[forward ERROR] {e}')
        return False

def handle_client(conn, addr):
    t0 = datetime.now()
    try:
        raw = conn.recv(4096).decode('utf-8', errors='ignore')
        if not raw: return
        first = raw.split('\r\n')[0].split(' ')
        path  = first[1].split('?')[0] if len(first)>=2 else '/'
        cache_file = path_to_cache_file(path)
        ms = lambda: f'{(datetime.now()-t0).total_seconds()*1000:.1f}ms'
        if os.path.exists(cache_file):
            # CACHE HIT
            with cache_lock:
                with open(cache_file,'rb') as f: resp = f.read()
            conn.sendall(resp)
            print(f'[HIT ] {addr[0]} | {path} | {ms()}')
        else:
            # CACHE MISS — forward ke server
            result = forward_to_server(raw)
            if result is None:
                # 504 Gateway Timeout — kirim file 504 jika ada, atau plain text
                body = b'<h1>504 Gateway Timeout</h1>'
                resp = b'HTTP/1.1 504 Gateway Timeout\r\nContent-Length: '+str(len(body)).encode()+b'\r\n\r\n'+body
                conn.sendall(resp)
                print(f'[504 ] {addr[0]} | {path}')
            elif result is False:
                body = b'<h1>502 Bad Gateway</h1>'
                resp = b'HTTP/1.1 502 Bad Gateway\r\nContent-Length: '+str(len(body)).encode()+b'\r\n\r\n'+body
                conn.sendall(resp)
                print(f'[502 ] {addr[0]} | {path}')
            else:
                # Simpan ke cache hanya jika response 200
                if result.startswith(b'HTTP/1.1 200'):
                    with cache_lock:
                        with open(cache_file,'wb') as f: f.write(result)
                conn.sendall(result)
                print(f'[MISS] {addr[0]} | {path} | {ms()} (dari server)')
    except Exception as e:
        print(f'[ERROR] handle_client proxy: {e}')
    finally:
        conn.close()

def start_proxy():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PROXY_PORT)); s.listen(20)
    print(f'[PROXY] Listening di port {PROXY_PORT} → forward ke {SERVER_HOST}:{SERVER_PORT}')
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn,addr), daemon=True).start()

if __name__ == '__main__':
    start_proxy()

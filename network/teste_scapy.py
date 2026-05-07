import netifaces
import socket
import ipaddress
import subprocess
from scapy.all import IP, TCP, sr
from concurrent.futures import ThreadPoolExecutor, as_completed

redes = []

# Descobre interfaces de rede
for iface in netifaces.interfaces():
    addrs = netifaces.ifaddresses(iface)
    if netifaces.AF_INET in addrs:
        for ip_info in addrs[netifaces.AF_INET]:
            ip = ip_info['addr']
            netmask = ip_info['netmask']
            network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
            print(f"Interface: {iface}")
            print(f"IP local: {ip}")
            print(f"Máscara: {netmask}")
            print(f"Range da rede: {network}")

            tabela = {"interface": iface, "ip": ip, "mascara": netmask, "range": str(network)}
            if tabela not in redes:
                redes.append(tabela)
            print()

REDES_PRIVADAS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
]

def eh_rede_local(ip: str) -> bool:
    endereco = ipaddress.ip_address(ip)
    return any(endereco in rede for rede in REDES_PRIVADAS)

ranges_locais = [rede["range"] for rede in redes if eh_rede_local(rede["ip"])]
target_network = ipaddress.IPv4Network(ranges_locais[0], strict=False)

# Função de ping otimizada
def ping_host(ip):
    try:
        subprocess.check_output(["ping", "-c", "1", "-W", "1", str(ip)], stderr=subprocess.DEVNULL)
        return ip
    except subprocess.CalledProcessError:
        return None

# --- Passo 1: Ping em paralelo ---
icmp_hosts = []
print("Verificando resposta ICMP (ping)...")

with ThreadPoolExecutor(max_workers=50) as executor:  # ajusta max_workers conforme sua máquina
    futures = {executor.submit(ping_host, str(ip)): ip for ip in target_network.hosts()}
    for future in as_completed(futures):
        result = future.result()
        if result:
            icmp_hosts.append(result)
            print(f"{result} respondeu ao ping")

def testar_rtsp_describe(ip, port=554):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((ip, port))

        rtsp_request = (
            f"DESCRIBE rtsp://{ip}:{port}/ RTSP/1.0\r\n"
            f"CSeq: 1\r\n"
            f"Accept: application/sdp\r\n\r\n"
        )
        s.send(rtsp_request.encode())
        resposta = s.recv(4096).decode(errors="ignore")
        s.close()

        # Mostra toda a resposta recebida
        print(f"\n--- Resposta RTSP de {ip}:{port} ---")
        print(resposta)
        print("-----------------------------------\n")

        if "RTSP/1.0 200 OK" in resposta and "application/sdp" in resposta:
            print(f"[+] {ip}:{port} respondeu DESCRIBE válido (possível câmera IP)")
            return "camera"
        elif "RTSP/1.0 401 Unauthorized" in resposta:
            print(f"[?] {ip}:{port} exige autenticação RTSP")
            # Analisa o cabeçalho WWW-Authenticate
            if "DVR" in resposta or "NVR" in resposta:
                print(f"[!] {ip}:{port} parece ser um DVR/NVR")
                return "dvr"
            elif "Camera" in resposta or "IP Camera" in resposta:
                print(f"[+] {ip}:{port} parece ser uma câmera IP protegida por senha")
                return "camera"
            else:
                print(f"[?] {ip}:{port} dispositivo RTSP protegido (não identificado)")
                return "unknown"
        else:
            print(f"[-] {ip}:{port} não retornou DESCRIBE válido")
            return "invalid"

    except Exception as e:
        print(f"[!] Erro ao conectar {ip}:{port} -> {e}")
        return "error"


# --- Passo 2: TCP SYN scan em múltiplas portas RTSP ---
rtsp_ports = [554, 8554, 10554]

print("\nVerificando portas RTSP...")
for ip in icmp_hosts:
    for port in rtsp_ports:
        pkt = IP(dst=ip)/TCP(dport=port, flags="S")
        ans, unans = sr(pkt, timeout=1, retry=0, verbose=0)  # timeout menor
        for sent, received in ans:
            if received.haslayer(TCP) and received[TCP].flags == "SA":
                resultado = testar_rtsp_describe(received[IP].src, port)
                if resultado == "camera":
                    print(f"Confirmado: {received[IP].src} é uma câmera IP")
                elif resultado == "dvr":
                    print(f"Confirmado: {received[IP].src} é um DVR/NVR")


                
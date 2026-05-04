import netifaces
import ipaddress
from scapy.all import IP, TCP, sr

redes = []

# Descobre interfaces de rede
for iface in netifaces.interfaces():
    addrs = netifaces.ifaddresses(iface)
    if netifaces.AF_INET in addrs:
        for ip_info in addrs[netifaces.AF_INET]:
            ip = ip_info['addr']
            netmask = ip_info['netmask']
            
            # Calcula o range da rede
            network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
            print(f"Interface: {iface}")
            print(f"IP local: {ip}")
            print(f"Máscara: {netmask}")
            print(f"Range da rede: {network}")

            # Criar um novo dicionário a cada iteração
            tabela = {
                "interface": iface,
                "ip": ip,
                "mascara": netmask,
                "range": str(network)
            }

            # Evita duplicados
            if tabela not in redes:
                redes.append(tabela)

            print()

# Faixas privadas definidas pela RFC 1918
REDES_PRIVADAS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
]

def eh_rede_local(ip: str) -> bool:
    """Verifica se um IP pertence a uma faixa de rede privada (RFC 1918)."""
    endereco = ipaddress.ip_address(ip)
    return any(endereco in rede for rede in REDES_PRIVADAS)

# Filtra e coleta os ranges das redes locais
ranges_locais = [
    rede["range"]
    for rede in redes
    if eh_rede_local(rede["ip"])
]

import subprocess

# Range da sub-rede desejada
target_network = ipaddress.IPv4Network(ranges_locais[0], strict=False)

# Função de ping nativo
def ping_host(ip):
    try:
        subprocess.check_output(["ping", "-c", "1", "-W", "1", str(ip)], stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

# --- Passo 1: Ping em todos os IPs do range ---
icmp_hosts = []
print("Verificando resposta ICMP (ping)...")
for ip in target_network.hosts():  # percorre todos os IPs válidos
    if ping_host(ip):
        icmp_hosts.append(str(ip))
        print(f"{ip} respondeu ao ping")

# --- Passo 2: TCP SYN scan em múltiplas portas RTSP ---
rtsp_ports = [554, 8554, 10554]

print("\nVerificando portas RTSP...")
for ip in icmp_hosts:
    for port in rtsp_ports:
        pkt = IP(dst=ip)/TCP(dport=port, flags="S")
        ans, unans = sr(pkt, timeout=2, retry=0, verbose=0)
        for sent, received in ans:
            if received.haslayer(TCP) and received[TCP].flags == "SA":
                print(f"Possível câmera RTSP encontrada: {received[IP].src} na porta {port}")
                

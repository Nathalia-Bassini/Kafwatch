import netifaces
import ipaddress
from scapy.all import IP, TCP, sr

# Descobre interfaces de rede
for iface in netifaces.interfaces():
    addrs = netifaces.ifaddresses(iface)
    if netifaces.AF_INET in addrs:
        ip_info = addrs[netifaces.AF_INET][0]
        ip = ip_info['addr']
        netmask = ip_info['netmask']
        
        # Calcula o range da rede
        network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
        print(f"Interface: {iface}")
        print(f"IP local: {ip}")
        print(f"Máscara: {netmask}")
        print(f"Range da rede: {network}")

        #Descobrindo se a rede printada é uma local ou é internet

    print()

import subprocess

# Range da sub-rede desejada
target_network = ipaddress.IPv4Network("10.145.80.0/22", strict=False)

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
                

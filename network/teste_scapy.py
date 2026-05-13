import netifaces
import socket
import ipaddress
import subprocess
from scapy.all import IP, TCP, sr, ARP, Ether, srp
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import time

# --- Função auxiliar para resolver ARP ---
def resolver_arp(ip, iface):
    arp_req = ARP(pdst=ip)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    ans, _ = srp(ether/arp_req, timeout=2, iface=iface, verbose=0)
    if ans:
        return ans[0][1].hwsrc  # MAC do destino
    return None

# Descobre interfaces de rede
def obter_redes():
    redes = []
    for iface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(iface)
        if netifaces.AF_INET in addrs:

            for ip_info in addrs[netifaces.AF_INET]:
                ip = ip_info['addr']
                netmask = ip_info['netmask']
                network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)

                tabela = {"interface": iface, "ip": ip, "mascara": netmask, "range": str(network)}
                if tabela not in redes:
                    redes.append(tabela)
    return redes

# - descobrir qual dos renges são de uma rede local (LAN) -

def eh_rede_local(ip: str) -> bool: # "-> bool" significa que o retorno vai ser booleano, e "ip: str" significa que só entram IPs salvos em formato string

    # intervalos padrão dos ranges das redes locais 
    REDES_PRIVADAS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ]

    endereco = ipaddress.ip_address(ip) 
    for rede in REDES_PRIVADAS:
        if endereco in rede:
            return True
    return False


# Função de ping otimizada
def ping_host(ip):
    try:
        subprocess.check_output(["ping", "-c", "1", "-W", "1", str(ip)], stderr=subprocess.DEVNULL)
        return ip
    except subprocess.CalledProcessError:
        return None

# --- Passo 1: Ping em paralelo ---
def ping_em_paralelo(redes):
    ranges_locais = []
    for rede in redes:
        ip_da_rede = rede["ip"]
        if eh_rede_local(ip_da_rede):
            range_da_rede = rede["range"]
            ranges_locais.append(range_da_rede)

    icmp_hosts = []
    for range_da_rede in ranges_locais:
        target_network = ipaddress.IPv4Network(range_da_rede, strict=False)

        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor: # max_workers(threads) conforme sua máquina
            futures = {}
            for ip in target_network.hosts():
                # cria uma tarefa (future) que vai rodar ping_host(ip) em paralelo
                future = executor.submit(ping_host, str(ip))
    
                # associa esse future ao IP correspondente
                futures[future] = ip

            for future in as_completed(futures):
                result = future.result()
                if result:
                    icmp_hosts.append(result)
    return icmp_hosts

    
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

        if "RTSP/1.0 200 OK" in resposta and "application/sdp" in resposta:
            return "camera"
        elif "RTSP/1.0 401 Unauthorized" in resposta:
            # Analisa o cabeçalho WWW-Authenticate
            if "DVR" in resposta or "NVR" in resposta:
                return "dvr"
            elif "Camera" in resposta or "IP Camera" in resposta:
                return "camera"
            else:
                return "unknown"
        else:
            return "invalid"

    except Exception as e:
        print(f"[!] Erro ao conectar {ip}:{port} -> {e}")
        return "error"


# --- Passo 2: TCP SYN scan em múltiplas portas RTSP ---
def scan_multiplas_portas(icmp_hosts, redes):
    rtsp_ports = [554, 8554, 10554]
    camera_result = []
    
    print("\nVerificando portas RTSP...")
    for ip in icmp_hosts:
        for port in rtsp_ports:
            pkt = IP(dst=ip)/TCP(dport=port, flags="S")

            iface = None
            for rede in redes:
                if ipaddress.ip_address(ip) in ipaddress.ip_network(rede["range"], strict=False):
                    iface = rede["interface"]
                    break
            ans, unans = sr(pkt, timeout=1, retry=0, verbose=0, iface=iface)

            for sent, received in ans:
                if received.haslayer(TCP) and received[TCP].flags == "SA":
                    resultado = testar_rtsp_describe(received[IP].src, port)
                    if resultado == "camera":
                        camera_result.append(ip)
    return camera_result


def main():
    start_time = time.time()
    
    lista_de_redes = obter_redes() #redes em que a máquina está conectada
    lista_de_respondedores = ping_em_paralelo(lista_de_redes) #responderam ao broadcast
    """
    lista_de_redes é o parâmetro de entrada, ou seja, a função ping_em_paralelo
    utiliza o que há dentro dela como se fosse o parametro local "redes", quando "redes" é
    utilizada dentro de ping_em_paralelo o valor que será utilizado agora será o de
    "lista_de_redes"

    """
    ip_camera = scan_multiplas_portas(lista_de_respondedores, lista_de_redes) #são cameras da rede local identificada

    final_time = time.time()
    print(f'{final_time - start_time}')
    print(f'{ip_camera}')

    return 0
if __name__ == "__main__":
    main()


                
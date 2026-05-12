import netifaces
import socket
import ipaddress
import subprocess
from scapy.all import IP, TCP, sr
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import time

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

                print(f"Interface: {iface}")
                print(f"IP local: {ip}")
                print(f"Máscara: {netmask}")
                print(f"Range da rede: {network}")

                tabela = {"interface": iface, "ip": ip, "mascara": netmask, "range": str(network)}
                if tabela not in redes:
                    redes.append(tabela)
                print()
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
    return any(endereco in rede for rede in REDES_PRIVADAS)

# Função de ping otimizada
def ping_host(ip):
    try:
        subprocess.check_output(["ping", "-c", "1", "-W", "1", str(ip)], stderr=subprocess.DEVNULL)
        return ip
    except subprocess.CalledProcessError:
        return None

# --- Passo 1: Ping em paralelo ---
def ping_em_paralelo(redes):
    ranges_locais = [rede["range"] for rede in redes if eh_rede_local(rede["ip"])]
    target_network = ipaddress.IPv4Network(ranges_locais[0], strict=False)

    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:  # max_workers(threads) conforme sua máquina
        print("Verificando resposta ICMP (ping)...")

        icmp_hosts = []
        futures = {executor.submit(ping_host, str(ip)): ip for ip in target_network.hosts()}
        for future in as_completed(futures):
            result = future.result()
            if result:
                icmp_hosts.append(result)
                print(f"{result} respondeu ao ping")
    return icmp_hosts

#
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
def scan_multiplas_portas(icmp_hosts):
    rtsp_ports = [554, 8554, 10554]
    camera_result = []
    
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
                        camera_result.append(ip)
                    elif resultado == "dvr":
                        print(f"Confirmado: {received[IP].src} é um DVR/NVR")
    return camera_result


def main():
    start_time = time.time()
    
    lista_de_redes = obter_redes() #redes em que a máquina está conectada
    lista_de_respondedores = ping_em_paralelo(lista_de_redes) #esponderam ao broadcast
    """
    lista_de_redes é o parâmetro de entrada, ou seja, a função ping_em_paralelo
    utiliza o que há dentro dela como se fosse o parametro local "redes", quando "redes" é
    utilizada dentro de ping_em_paralelo o valor que será utilizado agora será o de
    "lista_de_redes"

    """
    ip_camera = scan_multiplas_portas(lista_de_respondedores) #são cameras da rede local identificada

    print()
    print(f'{lista_de_redes}', end=" redes em que a máquina está conectada")
    print()
    print(f'{lista_de_respondedores}', end=" responderam ao broadcast")
    print()
    print(f'{ip_camera}', end=" são cameras da rede local identificada")
    print()

    final_time = time.time()
    print(f'{final_time - start_time}')

    return 0
if __name__ == "__main__":
    main()


                
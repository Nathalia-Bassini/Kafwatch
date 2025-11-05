import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

class NetworkScanner:
    def __init__(self, network_base, ip_range, port, timeout=0.1, max_workers=100):
        """
        Inicializa o scanner.
        
        Args:
            network_base (str): A base da rede (ex: "192.168.1").
            ip_range (iterable): Um range ou lista de IPs (ex: range(1, 255)).
            port (int): A porta a ser verificada.
            timeout (float): Timeout em segundos para cada tentativa de conexão.
            max_workers (int): Número máximo de threads paralelas.
        """
        self._network_base = network_base
        self._ip_range = ip_range
        self._port = port
        self._timeout = timeout
        # Ajustamos o número de workers para não ser maior que o número de IPs
        self._max_workers = min(max_workers, len(list(ip_range)))

    def _check_ip(self, ip):
        """
        Função "worker" que roda em cada thread.
        Tenta conectar a um único IP e porta. Retorna o IP se for bem-sucedido.
        """
        try:
            # socket.create_connection é a forma moderna e robusta de abrir um socket TCP
            with socket.create_connection((ip, self._port), timeout=self._timeout):
                # Se a linha acima funcionou, a porta está aberta.
                return ip
        except (socket.timeout, ConnectionRefusedError, OSError):
            # socket.timeout: O IP não respondeu a tempo.
            # ConnectionRefusedError: O IP respondeu, mas a porta está fechada.
            # OSError: Pode ocorrer para "No route to host" ou "Host is down".
            return None # Falha na conexão

    def discover(self, progress_callback=None):
        """
        Escaneia a rede em paralelo usando um pool de threads.
        Retorna uma lista de IPs de câmeras encontradas.
        """
        found_ips = []

        ips_to_check = []
        # Gera a lista completa de IPs a verificar
        for i in self._network_base:
            for j in self._ip_range:
                ips_to_check.append(f"{i}.{j}")

        # O ThreadPoolExecutor gerencia a criação e destruição das threads
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            
            # Submetemos todas as tarefas (uma para cada IP) ao pool.
            # Isso é não-bloqueante; as tarefas começam a rodar em background.
            # Usamos um dicionário para mapear o "Future" (tarefa) ao IP.
            future_to_ip = {executor.submit(self._check_ip, ip): ip for ip in ips_to_check}

            # as_completed() nos entrega os resultados assim que eles ficam prontos,
            # não na ordem em que foram submetidos. Isso é o ideal para performance.
            for future in as_completed(future_to_ip):
                result_ip = future.result() # Pega o resultado (será o IP ou None)
                
                if result_ip:
                    found_ips.append(result_ip)
                    if progress_callback:
                        progress_callback(result_ip) # Informa o progresso

        # É uma boa prática retornar a lista ordenada
        return sorted(found_ips)
    
if __name__ == "__main__":
    found_cameas = NetworkScanner(["10.145.80", "10.145.81", "10.145.82"], range(1, 255), 554, timeout=0.1)
    cameras = found_cameas.discover(progress_callback = lambda ip: print(f"Camera found at: {ip}"))
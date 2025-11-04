import yaml
import os
from urllib.parse import quote

class ComposeGenerator:
    def __init__(self, username, password):
        """
        Armazena as credenciais que serão usadas para todas as câmeras.
        """
        self.username = username
        # Codifica a senha para URLs (ex: 'Aluno@00' -> 'Aluno%4000')
        self.password_encoded = quote(password)
        
        # 1. Define o conteúdo estático do docker-compose.yml
        #    *** MODIFICAÇÃO: Adicionei a definição de 'networks' ***
        self.compose_config = {
            'version': '3.8', # Boa prática especificar a versão
            'services': {
                'rtsp-proxy': {
                    'image': 'bluenviron/mediamtx:latest',
                    'container_name': 'rtsp-proxy-server',
                    'restart': 'unless-stopped',
                    'ports': [
                        "8554:8554", # Porta principal do RTSP
                        "8443:8443", # Porta Web (WebRTC)
                        "8888:8888"  # Porta HLS (e painel web)
                    ],
                    'volumes': [
                        './mediamtx.yml:/mediamtx.yml' 
                    ],
                    'networks': [ # Conecta o proxy à nossa rede interna
                        'camera-net'
                    ]
                }
                # Os workers serão adicionados aqui dinamicamente
            },
            'networks': { # Define a rede interna
                'camera-net': {
                    'driver': 'bridge'
                }
            }
        }
        
        # 2. Prepara a base para o mediamtx.yml dinâmico
        self.mediamtx_config = {
            'paths': {} # Os 'paths' serão preenchidos
        }

    def generate_files(self, scan_results):
        """
        Usa os resultados do scan para gerar os dois arquivos de configuração.
        
        Args:
            scan_results (dict): Dicionário no formato {'ip': [port1, port2]}
        """
        
        cam_counter = 1
        for ip, ports in scan_results.items():
            for port in ports:
                # Cria um nome de caminho lógico (ex: cam1, cam2)
                path_name = f"cam{cam_counter}"
                
                # --- 1. Configuração do Proxy (mediamtx.yml) ---
                # (O que você já tinha feito)
                source_url = (
                    f"rtsp://{self.username}:{self.password_encoded}"
                    f"@{ip}:{port}" # Exemplo Hikvision
                    # NOTA: O caminho exato (/Streaming/Channels/1) pode variar!
                )
                
                self.mediamtx_config['paths'][path_name] = {
                    'source': source_url
                }
                
                # --- 2. Configuração do Worker (docker-compose.yml) ---
                # *** ESTA É A PARTE NOVA E CRUCIAL ***
                
                worker_service_name = f"worker-{path_name}"
                
                # A URL que o worker vai usar (apontando para o proxy)
                worker_rtsp_url = f"rtsp://rtsp-proxy:8554/{path_name}"

                self.compose_config['services'][worker_service_name] = {
                    'build': '.', # Usa o Dockerfile na pasta atual
                    'container_name': worker_service_name,
                    'restart': 'on-failure',
                    'depends_on': [
                        'rtsp-proxy' # Garante que o proxy inicie primeiro
                    ],
                    'environment': [
                        f'RTSP_URL={worker_rtsp_url}',
                        f'CAMERA_ID={path_name}'
                    ],
                    'volumes': [
                        # Mapeia a pasta de capturas para o host
                        './capturas:/app/capturas' 
                    ],
                    'networks': [ # Conecta o worker à mesma rede
                        'camera-net'
                    ]
                }
                
                cam_counter += 1

        # --- Salva os arquivos ---
        compose_filename = "docker-compose.yml"
        with open(compose_filename, 'w') as f:
            yaml.dump(self.compose_config, f, default_flow_style=False, sort_keys=False)
        print(f"Arquivo gerado: {os.path.abspath(compose_filename)}")

        mtx_filename = "mediamtx.yml"
        with open(mtx_filename, 'w') as f:
            yaml.dump(self.mediamtx_config, f, default_flow_style=False, sort_keys=False)
        print(f"Arquivo gerado: {os.path.abspath(mtx_filename)}")
        
        print("\n--- Relatório de Streams ---")
        for path, config in self.mediamtx_config['paths'].items():
            print(f"  [Câmera Real] {config['source']}")
            print(f"    -> [Proxy] rtsp://rtsp-proxy:8554/{path} (acesso interno dos workers)")
            print(f"    -> [Host]  rtsp://localhost:8554/{path} (acesso do seu PC, ex: VLC)")
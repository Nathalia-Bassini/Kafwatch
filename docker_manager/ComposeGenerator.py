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
                },
                'kafka': {
                    'image': 'confluentinc/cp-kafka:latest',
                    'container_name': 'kafka',
                    'networks': [
                        'camera-net'
                    ],
                    'restart': 'unless-stopped',
                    'ports': ["9092:9092"],
                    'environment': {
                        'KAFKA_PROCESS_ROLES': 'broker,controller',
                        'KAFKA_NODE_ID': 1,
                        'KAFKA_CONTROLLER_QUORUM_VOTERS': '1@kafka:9093',
                        # INTERNA (para os workers) na porta 29092
                        # EXTERNA (para o host) na porta 9092
                        'KAFKA_LISTENERS': 'INTERNAL://:29092,EXTERNAL://:9092,CONTROLLER://:9093',
                        'KAFKA_LISTENER_SECURITY_PROTOCOL_MAP': 'INTERNAL:PLAINTEXT,EXTERNAL:PLAINTEXT,CONTROLLER:PLAINTEXT',
                        # Diz aos workers para usar 'kafka:29092'
                        # Diz ao seu host (ex: consumidor) para usar 'localhost:9092'
                        'KAFKA_ADVERTISED_LISTENERS': 'INTERNAL://kafka:29092,EXTERNAL://localhost:9092',                        
                        'KAFKA_CONTROLLER_LISTENER_NAMES': 'CONTROLLER',
                        # <--- Define qual listener os brokers usarão para falar entre si ---
                        'KAFKA_INTER_BROKER_LISTENER_NAME': 'INTERNAL',                      
                        # Configurações KRaft de nó único
                        'KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR': 1,
                        'KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR': 1,
                        'KAFKA_TRANSACTION_STATE_LOG_MIN_ISR': 1,
                        'CLUSTER_ID': 'MkU3OEVBNTcwNTJENDM2Qk' ,
                    }
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

        # 3. Cria o arquivo Docker para rodar em cada camera
        self.docker_config = [
            'FROM python:3.10-slim\n',
            'WORKDIR /app \n',
            """RUN apt-get update && apt-get install -y --no-install-recommends \\
    libgl1 \\
    ffmpeg \\
    v4l-utils \\
    && rm -rf /var/lib/apt/lists/*
""",
            'COPY . .\n',
            'RUN pip install .\n',
            'CMD ["kafwatch-run"]'
        ]

        self.pyproject_config = [
            """[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

[project]
name = "kafwatch-worker"
version = "0.1.0"
dependencies = [
    # Coloque suas dependências aqui
    "opencv-python",
    "python-dotenv",
    "kafka-python",
    "numpy"
]

[project.scripts]
kafwatch-run = "kafwatch_worker.capture:main" """]
        
        self.kafka_config = [
            """services:
  kafka:
    image: confluentinc/cp-kafka:latest
    container_name: kafka
    ports:
      # A porta 9092 é para o seu script Python se conectar
      - "9092:9092"
    environment:
      # ---- Configuração do KRaft (Substitui o Zookeeper) ----
      # Define as funções: ele será o Broker E o Controller
      KAFKA_PROCESS_ROLES: 'broker,controller'
      KAFKA_NODE_ID: 1
      # Informa ao controller para votar em si mesmo
      KAFKA_CONTROLLER_QUORUM_VOTERS: '1@kafka:9093' 
      
      # ---- Configuração de Rede (Listeners) ----
      KAFKA_LISTENERS: 'PLAINTEXT://:9092,CONTROLLER://:9093'
      # Informa aos clientes (como o Python) como se conectar de fora do Docker
      KAFKA_ADVERTISED_LISTENERS: 'PLAINTEXT://localhost:9092'
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: 'CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT'
      KAFKA_CONTROLLER_LISTENER_NAMES: 'CONTROLLER'
      
      # ---- Configurações para cluster de nó único ----
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      
      # ---- ID do Cluster (Necessário para KRaft) ----
      # Você pode usar este ID aleatório
      CLUSTER_ID: 'MkU3OEVBNTcwNTJENDM2Qk' """
        ]
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
                    'build': {'context': '../worker_build', 
                              'dockerfile': 'Dockerfile'}, 
                    'container_name': worker_service_name,
                    'restart': 'on-failure',
                    'depends_on': [
                        'rtsp-proxy', # Garante que o proxy inicie primeiro
                        'kafka'       # Garante que o Kafka inicie primeiro
                    ],
                    'environment': [
                        f'RTSP_URL={worker_rtsp_url}',
                        f'CAMERA_ID={path_name}',
                        'KAFKA_BOOTSTRAP_SERVERS=kafka:29092'
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
        if(not os.path.exists("docker_files")):
            os.makedirs("docker_files")

        compose_filename = "docker_files/docker-compose.yml"
        try:
            with open(compose_filename, 'w') as f:
                yaml.dump(self.compose_config, f, default_flow_style=False, sort_keys=False)
            print(f"Arquivo gerado: {os.path.abspath(compose_filename)}")
        except Exception as e:
            print(f"Erro ao salvar docker-compose.yml: {e}")

        mtx_filename = "docker_files/mediamtx.yml"
        try:
            with open(mtx_filename, 'w') as f:
                yaml.dump(self.mediamtx_config, f, default_flow_style=False, sort_keys=False)
            print(f"Arquivo gerado: {os.path.abspath(mtx_filename)}")
        except Exception as e:
            print(f"Erro ao salvar mediamtx.yml: {e}")
        
        # --- Salva os arquivos do worker ---
        if(not os.path.exists("worker_build")):
            os.makedirs("worker_build")

        docker_filename = "worker_build/Dockerfile"
        try:
            with open(docker_filename, 'w') as f:
                f.writelines(self.docker_config)

        except Exception as e:
            print(f"Erro ao salvar Dockerfile: {e}")

        pyproject_filename = "worker_build/pyproject.toml"
        try:
            with open(pyproject_filename, 'w') as f:
                f.writelines(self.pyproject_config)
        except Exception as e:
            print(f"Erro ao salvar pyproject.toml: {e}")

        print("\n--- Relatório de Streams ---")
        for path, config in self.mediamtx_config['paths'].items():
            print(f"  [Câmera Real] {config['source']}")
            print(f"    -> [Proxy] rtsp://rtsp-proxy:8554/{path} (acesso interno dos workers)")
            print(f"    -> [Host]  rtsp://localhost:8554/{path} (acesso do seu PC, ex: VLC)")
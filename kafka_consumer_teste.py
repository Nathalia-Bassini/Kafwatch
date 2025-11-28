import os
import cv2
import numpy as np
import threading
import time
from kafka import KafkaConsumer
from dotenv import load_dotenv

# --- Classe Worker para Consumo em Background ---
class KafkaStreamReader:
    def __init__(self, bootstrap_servers, topic_name, group_id):
        self.lock = threading.Lock()
        self.running = False
        self.latest_frames = {} # Dicionário compartilhado: {'cam1': frame, 'cam2': frame}
        
        # Configuração do Consumidor Otimizada para Latência
        self.consumer = KafkaConsumer(
            topic_name,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset='latest',
            enable_auto_commit=True,
            # Fetch settings agressivos para pegar dados assim que chegarem
            fetch_min_bytes=1, 
            fetch_max_wait_ms=100,
            # Importante: não manter metadados velhos
            metadata_max_age_ms=1000
        )
        
        self.thread = threading.Thread(target=self._update_loop)
        self.thread.daemon = True # Morre se o programa principal morrer

    def start(self):
        self.running = True
        self.thread.start()
        print("[Thread] Leitor Kafka iniciado em background.")

    def stop(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join()
        self.consumer.close()

    def _update_loop(self):
        """Loop que roda em outra thread, focado apenas em REDE e DECODE."""
        while self.running:
            # Poll agressivo com timeout baixo
            pacote = self.consumer.poll(timeout_ms=10)
            
            if not pacote:
                continue

            for particao, mensagens in pacote.items():
                if not mensagens:
                    continue
                
                # --- ESTRATÉGIA DE FRAME DROPPING ---
                # Pega apenas a ÚLTIMA mensagem do lote (a mais recente)
                msg = mensagens[-1]
                
                if msg.key is None:
                    continue
                
                cam_id = msg.key.decode('utf-8')
                
                try:
                    # O 'imdecode' é pesado (CPU), por isso fazemos aqui na thread,
                    # e não na main thread que desenha a tela.
                    nparr = np.frombuffer(msg.value, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        # Seção Crítica: Atualiza o dicionário de forma segura
                        with self.lock:
                            self.latest_frames[cam_id] = frame
                            
                except Exception as e:
                    print(f"Erro decode: {e}")

    def get_frames(self):
        """Retorna uma cópia segura dos frames atuais para exibição."""
        with self.lock:
            return self.latest_frames.copy()

# --- Função Principal (Apenas GUI) ---
def main():
    load_dotenv()
    KAFKA_HOST = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    TOPIC = 'meu-topico-de-video'
    GROUP_ID = 'grupo-turbo-v1'

    # 1. Inicia o leitor em background
    reader = KafkaStreamReader(KAFKA_HOST, TOPIC, GROUP_ID)
    reader.start()

    print("[Main] Interface gráfica iniciada. Pressione 'q' para sair.")

    try:
        while True:
            # 2. Pega os frames já decodificados da thread
            frames = reader.get_frames()

            if not frames:
                # Se não tem frames, dorme um pouco para não fritar a CPU à toa
                time.sleep(0.01)
                continue

            # 3. Exibe as janelas
            for cam_id, frame in frames.items():
                cv2.imshow(f"Monitor: {cam_id}", frame)

            # 4. Controle da GUI
            # waitKey(1) é o mínimo para o OpenCV processar eventos de janela
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("Ctrl+C detectado.")
    finally:
        reader.stop()
        cv2.destroyAllWindows()
        print("Encerrado.")

if __name__ == "__main__":
    main()
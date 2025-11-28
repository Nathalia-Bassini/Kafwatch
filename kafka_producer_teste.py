import cv2
import time
import threading
import sys
import os
from kafka import KafkaProducer
from dotenv import load_dotenv

# --- Classe para Leitura de Câmera em Thread Separada ---
# Isso impede que o 'send' do Kafka bloqueie a leitura da câmera
class CameraBufferCleaner:
    def __init__(self, rtsp_url):
        self.stream = cv2.VideoCapture(rtsp_url)
        if not self.stream.isOpened():
            print(f"Erro ao abrir stream: {rtsp_url}")
            sys.exit(1)
            
        # Define buffer size baixo para evitar latência
        self.stream.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        self.last_frame = None
        self.stopped = False
        self.lock = threading.Lock()
        
        # Inicia a thread de leitura
        self.t = threading.Thread(target=self.update, args=())
        self.t.daemon = True
        self.t.start()

    def update(self):
        while not self.stopped:
            ret, frame = self.stream.read()
            if not ret:
                self.stopped = True
                break
            
            # Mantém apenas o frame mais recente na memória
            with self.lock:
                self.last_frame = frame

    def read(self):
        with self.lock:
            return self.last_frame is not None, self.last_frame

    def stop(self):
        self.stopped = True
        self.t.join()
        self.stream.release()

def main():
    load_dotenv()
    RTSP_URL = os.environ.get("RTSP_URL")
    CAMERA_ID = os.environ.get("CAMERA_ID")
    KAFKA_HOST = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')

    # Configurações de Qualidade
    NOVO_TAMANHO = (640, 480)
    QUALIDADE_JPEG = 70 # 70 é um ótimo balanço entre tamanho e velocidade
    
    # 1. Configurar Kafka
    # batch_size maior ajuda no throughput
    produtor = KafkaProducer(
        bootstrap_servers=KAFKA_HOST,
        linger_ms=5, 
        batch_size=32768, 
        compression_type='gzip' # Compressão extra no nível do Kafka
    )
    
    # 2. Iniciar captura em Thread
    #print(f"Iniciando captura otimizada para {CAMERA_ID}...")
    cam_cleaner = CameraBufferCleaner(RTSP_URL)
    
    # Aguarda o primeiro frame
    time.sleep(1.0) 

    contador_frames = 0
    contador_bytes = 0
    tempo_inicio = time.time()
    
    try:
        while True:
            # Pega o frame mais recente (instantâneo)
            sucess, frame = cam_cleaner.read()
            
            if not sucess:
                continue # Se a thread ainda não leu um novo frame, pula
            
            # --- Processamento ---
            frame_redimensionado = cv2.resize(frame, NOVO_TAMANHO)
            frame_cinza = cv2.cvtColor(frame_redimensionado, cv2.COLOR_BGR2GRAY)
            
            # --- Compressão (Essencial para FPS alto) ---
            # Enviar RAW (300KB) é lento. JPEG (20KB) é rápido.
            ret, buffer = cv2.imencode('.jpg', frame_cinza, [cv2.IMWRITE_JPEG_QUALITY, QUALIDADE_JPEG])
            
            if ret:
                dados_msg = buffer.tobytes()
                
                # Envio Assíncrono (Fire and Forget)
                produtor.send(
                    'meu-topico-de-video', 
                    key=CAMERA_ID.encode('utf-8'), 
                    value=buffer.tobytes()
                )
                
                # Stats
                contador_frames += 1
                contador_bytes += len(dados_msg)
            
            # --- Monitoramento (A cada 1s) ---
            tempo_atual = time.time()
            tempo_passado = tempo_atual - tempo_inicio
            if tempo_passado >= 1.0:
                fps = contador_frames / tempo_passado
                mb_s = (contador_bytes / (1024*1024)) / tempo_passado
                
                #print(f"[{CAMERA_ID}] FPS: {fps:.2f} | Rede: {mb_s:.2f} MiB/s")
                
                contador_frames = 0
                contador_bytes = 0
                tempo_inicio = time.time()

    except KeyboardInterrupt:
        print("Parando...")
    finally:
        cam_cleaner.stop()
        produtor.close()

if __name__ == "__main__":
    main()
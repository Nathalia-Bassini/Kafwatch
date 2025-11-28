from kafka import KafkaProducer
import cv2
import sys
import os
from dotenv import load_dotenv
import numpy as np
import time

def main():
    load_dotenv()
    RTSP_URL = os.environ.get("RTSP_URL")
    CAMERA_ID = os.environ.get("CAMERA_ID")

    # 1. Configurar e criar o Produtor
    produtor = KafkaProducer(
        bootstrap_servers='localhost:9092',
        linger_ms=1
    )
    novo_tamanho = (640, 480) # 480p
    qualidade_jpg = 100
    # Fechar o produtor (em um script real, faria isso ao final)
    #produtor.close()

    # ----------------------------------------------
    # Tenta abrir o stream de vídeo
    cap = cv2.VideoCapture(RTSP_URL)

    if not cap.isOpened():
        print(f"Erro: Não foi possível abrir o stream RTSP da URL: {RTSP_URL}")
        sys.exit(1)

    contador_bytes = 0
    contador_frames = 0
    tempo_inicio = time.time()
    while True:
       
        sucess, frame = cap.read()
        if not sucess:
            print("Erro ao capturar o frame do stream.")
            break

        frame_redimensionado = cv2.resize(frame, novo_tamanho)
        frame_cinza = cv2.cvtColor(frame_redimensionado, cv2.COLOR_BGR2GRAY)
        #ret, buffer = cv2.imencode('.jpg', frame_cinza, [cv2.IMWRITE_JPEG_QUALITY, qualidade_jpg]
        dados_imagem = frame_cinza.tobytes()

        produtor.send('meu-topico-de-video',
                      key = CAMERA_ID.encode('utf-8'), #chave
                      value = dados_imagem #dados
                      )
        #produtor.flush() # Garante que a mensagem foi enviada

        tamanho_msg = len(dados_imagem) # Tamanho em bytes
        contador_bytes += tamanho_msg
        contador_frames += 1

        tempo_atual = time.time()
        delta_tempo = tempo_atual - tempo_inicio
        if delta_tempo >= 1.0:
            mb_por_segundo = (contador_bytes / (1024 * 1024)) / delta_tempo
            fps = contador_frames / delta_tempo
            tamanho_medio_kb = (contador_bytes / contador_frames) / 1024        

            print(f"[Stats {CAMERA_ID}] "
                    f"Taxa: {mb_por_segundo:.2f} MB/s | "
                    f"FPS: {fps:.1f} | "
                    f"Tamanho Médio: {tamanho_medio_kb:.1f} KB")
      
            # Reseta os contadores
            contador_bytes = 0
            contador_frames = 0
            tempo_inicio = time.time()

        #cv2.imshow("Camera Stream", frame_cinza)

        # Pressione 'q' para sair
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    # Libera o objeto de captura
    cap.release()

if __name__ == "__main__":
    main() 
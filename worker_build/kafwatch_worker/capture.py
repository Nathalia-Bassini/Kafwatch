from kafka import KafkaProducer
import cv2
import sys
import os
from dotenv import load_dotenv
import numpy as np
import multiprocessing
def main():
    load_dotenv()
    RTSP_URL = os.environ.get("RTSP_URL")
    CAMERA_ID = os.environ.get("CAMERA_ID")
    KAFKA_HOST = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')

    # 1. Configurar e criar o Produtor
    produtor = KafkaProducer(
        bootstrap_servers=KAFKA_HOST,
        linger_ms=1
    )
    novo_tamanho = (640, 480) # 480p
    qualidade_jpg = 40
    # Fechar o produtor (em um script real, faria isso ao final)
    #produtor.close()
    # -----------------------------------------------
    # Tenta abrir o stream de vídeo
    cap = cv2.VideoCapture(RTSP_URL)

    if not cap.isOpened():
        print(f"Erro: Não foi possível abrir o stream RTSP da URL: {RTSP_URL}")
        sys.exit(1)

    while True:
        
        sucess, frame = cap.read()

        if not sucess:
            print("Erro ao capturar o frame do stream.")
            break
        frame_redimensionado = cv2.resize(frame, novo_tamanho)
        ret, buffer = cv2.imencode('.jpg', frame_redimensionado)

        produtor.send('meu-topico-de-video', 
                      key = CAMERA_ID.encode('utf-8'), #chave
                      value = buffer.tobytes() #dados
                      )        
        
        if not ret:
            print("Error: Could not read frame. Stream may have ended or is corrupt.")
            break

        #cv2.imshow("Camera Stream", frame)

        # Pressione 'q' para sair
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Libera o objeto de captura
    cap.release()
    produtor.flush()
    produtor.close()

if __name__ == "__main__":
    main()


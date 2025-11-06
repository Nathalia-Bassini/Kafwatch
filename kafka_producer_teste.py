from kafka import KafkaProducer
import cv2
import sys
import time
import os
from dotenv import load_dotenv
import numpy as np

load_dotenv()
RTSP_URL = os.environ.get("RTSP_URL")
CAMERA_ID = os.environ.get("CAMERA_ID")

# 1. Configurar e criar o Produtor
produtor = KafkaProducer(
    bootstrap_servers='localhost:9092',
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

print("Stream RTSP aberto com sucesso! Tentando capturar um frame...")
while True:
    
    sucess, frame = cap.read()

    if not sucess:
        print("Erro ao capturar o frame do stream.")
        break
    frame_redimensionado = cv2.resize(frame, novo_tamanho)
    frame_cinza = cv2.cvtColor(frame_redimensionado, cv2.COLOR_BGR2GRAY)
    ret, buffer = cv2.imencode('.jpg', frame_cinza, [cv2.IMWRITE_JPEG_QUALITY, qualidade_jpg])

    produtor.send('meu-topico-de-video', buffer.tobytes())
    produtor.flush() # Garante que a mensagem foi enviada
    #print("Mensagem enviada com sucesso!")
    
    
    if not ret:
        print("Error: Could not read frame. Stream may have ended or is corrupt.")
        break

    #cv2.imshow("Camera Stream", frame)

    # Pressione 'q' para sair
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Libera o objeto de captura
cap.release()
print("Teste de captura finalizado.")


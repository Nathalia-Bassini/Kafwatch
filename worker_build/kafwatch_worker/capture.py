import cv2
import sys
import time
import os
from dotenv import load_dotenv

def main():
    load_dotenv()
    RTSP_URL = os.environ.get("RTSP_URL")
    CAMERA_ID = os.environ.get("CAMERA_ID")
    # -----------------------------------------------
    # Tenta abrir o stream de vídeo
    cap = cv2.VideoCapture(RTSP_URL)

    if not cap.isOpened():
        print(f"Erro: Não foi possível abrir o stream RTSP da URL: {RTSP_URL}")
        sys.exit(1)

    print("Stream RTSP aberto com sucesso! Tentando capturar um frame...")
    pt = 0
    j = 0
    init = time.time()
    while True:
        final = time.time()
        tp = final - init
        pt = tp//0.5
        if pt>j:
            j += 1
            filename = f"captured_frame_{j}.jpg"
            cv2.imwrite(filename, frame)
            print(f"Frame capturado e salvo como {filename} em {os.getcwd()} após {tp:.2f} segundos.")
        if tp > 2:
            
            break
        ret, frame = cap.read()
        
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

    while True:
        time.sleep(60)
        break

if __name__ == "__main__":
    main()
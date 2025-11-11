from kafka import KafkaConsumer
import numpy as np
import cv2

# --- 1. Configurar o Consumidor ---
# (Rode este script na sua máquina host, não no Docker)
consumidor = KafkaConsumer(
    'meu-topico-de-video',
    bootstrap_servers='localhost:9092',
    auto_offset_reset='earliest',
    # Um group_id é sempre recomendado
    group_id='meu-grupo-de-exibicao-simples' 
)

print("Iniciando consumidor simples...")
print("Esperando por mensagens no 'meu-topico-de-video'...")

# --- 2. Dicionário para guardar o frame mais recente de cada câmera ---
# A chave será o ID da câmera (ex: 'cam_1'), o valor será o frame (imagem)
ultimos_frames = {}

try:
    # --- 3. Loop Principal de Consumo e Exibição ---
    while True:
        
        # A. Pergunte ao Kafka por um lote de mensagens
        # O poll() busca todas as mensagens que chegaram desde a última chamada
        novas_mensagens = consumidor.poll(timeout_ms=50) # Timeout de 50ms

        # B. Se houver mensagens, processe TODAS elas
        if novas_mensagens:
            for particao, mensagens in novas_mensagens.items():
                for mensagem in mensagens:
                    try:
                        # Obtenha o ID da câmera pela chave
                        id_camera = mensagem.key.decode('utf-8')
                        
                        # Decodifique o frame
                        bytes_do_frame = mensagem.value
                        nparr = np.frombuffer(bytes_do_frame, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                        # C. Armazene o frame mais recente no dicionário
                        if frame is not None:
                            ultimos_frames[id_camera] = frame
                    
                    except Exception as e:
                        # Ignora frames corrompidos ou chaves inválidas
                        # print(f"Erro ao processar mensagem: {e}")
                        pass

        # D. EXIBA todos os frames mais recentes (fora do loop de poll)
        # Iteramos pelo dicionário e exibimos cada frame em sua janela
        if ultimos_frames:
            for id_camera, frame in ultimos_frames.items():
                # --- A MÁGICA ACONTECE AQUI ---
                # cv2.imshow cria/atualiza uma janela baseada no nome
                # Se id_camera for "cam_1", a janela será "Camera cam_1"
                # Se id_camera for "cam_2", a janela será "Camera cam_2"
                cv2.imshow(f"Camera {id_camera}", frame)
        
        # E. Verifique se o usuário quer sair
        # (Pressione 'q' com qualquer janela do OpenCV em foco)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Tecla 'q' pressionada, saindo...")
            break

except KeyboardInterrupt:
    print("\nEncerrando o consumidor (Ctrl+C)...")
finally:
    # Fecha tudo
    cv2.destroyAllWindows()
    consumidor.close()
    print("Consumidor fechado.")
from kafka import KafkaConsumer
import numpy as np
import cv2

# 1. Configurar e criar o Consumidor
consumidor = KafkaConsumer(
    'meu-topico-de-video',
    bootstrap_servers='localhost:9092',
    auto_offset_reset='earliest',
    # Use um group_id novo para garantir que ele leia desde o início
    group_id='grupo-video-display-poll-1' 
)

print("Esperando por mensagens no 'meu-topico-de-video'...")


# Variável para guardar o último frame válido recebido
ultimo_frame_valido = None

try:
    # Este é o nosso loop principal de renderização
    while True:
        
        # 1. Pergunte ao Kafka por mensagens
        novas_mensagens = consumidor.poll(timeout_ms=1) # Timeout de 10ms

        frame_para_exibir = None

        if novas_mensagens:
            # Encontramos mensagens!
            
            # --- ESTA É A MUDANÇA PRINCIPAL ---
            # Em vez de um loop 'for', vamos direto para a última mensagem
            # 1. Pegue a última partição que tem mensagens
            particao_recente = list(novas_mensagens.keys())[-1]
            
            # 2. Pegue a última mensagem dessa partição
            mensagem_recente = novas_mensagens[particao_recente][-1]
            # ------------------------------------

            # Agora só decodificamos UMA mensagem
            bytes_do_frame = mensagem_recente.value
            nparr = np.frombuffer(bytes_do_frame, np.uint8)
            frame_para_exibir = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # 3. Exiba o frame decodificado (se tivermos um)
        if frame_para_exibir is not None:
            cv2.imshow('Stream de Video do Kafka', frame_para_exibir)
        
        # 4. A linha que mantém a janela viva
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Tecla 'q' pressionada, saindo...")
            break

except KeyboardInterrupt:
    print("\nEncerrando o consumidor (Ctrl+C)...")
finally:
    cv2.destroyAllWindows()
    consumidor.close()
    print("Consumidor fechado.")
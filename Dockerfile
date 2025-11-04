# Usa uma imagem base Python com as ferramentas necessárias
FROM python:3.10-slim

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Instala as dependências de sistema necessárias para o OpenCV
# libgl1 é o substituto mais comum para libgl1-mesa-glx em imagens minimalistas
# Adicionamos 'v4l-utils' para futuras necessidades de manipulação de dispositivos de vídeo
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    ffmpeg \
    v4l-utils \
    && rm -rf /var/lib/apt/lists/*

# Instala a biblioteca Python OpenCV
RUN pip install opencv-python python-dotenv

# Copia o seu script de coleta de imagens
COPY capture_test.py /app/capture_test.py

# Define o comando padrão que será executado
CMD ["python", "capture_test.py"]
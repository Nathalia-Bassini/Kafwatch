FROM python:3.10-slim
WORKDIR /app 
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    ffmpeg \
    v4l-utils \
    && rm -rf /var/lib/apt/lists/*
RUN pip install opencv-python python-dotenv
COPY capture_test.py /app/capture_test.py
CMD ["python", "capture_test.py"]
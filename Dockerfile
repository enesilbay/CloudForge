FROM python:3.11-slim

# Git ve Docker iletişimi için temel sistem araçları
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Bağımlılıkları yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodunu kopyala
COPY . .

# Varsayılan komut (Docker Compose içerisinde ezilebilir)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

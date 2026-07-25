import os

def process_dockerfile(repo_path: str):
    dosyalar = os.listdir(repo_path)
    
    if "Dockerfile" in dosyalar:
        # Mevcut Dockerfile varsa varsayılan olarak 8000 kabul edelim
        return "Projede mevcut Dockerfile bulundu, aynen kullanılıyor.", 8000
        
    elif "package.json" in dosyalar:
        dockerfile_icerigi = """FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
"""
        with open(os.path.join(repo_path, "Dockerfile"), "w") as f:
            f.write(dockerfile_icerigi)
        return "Sistem tarafından otomatik Node.js Dockerfile oluşturuldu.", 3000
        
    elif "requirements.txt" in dosyalar:
        dockerfile_icerigi = """FROM python:3.10-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
        with open(os.path.join(repo_path, "Dockerfile"), "w") as f:
            f.write(dockerfile_icerigi)
        return "Sistem tarafından otomatik Python Dockerfile oluşturuldu.", 8000
        
    else:
        raise Exception("Desteklenmeyen proje! İçinde Dockerfile, requirements.txt veya package.json bulunmalı.")
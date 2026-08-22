import os
import json

def process_dockerfile(repo_path: str):
    dosyalar = os.listdir(repo_path)
    
    if "Dockerfile" in dosyalar:
        # Mevcut Dockerfile varsa varsayılan olarak 8000 kabul edelim
        return "Projede mevcut Dockerfile bulundu, aynen kullanılıyor.", 8000
        
    elif "package.json" in dosyalar:
        pkg_path = os.path.join(repo_path, "package.json")
        start_cmd = 'CMD ["npm", "start"]'
        target_port = 3000
        detected_msg = "Sistem tarafından otomatik Node.js Dockerfile oluşturuldu."

        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                pkg_data = json.load(f)
                scripts = pkg_data.get("scripts", {})
                deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                
                if "vite" in deps:
                    target_port = 5173
                    start_cmd = 'CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]'
                    detected_msg = "Vite projesi tespit edildi, otomatik Dockerfile oluşturuldu."
                elif "next" in deps:
                    target_port = 3000
                    start_cmd = 'CMD ["npm", "run", "dev"]'
                    detected_msg = "Next.js projesi tespit edildi, otomatik Dockerfile oluşturuldu."
                elif "start" in scripts:
                    target_port = 3000
                    start_cmd = 'CMD ["npm", "start"]'
                    detected_msg = "Node.js (npm start) projesi tespit edildi, otomatik Dockerfile oluşturuldu."
                elif "dev" in scripts:
                    target_port = 3000
                    start_cmd = 'CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]'
                    detected_msg = "Node.js (npm run dev) projesi tespit edildi, otomatik Dockerfile oluşturuldu."
        except Exception:
            pass

        dockerfile_icerigi = f"""FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --ignore-scripts
COPY . .
EXPOSE {target_port}
{start_cmd}
"""
        with open(os.path.join(repo_path, "Dockerfile"), "w", encoding="utf-8") as f:
            f.write(dockerfile_icerigi)
        return detected_msg, target_port
        
    elif "requirements.txt" in dosyalar:
        dockerfile_icerigi = """FROM python:3.10-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir uvicorn && pip install --no-cache-dir -r requirements.txt
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
        with open(os.path.join(repo_path, "Dockerfile"), "w", encoding="utf-8") as f:
            f.write(dockerfile_icerigi)
        return "Sistem tarafından otomatik Python Dockerfile oluşturuldu.", 8000
        
    else:
        raise Exception("Desteklenmeyen proje! İçinde Dockerfile, requirements.txt veya package.json bulunmalı.")
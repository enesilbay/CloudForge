from fastapi import FastAPI
from pydantic import BaseModel
import tempfile
import os
import shutil
import uuid
import socket
from git import Repo
import docker
import stat
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI(title="CloudForge API")
# YENİ: Tarayıcı güvenlik duvarını (CORS) aşmak için izinler
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # React'in adresi
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DeployRequest(BaseModel):
    repo_url: str

# YENİ: Gerçekten boş olan güvenli bir port bulma fonksiyonu
def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

# GÜNCELLENDİ: Önce mevcut Dockerfile var mı diye kontrol eden motor
def process_dockerfile(repo_path: str):
    dosyalar = os.listdir(repo_path)
    
    if "Dockerfile" in dosyalar:
        return "Projede mevcut Dockerfile bulundu, aynen kullanılıyor."
        
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
        return "Sistem tarafından otomatik Python Dockerfile oluşturuldu."
    else:
        raise Exception("Desteklenmeyen proje! İçinde Dockerfile veya requirements.txt bulunmalı.")

@app.post("/deploy")
async def deploy_app(request: DeployRequest):
    temp_dir = tempfile.mkdtemp()
    repo = None # YENİ: Repoyu finally bloğunda kapatabilmek için burada tanımlıyoruz
    
    try:
        print(f"Klonlanıyor: {request.repo_url}")
        repo = Repo.clone_from(request.repo_url, temp_dir)
        
        algilama_mesaji = process_dockerfile(temp_dir)
        
        deploy_id = uuid.uuid4().hex[:8]
        image_tag = f"cloudforge-app:{deploy_id}"
        container_name = f"cf-app-{deploy_id}"
        
        docker_client = docker.from_env()
        
        print(f"[{deploy_id}] İmaj inşa ediliyor...")
        image, build_logs = docker_client.images.build(
            path=temp_dir,
            tag=image_tag,
            rm=True
        )
        
        host_port = get_free_port()
        print(f"[{deploy_id}] Konteyner başlatılıyor... Port: {host_port}")
        
        container = docker_client.containers.run(
            image.id,
            name=container_name,
            detach=True,
            ports={'8000/tcp': host_port}
        )
        
        return {
            "status": "success",
            "message": "Uygulama başarıyla canlıya alındı!",
            "details": algilama_mesaji,
            "deploy_id": deploy_id,
            "url": f"http://localhost:{host_port}",
            "container_name": container_name
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
        
    finally:
        # YENİ: 1. GitPython'un dosya kilidini bırakmasını sağla
        if repo:
            repo.close()
            
        # YENİ: 2. Salt okunur (Read-Only) dosyaların kilidini açıp silen fonksiyon
        def remove_readonly(func, path, exc_info):
            os.chmod(path, stat.S_IWRITE)
            func(path)
            
        print(f"Geçici klasör temizleniyor: {temp_dir}")
        if os.path.exists(temp_dir):
            # Python 3.12 ve üstü için onexc kullanıyoruz
            shutil.rmtree(temp_dir, onexc=remove_readonly)
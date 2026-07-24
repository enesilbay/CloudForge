from celery import Celery
import tempfile
import os
import shutil
import socket
import stat
from git import Repo
import docker

celery_app = Celery(
    "cloudforge_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

# PORT BULMA FONKSİYONU
def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

# DOCKERFILE MOTORU
def process_dockerfile(repo_path: str):
    dosyalar = os.listdir(repo_path)
    if "Dockerfile" in dosyalar:
        return "Projede mevcut Dockerfile bulundu, aynen kullanılıyor."
    elif "requirements.txt" in dosyalar:
        dockerfile_icerigi = """FROM python:3.10-slim\nWORKDIR /app\nCOPY . /app\nRUN pip install --no-cache-dir -r requirements.txt\nEXPOSE 8000\nCMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]\n"""
        with open(os.path.join(repo_path, "Dockerfile"), "w") as f:
            f.write(dockerfile_icerigi)
        return "Sistem tarafından otomatik Python Dockerfile oluşturuldu."
    else:
        raise Exception("Desteklenmeyen proje! İçinde Dockerfile veya requirements.txt bulunmalı.")

# SALT OKUNUR SİLİCİ
def remove_readonly(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)

# ASIL ARKA PLAN İŞİMİZ
@celery_app.task(bind=True)
def build_and_deploy_task(self, repo_url, deploy_id):
    temp_dir = tempfile.mkdtemp()
    repo = None
    
    try:
        repo = Repo.clone_from(repo_url, temp_dir)
        algilama_mesaji = process_dockerfile(temp_dir)
        
        image_tag = f"cloudforge-app:{deploy_id}"
        container_name = f"cf-app-{deploy_id}"
        
        docker_client = docker.from_env()
        
        # Docker Build işlemi (zaman alan kısım)
        image, build_logs = docker_client.images.build(
            path=temp_dir, tag=image_tag, rm=True
        )
        
        # Docker Run işlemi
        host_port = get_free_port()
        container = docker_client.containers.run(
            image.id, name=container_name, detach=True, ports={'8000/tcp': host_port}
        )
        
        # İşlem bittiğinde Redis'e kaydedilecek Başarı Raporu
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
        if repo:
            repo.close()
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, onexc=remove_readonly)
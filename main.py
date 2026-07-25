from fastapi import FastAPI
from pydantic import BaseModel
import uuid
from fastapi.middleware.cors import CORSMiddleware

# YENİ: Aşçımızı (worker) ve görevimizi import ediyoruz
from tasks.worker import build_and_deploy_task, celery_app

from services.docker_service import list_containers, stop_container, remove_container

app = FastAPI(title="CloudForge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DeployRequest(BaseModel):
    repo_url: str

@app.post("/deploy")
async def deploy_app(request: DeployRequest):
    deploy_id = uuid.uuid4().hex[:8]
    
    # YENİ SİHİR: İşi arka plana atıyoruz! (API beklemez)
    task = build_and_deploy_task.delay(request.repo_url, deploy_id)
    
    return {
        "status": "processing",
        "message": "Uygulama kuyruğa alındı, inşa ediliyor...",
        "task_id": task.id,
        "deploy_id": deploy_id
    }

# YENİ UÇ NOKTA: Arayüzün gelip "İşim bitti mi?" diye soracağı yer
@app.get("/status/{task_id}")
async def get_status(task_id: str):
    # Redis'teki sipariş panosuna (AsyncResult) bak
    task_result = celery_app.AsyncResult(task_id)
    
    if task_result.ready():
        # İş bitmişse (hatalı veya başarılı) sonucu direkt dön
        return task_result.result
    else:
        # Hala çalışıyorsa durumu bildir
        return {"status": "processing"}

# YENİ UÇ NOKTALAR (DASHBOARD İÇİN)

@app.get("/containers")
async def get_containers():
    try:
        containers = list_containers()
        return {"status": "success", "containers": containers}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/containers/{container_id}/stop")
async def stop_app_container(container_id: str):
    try:
        stop_container(container_id)
        return {"status": "success", "message": "Konteyner durduruldu"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.delete("/containers/{container_id}")
async def delete_app_container(container_id: str):
    try:
        remove_container(container_id)
        return {"status": "success", "message": "Konteyner silindi"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
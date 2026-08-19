import os
import uuid
import asyncio
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis.asyncio as aioredis
from sqlalchemy.orm import Session

from tasks.worker import build_and_deploy_task, celery_app
from services.docker_service import list_containers, stop_container, remove_container

from db.database import engine, Base, get_db
from db import models, schemas, crud

# Veritabanı tablolarını otomatik oluştur
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CloudForge API",
    description="Render & Vercel Tarzı PaaS Platform API",
    version="0.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class DeployRequest(BaseModel):
    repo_url: str
    project_id: Optional[str] = None

# PROJE ENDPOINT'LERİ (VERİTABANI ENTEGRASYONU)

@app.post("/projects", response_model=schemas.ProjectResponse)
def create_new_project(project_in: schemas.ProjectCreate, db: Session = Depends(get_db)):
    """Yeni bir proje oluşturur."""
    project = crud.create_project(db, name=project_in.name, repo_url=project_in.repo_url)
    return project

@app.get("/projects", response_model=List[schemas.ProjectResponse])
def list_all_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Tüm projeleri listeler."""
    return crud.get_projects(db, skip=skip, limit=limit)

@app.get("/projects/{project_id}", response_model=schemas.ProjectResponse)
def get_project_detail(project_id: str, db: Session = Depends(get_db)):
    """Proje detayını ve projeye ait deploy geçmişini getirir."""
    project = crud.get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    return project

# DEPLOYMENT ENDPOINT'LERİ (VERİTABANI ENTEGRASYONU)

@app.post("/deploy")
def deploy_app(request: DeployRequest, db: Session = Depends(get_db)):
    """
    Yeni bir deploy işlemi başlatır.
    Deploy durumu veritabanında 'QUEUED' olarak saklanır ve Celery iş parçacığı tetiklenir.
    """
    deploy_id = uuid.uuid4().hex[:8]
    
    # 1. Veritabanında kalıcı Deployment kaydı oluştur
    deployment = crud.create_deployment(
        db,
        repo_url=request.repo_url,
        project_id=request.project_id,
        deploy_id=deploy_id
    )
    
    # 2. Celery kuyruğuna işi at
    task = build_and_deploy_task.delay(request.repo_url, deploy_id)
    
    return {
        "status": "processing",
        "message": "Uygulama kuyruğa alındı ve veritabanına kaydedildi.",
        "task_id": task.id,
        "deploy_id": deploy_id,
        "deployment": schemas.DeploymentResponse.model_validate(deployment)
    }

@app.get("/deployments", response_model=List[schemas.DeploymentResponse])
def list_deployments(project_id: Optional[str] = None, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """Tüm veya projeye özel deploy geçmişini veritabanından getirir."""
    return crud.get_deployments(db, project_id=project_id, skip=skip, limit=limit)

@app.get("/deployments/{deploy_id}", response_model=schemas.DeploymentResponse)
def get_deployment_detail(deploy_id: str, db: Session = Depends(get_db)):
    """Spesifik bir deploy işleminin veritabanındaki durumunu, sürelerini ve loglarını getirir."""
    deployment = crud.get_deployment_by_id(db, deploy_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment kaydı bulunamadı")
    return deployment

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    """Geriye dönük uyumluluk için Celery durum sorgulama endpoint'i."""
    task_result = celery_app.AsyncResult(task_id)
    if task_result.ready():
        return task_result.result
    else:
        return {"status": "processing"}

# KONTEYNER YÖNETİM ENDPOINT'LERİ

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

# CANLI LOG AKIŞI (WEBSOCKETS)

@app.websocket("/ws/logs/{deploy_id}")
async def websocket_logs(websocket: WebSocket, deploy_id: str):
    await websocket.accept()
    
    redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"logs_{deploy_id}")
    
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                log_data = message["data"]
                await websocket.send_text(log_data)
                if log_data == "EOF":
                    break
            await asyncio.sleep(0.1)
    except Exception as e:
        await websocket.send_text(f"Log bağlantı hatası: {str(e)}")
    finally:
        await pubsub.unsubscribe(f"logs_{deploy_id}")
        await websocket.close()
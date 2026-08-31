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

# Redis Konfigürasyonu
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_URL = os.getenv("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/0")

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

class DeployRequest(BaseModel):
    repo_url: str
    project_id: Optional[str] = None

from fastapi.security import OAuth2PasswordBearer

from services import auth_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Optional[models.User]:
    if not token:
        return None
    payload = auth_service.decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    user_id = payload["sub"]
    return crud.get_user_by_id(db, user_id=user_id)

# AUTH ENDPOINT'LERİ

@app.post("/auth/register", response_model=schemas.TokenResponse)
def register_user(user_in: schemas.UserRegister, db: Session = Depends(get_db)):
    """Yeni kullanıcı kaydı oluşturur ve JWT token döner."""
    if crud.get_user_by_username(db, user_in.username):
        raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten kullanımda.")
    if crud.get_user_by_email(db, user_in.email):
        raise HTTPException(status_code=400, detail="Bu e-posta adresi zaten kullanımda.")

    hashed_pw = auth_service.hash_password(user_in.password)
    user = crud.create_user(db, username=user_in.username, email=user_in.email, password_hash=hashed_pw)

    access_token = auth_service.create_access_token({"sub": user.id, "username": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": schemas.UserResponse.model_validate(user)
    }

@app.post("/auth/login", response_model=schemas.TokenResponse)
def login_user(login_in: schemas.UserLogin, db: Session = Depends(get_db)):
    """Kullanıcı girişi yapar ve JWT token döner."""
    user = crud.get_user_by_username(db, login_in.username_or_email) or crud.get_user_by_email(db, login_in.username_or_email)
    if not user or not user.hashed_password:
        raise HTTPException(status_code=400, detail="Geçersiz kullanıcı adı veya parola.")
    
    if not auth_service.verify_password(login_in.password, str(user.hashed_password)):
        raise HTTPException(status_code=400, detail="Geçersiz kullanıcı adı veya parola.")

    access_token = auth_service.create_access_token({"sub": user.id, "username": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": schemas.UserResponse.model_validate(user)
    }

@app.get("/auth/me", response_model=schemas.UserResponse)
def get_me(current_user: Optional[models.User] = Depends(get_current_user)):
    """Mevcut giriş yapmış kullanıcının profil bilgilerini döner."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Oturum açılmamış.")
    return current_user

# PROJE ENDPOINT'LERİ (VERİTABANI ENTEGRASYONU)

@app.post("/projects", response_model=schemas.ProjectResponse)
def create_new_project(
    project_in: schemas.ProjectCreate,
    current_user: Optional[models.User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Yeni bir proje oluşturur."""
    user_id = str(current_user.id) if current_user else None
    project = crud.create_project(db, name=project_in.name, repo_url=project_in.repo_url, user_id=user_id)
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

# BUILD SETTINGS ENDPOINT'LERİ

@app.get("/projects/{project_id}/build-settings", response_model=Optional[schemas.BuildSettingsResponse])
def get_project_build_settings(project_id: str, db: Session = Depends(get_db)):
    """Projeye ait custom build ayarlarını getirir."""
    project = crud.get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    return crud.get_build_settings(db, project_id)

@app.put("/projects/{project_id}/build-settings", response_model=schemas.BuildSettingsResponse)
def update_project_build_settings(
    project_id: str,
    settings_in: schemas.BuildSettingsUpdate,
    db: Session = Depends(get_db)
):
    """Projeye ait custom build ayarlarını oluşturur veya günceller."""
    project = crud.get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")

    return crud.upsert_build_settings(
        db,
        project_id=project_id,
        root_directory=settings_in.root_directory,
        install_command=settings_in.install_command,
        build_command=settings_in.build_command,
        start_command=settings_in.start_command,
        output_directory=settings_in.output_directory,
        port=settings_in.port
    )

# ORTAM DEĞİŞKENLERİ & SECRETS ENDPOINT'LERİ

@app.post("/projects/{project_id}/env", response_model=schemas.EnvVarResponse)
def set_project_env_var(project_id: str, env_in: schemas.EnvVarCreate, db: Session = Depends(get_db)):
    """Projeye yeni bir şifreli ortam değişkeni (secret) ekler veya günceller."""
    project = crud.get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")

    env_var = crud.create_or_update_env_var(
        db,
        project_id=project_id,
        key=env_in.key,
        value=env_in.value,
        environment=env_in.environment,
        is_secret=env_in.is_secret
    )
    decrypted_val = env_in.value
    masked_val = crud.mask_secret(decrypted_val) if env_var.is_secret else decrypted_val
    return {
        "id": env_var.id,
        "project_id": env_var.project_id,
        "key": env_var.key,
        "value_masked": masked_val,
        "environment": env_var.environment,
        "is_secret": env_var.is_secret,
        "created_at": env_var.created_at,
        "updated_at": env_var.updated_at
    }

@app.get("/projects/{project_id}/env", response_model=List[schemas.EnvVarResponse])
def get_project_env_vars(project_id: str, db: Session = Depends(get_db)):
    """Projeye ait tüm maskelenmiş ortam değişkenlerini getirir."""
    project = crud.get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    return crud.get_env_vars_by_project(db, project_id=project_id)

@app.delete("/projects/{project_id}/env/{env_id}")
def delete_project_env_var(project_id: str, env_id: str, db: Session = Depends(get_db)):
    """Bir ortam değişkenini siler."""
    success = crud.delete_env_var(db, env_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ortam değişkeni bulunamadı")
    return {"status": "success", "message": "Ortam değişkeni silindi"}

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
    
    # 2. Celery kuyruğuna işi at (project_id ile birlikte)
    task = build_and_deploy_task.delay(request.repo_url, deploy_id, project_id=request.project_id)

    
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
                if log_data is not None:
                    text_content = str(log_data)
                    await websocket.send_text(text_content)
                    if text_content == "EOF":
                        break
            await asyncio.sleep(0.1)
    except Exception as e:
        await websocket.send_text(f"Log bağlantı hatası: {str(e)}")
    finally:
        await pubsub.unsubscribe(f"logs_{deploy_id}")
        await websocket.close()

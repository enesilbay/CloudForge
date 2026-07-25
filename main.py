from fastapi import FastAPI
from pydantic import BaseModel
import uuid
from fastapi.middleware.cors import CORSMiddleware
from tasks.worker import build_and_deploy_task, celery_app
from services.docker_service import list_containers, stop_container, remove_container
from fastapi import WebSocket
import redis.asyncio as aioredis
import asyncio




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

# YENİ: CANLI LOG AKIŞI (WEBSOCKETS)

@app.websocket("/ws/logs/{deploy_id}")
async def websocket_logs(websocket: WebSocket, deploy_id: str):
    # 1. React'ten gelen bağlantıyı kabul et
    await websocket.accept()
    
    # 2. Redis radyosuna bağlan ve sadece bu deploy_id'nin kanalını dinle
    redis_client = aioredis.from_url("redis://localhost:6379/0", decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"logs_{deploy_id}")
    
    try:
        while True:
            # 3. Radyodan yeni bir mesaj var mı diye bak
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            
            if message:
                log_data = message["data"]
                # 4. Mesajı React'e fırlat
                await websocket.send_text(log_data)
                
                # 5. Eğer Celery "EOF" (İşlem Bitti) derse yayını kes
                if log_data == "EOF":
                    break
            
            # İşlemciyi yormamak için çok kısa bir bekleme
            await asyncio.sleep(0.1)
            
    except Exception as e:
        await websocket.send_text(f"Log bağlantı hatası: {str(e)}")
    finally:
        # İş bitince radyodan çık ve bağlantıyı kapat
        await pubsub.unsubscribe(f"logs_{deploy_id}")
        await websocket.close()
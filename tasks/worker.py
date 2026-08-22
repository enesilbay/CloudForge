from celery import Celery
import tempfile
import redis
import os

from services.git_service import clone_repo, cleanup_repo
from services.detector_service import process_dockerfile
from services.docker_service import get_free_port, build_image, run_container
from db.database import SessionLocal
from db import crud

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_URL = os.getenv("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/0")

celery_app = Celery(
    "cloudforge_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

@celery_app.task(bind=True)
def build_and_deploy_task(self, repo_url, deploy_id, project_id=None):
    temp_dir = tempfile.mkdtemp()
    repo = None
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    
    def emit_log(message: str, status: str = "BUILDING"):
        redis_client.publish(f"logs_{deploy_id}", message)
        with SessionLocal() as db:
            crud.update_deployment_status(db, deploy_id=deploy_id, status=status, build_log_append=message)

    try:
        emit_log(f"Klonlanıyor: {repo_url}\n", status="BUILDING")
        repo = clone_repo(repo_url, temp_dir)

        emit_log("Proje yapısı analiz ediliyor...\n")
        algilama_mesaji, container_port = process_dockerfile(temp_dir)
        emit_log(f"{algilama_mesaji}\n")
        
        image_tag = f"cloudforge-app:{deploy_id}"
        container_name = f"cf-app-{deploy_id}"
        
        build_image(temp_dir, image_tag, deploy_id)

        # Projeye özel şifrelenmiş ortam değişkenlerini (secrets) çöz ve hazırlayıp enjekte et
        env_vars = {}
        if project_id:
            with SessionLocal() as db:
                env_vars = crud.get_decrypted_env_dict_for_project(db, project_id=project_id)
                if env_vars:
                    emit_log(f"[ENV] {len(env_vars)} ortam degiskeni (secrets) konteynere enjekte ediliyor...\n")

        emit_log("Konteyner baslatiliyor...\n")
        host_port = get_free_port()
        
        run_container(image_tag, container_name, host_port, container_port, env_vars=env_vars)

        success_msg = f"[SUCCESS] Uygulama yayinda! Port: {host_port}\n"
        redis_client.publish(f"logs_{deploy_id}", success_msg)

        # Veritabaninda Basarili olarak guncelle
        with SessionLocal() as db:
            crud.update_deployment_status(
                db,
                deploy_id=deploy_id,
                status="SUCCESS",
                build_log_append=success_msg,
                host_port=host_port,
                container_port=container_port,
                container_name=container_name,
                detected_framework=algilama_mesaji
            )
        
        return {
            "status": "success",
            "message": "Uygulama basariyla canliya alindi!",
            "details": algilama_mesaji,
            "deploy_id": deploy_id,
            "url": f"http://localhost:{host_port}",
            "container_name": container_name
        }
        
    except Exception as e:
        error_msg = f"[ERROR] Kritik Hata: {str(e)}\n"
        redis_client.publish(f"logs_{deploy_id}", error_msg)
        with SessionLocal() as db:
            crud.update_deployment_status(
                db,
                deploy_id=deploy_id,
                status="FAILED",
                build_log_append=error_msg
            )
        return {"status": "error", "message": str(e)}
        
    finally:
        cleanup_repo(repo, temp_dir)
        redis_client.publish(f"logs_{deploy_id}", "EOF")
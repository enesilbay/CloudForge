from celery import Celery
import tempfile
import redis

from services.git_service import clone_repo, cleanup_repo
from services.detector_service import process_dockerfile
from services.docker_service import get_free_port, build_image, run_container

celery_app = Celery(
    "cloudforge_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

@celery_app.task(bind=True)
def build_and_deploy_task(self, repo_url, deploy_id):
    temp_dir = tempfile.mkdtemp()
    repo = None
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    try:
        redis_client.publish(f"logs_{deploy_id}", f"Klonlanıyor: {repo_url}\n")
        repo = clone_repo(repo_url, temp_dir)

        redis_client.publish(f"logs_{deploy_id}", "Proje yapısı analiz ediliyor...\n")
        # YENİ: Artık detector mesajın yanında portu da veriyor
        algilama_mesaji, container_port = process_dockerfile(temp_dir)
        redis_client.publish(f"logs_{deploy_id}", f"{algilama_mesaji}\n")
        
        image_tag = f"cloudforge-app:{deploy_id}"
        container_name = f"cf-app-{deploy_id}"
        
        build_image(temp_dir, image_tag, deploy_id)

        redis_client.publish(f"logs_{deploy_id}", "Konteyner başlatılıyor...\n")
        host_port = get_free_port()
        
        # YENİ: Konteyner portunu aşçıya (run_container) gönderiyoruz
        run_container(image_tag, container_name, host_port, container_port)

        redis_client.publish(f"logs_{deploy_id}", f"🚀 Uygulama yayında! Port: {host_port}\n")
        
        return {
            "status": "success",
            "message": "Uygulama başarıyla canlıya alındı!",
            "details": algilama_mesaji,
            "deploy_id": deploy_id,
            "url": f"http://localhost:{host_port}",
            "container_name": container_name
        }
        
    except Exception as e:
        redis_client.publish(f"logs_{deploy_id}", f"❌ Kritik Hata: {str(e)}\n")
        return {"status": "error", "message": str(e)}
        
    finally:
        cleanup_repo(repo, temp_dir)
        redis_client.publish(f"logs_{deploy_id}", "EOF")
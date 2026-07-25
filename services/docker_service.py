import socket
import docker
import redis

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

# YENİ: deploy_id parametresini ekledik ki hangi kanala anons edeceğimizi bilelim
def build_image(repo_path: str, image_tag: str, deploy_id: str):
    client = docker.from_env()
    # Redis bağlantımızı kuruyoruz
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    redis_client.publish(f"logs_{deploy_id}", f"İmaj inşa ediliyor: {image_tag}\n")
    
    # SİHİRLİ KISIM: decode=True ile logları satır satır alıyoruz (Kara Kutu yerine)
    build_logs = client.api.build(path=repo_path, tag=image_tag, rm=True, decode=True)
    
    for chunk in build_logs:
        if 'stream' in chunk:
            # Docker'dan gelen her yeni satırı anında radyoya (React'e) fırlat
            log_line = chunk['stream']
            redis_client.publish(f"logs_{deploy_id}", log_line)
        elif 'error' in chunk:
            # Hata olursa kırmızı alarm
            redis_client.publish(f"logs_{deploy_id}", f"HATA: {chunk['error']}\n")
            raise Exception(chunk['error'])
            
    redis_client.publish(f"logs_{deploy_id}", "Docker build başarıyla tamamlandı!\n")
    return True

def run_container(image_tag: str, container_name: str, host_port: int, container_port: int):
    client = docker.from_env()
    container = client.containers.run(
        image_tag,
        name=container_name,
        detach=True,
        ports={f'{container_port}/tcp': host_port} 
    )
    return container



def list_containers():
    client = docker.from_env()
    # Sadece bizim oluşturduğumuz (cf-app- ile başlayan) konteynerleri getir
    containers = client.containers.list(all=True, filters={"name": "cf-app-"})
    
    result = []
    for c in containers:
        # Konteynerin dışarıya açılan portunu bulmaya çalışıyoruz
        ports = c.attrs['NetworkSettings']['Ports']
        host_port = "Bilinmiyor"
        if ports:
            for k, v in ports.items():
                if v:
                    host_port = v[0]['HostPort']
                    break
        
        result.append({
            "id": c.short_id,
            "name": c.name,
            "status": c.status, # 'running' veya 'exited' döner
            "port": host_port
        })
    return result

def stop_container(container_id: str):
    client = docker.from_env()
    container = client.containers.get(container_id)
    container.stop()

def remove_container(container_id: str):
    client = docker.from_env()
    container = client.containers.get(container_id)
    container.remove(force=True) # force=True çalışıyorsa bile zorla siler
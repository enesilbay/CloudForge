import socket
import docker

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def build_image(repo_path: str, image_tag: str):
    client = docker.from_env()
    print(f"İmaj inşa ediliyor: {image_tag}")
    image, build_logs = client.images.build(path=repo_path, tag=image_tag, rm=True)
    return image

def run_container(image_tag: str, container_name: str, host_port: int, container_port: int):
    client = docker.from_env()
    print(f"Konteyner başlatılıyor: {container_name} -> Port: {host_port}")
    
    # YENİ: Sadece Detector'ün bulduğu doğru portu bağlıyoruz
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
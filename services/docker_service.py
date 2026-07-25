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


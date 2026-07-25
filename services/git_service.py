import os
import stat
import shutil
from git import Repo

def clone_repo(repo_url: str, temp_dir: str):
    print(f"Klonlanıyor: {repo_url}")
    return Repo.clone_from(repo_url, temp_dir)

def remove_readonly(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)

def cleanup_repo(repo, temp_dir: str):
    print(f"Geçici klasör temizleniyor: {temp_dir}")
    if repo:
        repo.close()
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, onexc=remove_readonly)
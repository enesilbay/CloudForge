from datetime import datetime, timezone
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from db.models import User, Project, Deployment, EnvironmentVariable, ProjectBuildSettings
from services.crypto_service import encrypt_secret, decrypt_secret

# User CRUD
def create_user(db: Session, username: str, email: str, password_hash: str) -> User:
    user = User(username=username, email=email, hashed_password=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

# Project CRUD
def create_project(db: Session, name: str, repo_url: str, user_id: Optional[str] = None) -> Project:
    project = Project(name=name, repo_url=repo_url, user_id=user_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

def get_project_by_id(db: Session, project_id: str) -> Optional[Project]:
    return db.query(Project).filter(Project.id == project_id).first()

def get_projects(db: Session, user_id: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Project]:
    query = db.query(Project)
    if user_id:
        query = query.filter(Project.user_id == user_id)
    return query.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()

# Build Settings CRUD
def get_build_settings(db: Session, project_id: str) -> Optional[ProjectBuildSettings]:
    return db.query(ProjectBuildSettings).filter(ProjectBuildSettings.project_id == project_id).first()

def upsert_build_settings(
    db: Session,
    project_id: str,
    root_directory: Optional[str] = None,
    install_command: Optional[str] = None,
    build_command: Optional[str] = None,
    start_command: Optional[str] = None,
    output_directory: Optional[str] = None,
    port: Optional[int] = None
) -> ProjectBuildSettings:
    settings = get_build_settings(db, project_id)
    if not settings:
        settings = ProjectBuildSettings(project_id=project_id)
        db.add(settings)

    settings.root_directory = root_directory
    settings.install_command = install_command
    settings.build_command = build_command
    settings.start_command = start_command
    settings.output_directory = output_directory
    settings.port = port
    settings.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(settings)
    return settings

# Environment Variables & Secrets CRUD
def mask_secret(value: str) -> str:
    """Secret değerini frontend için güvenli bir şekilde maskeler."""
    if not value:
        return "••••••••"
    if len(value) <= 4:
        return "••••"
    return value[:2] + "•" * (len(value) - 4) + value[-2:]

def create_or_update_env_var(
    db: Session,
    project_id: str,
    key: str,
    value: str,
    environment: str = "production",
    is_secret: bool = True
) -> EnvironmentVariable:
    # Var olan key varsa güncelle
    existing = db.query(EnvironmentVariable).filter(
        EnvironmentVariable.project_id == project_id,
        EnvironmentVariable.key == key,
        EnvironmentVariable.environment == environment
    ).first()

    encrypted_val = encrypt_secret(value)

    if existing:
        existing.value_encrypted = encrypted_val
        existing.is_secret = is_secret
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        env_var = EnvironmentVariable(
            project_id=project_id,
            key=key,
            value_encrypted=encrypted_val,
            environment=environment,
            is_secret=is_secret
        )
        db.add(env_var)
        db.commit()
        db.refresh(env_var)
        return env_var

def get_env_vars_by_project(db: Session, project_id: str) -> List[dict]:
    """Frontend için maskelenmiş ortam değişkenlerini döndürür."""
    env_vars = db.query(EnvironmentVariable).filter(EnvironmentVariable.project_id == project_id).all()
    result = []
    for var in env_vars:
        decrypted_val = decrypt_secret(str(var.value_encrypted))
        masked_val = mask_secret(decrypted_val) if var.is_secret else decrypted_val
        result.append({
            "id": var.id,
            "project_id": var.project_id,
            "key": var.key,
            "value_masked": masked_val,
            "environment": var.environment,
            "is_secret": var.is_secret,
            "created_at": var.created_at,
            "updated_at": var.updated_at
        })
    return result

def get_decrypted_env_dict_for_project(db: Session, project_id: str, environment: str = "production") -> Dict[str, str]:
    """Celery Worker'ın Docker konteynerine enjekte etmesi için şifresi çözülmüş dict döner."""
    env_vars = db.query(EnvironmentVariable).filter(
        EnvironmentVariable.project_id == project_id,
        EnvironmentVariable.environment.in_([environment, "all"])
    ).all()

    env_dict = {}
    for var in env_vars:
        env_dict[str(var.key)] = decrypt_secret(str(var.value_encrypted))
    return env_dict

def delete_env_var(db: Session, env_id: str) -> bool:
    env_var = db.query(EnvironmentVariable).filter(EnvironmentVariable.id == env_id).first()
    if not env_var:
        return False
    db.delete(env_var)
    db.commit()
    return True

# Deployment CRUD
def create_deployment(db: Session, repo_url: str, project_id: Optional[str] = None, deploy_id: Optional[str] = None) -> Deployment:
    deployment = Deployment(
        id=deploy_id if deploy_id else None,
        project_id=project_id,
        repo_url=repo_url,
        status="QUEUED"
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)
    return deployment

def get_deployment_by_id(db: Session, deploy_id: str) -> Optional[Deployment]:
    return db.query(Deployment).filter(Deployment.id == deploy_id).first()

def get_deployments(db: Session, project_id: Optional[str] = None, skip: int = 0, limit: int = 50) -> List[Deployment]:
    query = db.query(Deployment)
    if project_id:
        query = query.filter(Deployment.project_id == project_id)
    return query.order_by(Deployment.created_at.desc()).offset(skip).limit(limit).all()

def update_deployment_status(
    db: Session,
    deploy_id: str,
    status: str,
    build_log_append: Optional[str] = None,
    host_port: Optional[int] = None,
    container_port: Optional[int] = None,
    container_name: Optional[str] = None,
    detected_framework: Optional[str] = None,
    commit_hash: Optional[str] = None
) -> Optional[Deployment]:
    deployment = db.query(Deployment).filter(Deployment.id == deploy_id).first()
    if not deployment:
        return None

    deployment.status = status

    if status == "BUILDING" and not deployment.started_at:
        deployment.started_at = datetime.now(timezone.utc)

    if build_log_append:
        current_logs = deployment.build_logs or ""
        deployment.build_logs = current_logs + build_log_append

    if host_port is not None:
        deployment.host_port = host_port
    if container_port is not None:
        deployment.container_port = container_port
    if container_name:
        deployment.container_name = container_name
    if detected_framework:
        deployment.detected_framework = detected_framework
    if commit_hash:
        deployment.commit_hash = commit_hash

    if status in ["SUCCESS", "FAILED"]:
        now = datetime.now(timezone.utc)
        deployment.finished_at = now
        if deployment.started_at:
            started = deployment.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            deployment.duration_seconds = round((now - started).total_seconds(), 2)

    db.commit()
    db.refresh(deployment)
    return deployment


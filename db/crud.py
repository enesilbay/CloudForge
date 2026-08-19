from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from db.models import Project, Deployment

# Project CRUD
def create_project(db: Session, name: str, repo_url: str, user_id: Optional[str] = None) -> Project:
    project = Project(name=name, repo_url=repo_url, user_id=user_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

def get_project_by_id(db: Session, project_id: str) -> Optional[Project]:
    return db.query(Project).filter(Project.id == project_id).first()

def get_projects(db: Session, skip: int = 0, limit: int = 100) -> List[Project]:
    return db.query(Project).order_by(Project.created_at.desc()).offset(skip).limit(limit).all()

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
        deployment.started_at = datetime.utcnow()

    if build_log_append:
        if deployment.build_logs:
            deployment.build_logs += build_log_append
        else:
            deployment.build_logs = build_log_append

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
        deployment.finished_at = datetime.utcnow()
        if deployment.started_at:
            deployment.duration_seconds = round((deployment.finished_at - deployment.started_at).total_seconds(), 2)

    db.commit()
    db.refresh(deployment)
    return deployment

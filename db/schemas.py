from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Deployment Schemas
class DeploymentBase(BaseModel):
    repo_url: str

class DeploymentCreate(DeploymentBase):
    project_id: Optional[str] = None

class DeploymentResponse(BaseModel):
    id: str
    project_id: Optional[str] = None
    repo_url: str
    status: str
    commit_hash: Optional[str] = None
    commit_message: Optional[str] = None
    detected_framework: Optional[str] = None
    host_port: Optional[int] = None
    container_port: Optional[int] = None
    container_name: Optional[str] = None
    build_logs: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Project Schemas
class ProjectCreate(BaseModel):
    name: str
    repo_url: str

class ProjectResponse(BaseModel):
    id: str
    name: str
    repo_url: str
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    deployments: List[DeploymentResponse] = []

    class Config:
        from_attributes = True

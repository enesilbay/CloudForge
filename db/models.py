import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from db.database import Base

def generate_uuid():
    return uuid.uuid4().hex

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utcnow)

    projects: Mapped[List["Project"]] = relationship("Project", back_populates="owner", cascade="all, delete-orphan")

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    repo_url: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    owner: Mapped[Optional["User"]] = relationship("User", back_populates="projects")
    deployments: Mapped[List["Deployment"]] = relationship("Deployment", back_populates="project", cascade="all, delete-orphan")
    env_vars: Mapped[List["EnvironmentVariable"]] = relationship("EnvironmentVariable", back_populates="project", cascade="all, delete-orphan")

class EnvironmentVariable(Base):
    __tablename__ = "env_variables"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    environment: Mapped[Optional[str]] = mapped_column(String(30), default="production")  # production / preview / all
    is_secret: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="env_vars")


class Deployment(Base):
    __tablename__ = "deployments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("projects.id"), nullable=True)
    repo_url: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[Optional[str]] = mapped_column(String(30), default="QUEUED", index=True) # QUEUED, BUILDING, SUCCESS, FAILED
    
    commit_hash: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    commit_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detected_framework: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    host_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    container_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    container_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    build_logs: Mapped[Optional[str]] = mapped_column(Text, default="")
    
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utcnow)

    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="deployments")



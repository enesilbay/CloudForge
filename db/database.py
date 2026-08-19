import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# PostgreSQL veritabanı bağlantı adresi (varsayılan: docker-compose varsayılanı)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://cloudforge:cloudforge_secret@localhost:5432/cloudforge_db"
)

# SQLite desteği için connect_args kontrolü
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

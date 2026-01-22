from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings


# echo=True 会打印 SQL 语句，调试时可以打开
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    future=True,
    echo=False,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()

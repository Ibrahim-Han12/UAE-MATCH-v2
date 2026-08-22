"""测试共用 fixture。"""
import importlib
import pkgutil

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base


def _register_all_models() -> None:
    """导入 app.models 下全部模块，让 Base.metadata 收齐所有表。

    app/models/__init__.py 只显式登记了 BR-202 之后的新表，users / user_profiles 等
    早期表由各自模块定义；不全部导入，create_all 会因外键找不到 users 而失败。
    """
    import app.models as models_pkg

    for mod in pkgutil.iter_modules(models_pkg.__path__):
        importlib.import_module(f"app.models.{mod.name}")


@pytest.fixture()
def db():
    """内存 SQLite 会话：验状态读写，不依赖 Postgres。"""
    _register_all_models()
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()

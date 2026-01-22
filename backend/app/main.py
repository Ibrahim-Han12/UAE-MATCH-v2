from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import atexit

from app.core.config import settings
from app.core.scheduler import start_scheduler, stop_scheduler
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.profile import router as profile_router
from app.api.v1.endpoints.preferences import router as preferences_router
from app.db.session import engine
from app.db import base  # noqa
from app.api.v1.endpoints.matches import router as matches_router
from app.api.v1.endpoints.chat import router as chat_router
from app.api.v1.endpoints.chat_ws import router as chat_ws_router
from app.api.v1.endpoints.coach import router as coach_router
from app.api.v1.endpoints.safety import router as safety_router
from app.api.v1.endpoints.events import router as events_router
from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.admin import router as admin_router
from app.api.v1.endpoints.photos import router as photos_router
from app.api.v1.endpoints.payment import router as payment_router
from app.api.v1.endpoints.ai_chat import router as ai_chat_router
from app.api.v1.endpoints.match_recommendation import router as match_recommendation_router
from app.api.v1.endpoints.notifications import router as notifications_router






def create_app() -> FastAPI:
    base.Base.metadata.create_all(bind=engine)

    app = FastAPI(
        title="UAE Match API",
        version="0.1.0",
    )
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",  # 备用端口
        "http://localhost:5173",  # Vite 默认端口
        "http://127.0.0.1:5173",  # Vite 默认端口
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    app.include_router(health_router, prefix=settings.API_V1_STR)
    app.include_router(auth_router, prefix=settings.API_V1_STR)
    app.include_router(profile_router, prefix=settings.API_V1_STR)
    app.include_router(preferences_router, prefix=settings.API_V1_STR)
    app.include_router(matches_router, prefix=settings.API_V1_STR)
    app.include_router(chat_router, prefix=settings.API_V1_STR)
    app.include_router(chat_ws_router, prefix=settings.API_V1_STR)
    app.include_router(coach_router, prefix=settings.API_V1_STR)
    app.include_router(safety_router, prefix=settings.API_V1_STR)  
    app.include_router(events_router, prefix=settings.API_V1_STR)
    app.include_router(analytics_router, prefix=settings.API_V1_STR)
    app.include_router(admin_router, prefix=settings.API_V1_STR)
    app.include_router(photos_router, prefix=settings.API_V1_STR)
    app.include_router(payment_router, prefix=settings.API_V1_STR)
    app.include_router(ai_chat_router, prefix=settings.API_V1_STR)
    app.include_router(match_recommendation_router, prefix=settings.API_V1_STR)
    app.include_router(notifications_router, prefix=settings.API_V1_STR)

    # 启动定时任务调度器（用于清理缓存等）
    try:
        start_scheduler()
        # 注册退出时的清理函数
        atexit.register(stop_scheduler)
    except Exception as e:
        print(f"[WARNING] 启动定时任务调度器失败: {e}")

    return app


app = create_app()

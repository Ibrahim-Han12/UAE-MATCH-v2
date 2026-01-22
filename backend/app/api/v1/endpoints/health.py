from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["health"])
def health_check():
    """
    健康检查接口，用来确认服务是否正常运行。
    """
    return {"status": "ok"}

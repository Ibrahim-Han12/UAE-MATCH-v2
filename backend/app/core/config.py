from pydantic_settings import BaseSettings
from datetime import timedelta
from pathlib import Path
import os


# 确定 .env 文件路径
def find_env_file():
    """查找 .env 文件"""
    # 尝试多个可能的位置
    possible_paths = [
        Path(__file__).parent.parent.parent / ".env",  # backend/.env (从 app/core/config.py 向上找)
        Path(".env"),  # 当前工作目录
        Path("backend/.env"),  # 相对路径
    ]
    
    for path in possible_paths:
        if path.exists():
            return str(path.absolute())
    return ".env"  # 默认值


class Settings(BaseSettings):
    # 项目信息
    PROJECT_NAME: str = "UAE Match - Serious Dating for Chinese in UAE"
    API_V1_STR: str = "/api/v1"

    # 数据库配置
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///./app.db"

    # JWT 配置（可以放到 .env 里覆盖）
    JWT_SECRET_KEY: str = "change-this-in-production"  # !!! 上线必须改 !!!
    JWT_REFRESH_SECRET_KEY: str = "change-this-refresh-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30      # 访问令牌 30 分钟
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7         # 刷新令牌 7 天

    # 文件上传配置
    UPLOAD_DIR: str = "uploads"  # 上传文件目录
    MAX_PHOTO_SIZE: int = 10 * 1024 * 1024  # 最大照片大小 10MB
    ALLOWED_PHOTO_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp"]
    PHOTOS_PER_USER: int = 9  # 每个用户最多照片数

    # 支付配置
    ALIPAY_APP_ID: str = ""  # 支付宝AppID
    ALIPAY_PRIVATE_KEY: str = ""  # 支付宝私钥
    ALIPAY_PUBLIC_KEY: str = ""  # 支付宝公钥
    WECHAT_APP_ID: str = ""  # 微信AppID
    WECHAT_MCH_ID: str = ""  # 微信商户号
    WECHAT_API_KEY: str = ""  # 微信API密钥
    PAYMENT_NOTIFY_URL: str = ""  # 支付回调URL

    # OpenAI配置
    OPENAI_API_KEY: str = ""  # OpenAI API Key（从环境变量读取）
    OPENAI_MODEL_GPT4O_MINI: str = "gpt-4o-mini"  # 主要模型：成本低、速度快、性能好
    OPENAI_MODEL_GPT4: str = "gpt-4"
    OPENAI_MODEL_GPT35: str = "gpt-3.5-turbo"
    OPENAI_MODEL_GPT4_TURBO: str = "gpt-4-turbo"  # 用于核心功能（匹配推荐）
    OPENAI_MODEL_EMBEDDING: str = "text-embedding-3-small"  # Embedding模型：成本极低
    
    # AI预算和配额配置
    GLOBAL_BUDGET_LIMIT: float = 500.00  # 全局月度预算上限（美元）
    DEFAULT_USER_TOKEN_LIMIT: int = 50000  # 普通用户月度token上限（提高至5万，确保能完成注册引导和基础咨询）
    VIP_USER_TOKEN_LIMIT: int = 100000  # VIP用户月度token上限
    DEFAULT_USER_RECOMMENDATION_QUOTA: int = 2  # 普通用户月度推荐额度
    VIP_USER_RECOMMENDATION_QUOTA: int = 10  # VIP用户月度推荐额度
    
    # 匹配分析报告缓存配置
    MATCH_INSIGHT_CACHE_EXPIRY_DAYS: int = 30  # 缓存有效期（天）
    MATCH_INSIGHT_CACHE_MAX_PER_USER: int = 20  # 每个用户最多缓存数量

    class Config:
        env_file = find_env_file()  # 使用找到的 .env 文件路径
        env_file_encoding = "utf-8"


settings = Settings()

# 如果 API Key 未加载，尝试手动从 .env 文件读取
if not settings.OPENAI_API_KEY:
    env_file_path = find_env_file()
    if env_file_path and Path(env_file_path).exists():
        try:
            # 尝试多种编码方式读取文件（处理BOM和编码问题）
            content = None
            for encoding in ["utf-8-sig", "utf-8", "gbk"]:
                try:
                    with open(env_file_path, "r", encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content:
                for line in content.splitlines():
                    line = line.strip()
                    # 跳过空行
                    if not line:
                        continue
                    
                    # 查找 OPENAI_API_KEY（可能在注释行中，也可能在独立行）
                    # 处理两种情况：
                    # 1. OPENAI_API_KEY=sk-... (独立行)
                    # 2. # comment OPENAI_API_KEY=sk-... (注释行中包含配置)
                    if "OPENAI_API_KEY=" in line:
                        # 找到 OPENAI_API_KEY= 的位置
                        key_start = line.find("OPENAI_API_KEY=")
                        if key_start >= 0:
                            # 提取从 OPENAI_API_KEY= 开始的部分
                            key_part = line[key_start + len("OPENAI_API_KEY="):].strip()
                            # 移除可能的引号
                            if key_part.startswith('"') and key_part.endswith('"'):
                                key_value = key_part[1:-1]
                            elif key_part.startswith("'") and key_part.endswith("'"):
                                key_value = key_part[1:-1]
                            else:
                                key_value = key_part
                            
                            # 如果值中有空格或特殊字符，取第一个有效部分
                            # 通常API Key是连续的，但如果有注释在后面，需要截断
                            if key_value:
                                # 移除可能的尾随注释（# 后面的内容）
                                if "#" in key_value:
                                    key_value = key_value.split("#")[0].strip()
                                if key_value:
                                    settings.OPENAI_API_KEY = key_value
                                    print(f"[OK] 成功从 .env 文件加载 OPENAI_API_KEY (长度: {len(key_value)})")
                                    break
        except Exception as e:
            print(f"[ERROR] 读取 .env 文件失败: {e}")
    
    # 如果还是为空，尝试从环境变量读取
    if not settings.OPENAI_API_KEY:
        env_key = os.getenv("OPENAI_API_KEY")
        if env_key:
            settings.OPENAI_API_KEY = env_key
            print(f"[OK] 从环境变量加载 OPENAI_API_KEY (长度: {len(env_key)})")
    
    # 最终检查
    if not settings.OPENAI_API_KEY:
        print("[WARNING] OPENAI_API_KEY 未配置，AI功能将无法使用")
    else:
        print(f"[OK] OPENAI_API_KEY 已配置 (前10个字符: {settings.OPENAI_API_KEY[:10]}...)")

# 确保上传目录存在
upload_path = Path(settings.UPLOAD_DIR)
upload_path.mkdir(parents=True, exist_ok=True)
(upload_path / "photos").mkdir(parents=True, exist_ok=True)

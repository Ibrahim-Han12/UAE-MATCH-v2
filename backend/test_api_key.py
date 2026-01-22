"""
测试脚本：检查 OPENAI_API_KEY 是否正确加载
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.core.config import settings
    
    print("=" * 50)
    print("OPENAI_API_KEY 配置检查")
    print("=" * 50)
    
    if settings.OPENAI_API_KEY:
        print(f"[OK] API Key 已加载")
        print(f"   长度: {len(settings.OPENAI_API_KEY)} 字符")
        print(f"   前10个字符: {settings.OPENAI_API_KEY[:10]}...")
        print(f"   后10个字符: ...{settings.OPENAI_API_KEY[-10:]}")
        
        # 测试 OpenAI 客户端初始化
        try:
            from app.core.openai_client import get_openai_client
            client = get_openai_client()
            print("\n[OK] OpenAI 客户端初始化成功")
        except Exception as e:
            print(f"\n[ERROR] OpenAI 客户端初始化失败: {e}")
    else:
        print("[ERROR] API Key 未加载")
        print("\n请检查:")
        print("1. .env 文件是否存在 (H:\\uae-match\\backend\\.env)")
        print("2. .env 文件中是否有 OPENAI_API_KEY=sk-...")
        print("3. 文件编码是否为 UTF-8")
    
    print("=" * 50)
    
except Exception as e:
    print(f"[ERROR] 检查失败: {e}")
    import traceback
    traceback.print_exc()














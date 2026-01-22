"""
启动后端服务器的辅助脚本
"""
import uvicorn
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    try:
        print("正在启动后端服务器...")
        print("访问地址: http://127.0.0.1:8000")
        print("API文档: http://127.0.0.1:8000/docs")
        print("按 Ctrl+C 停止服务器\n")
        
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

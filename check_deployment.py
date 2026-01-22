"""
前后端对接配置检查脚本
运行此脚本检查前后端配置是否正确
"""
import os
import sys
import json
from pathlib import Path

def check_backend_config():
    """检查后端配置"""
    print("\n" + "="*60)
    print("[检查] 后端配置")
    print("="*60)
    
    backend_path = Path(__file__).parent / "backend"
    main_py = backend_path / "app" / "main.py"
    config_py = backend_path / "app" / "core" / "config.py"
    env_file = backend_path / ".env"
    
    issues = []
    
    # 检查文件是否存在
    if not main_py.exists():
        issues.append("[错误] backend/app/main.py 不存在")
    else:
        print("[OK] backend/app/main.py 存在")
        
        # 检查 CORS 配置
        with open(main_py, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'localhost:3000' in content or '127.0.0.1:3000' in content:
                print("[OK] CORS 配置包含 localhost:3000")
            else:
                issues.append("[警告] CORS 配置可能不包含 localhost:3000")
    
    if not config_py.exists():
        issues.append("[错误] backend/app/core/config.py 不存在")
    else:
        print("[OK] backend/app/core/config.py 存在")
    
    if env_file.exists():
        print("[OK] backend/.env 文件存在")
    else:
        issues.append("[警告] backend/.env 文件不存在（可能使用默认配置）")
    
    # 检查数据库
    db_file = backend_path / "app.db"
    if db_file.exists():
        print(f"[OK] 数据库文件存在: {db_file}")
    else:
        issues.append("[警告] 数据库文件不存在，首次运行时会自动创建")
    
    return issues

def check_frontend_config():
    """检查前端配置"""
    print("\n" + "="*60)
    print("[检查] 前端配置")
    print("="*60)
    
    frontend_path = Path(__file__).parent / "uae-match-web"
    api_ts = frontend_path / "src" / "lib" / "api.ts"
    env_local = frontend_path / ".env.local"
    package_json = frontend_path / "package.json"
    node_modules = frontend_path / "node_modules"
    
    issues = []
    
    # 检查文件是否存在
    if not frontend_path.exists():
        issues.append("[错误] uae-match-web 目录不存在")
        print("[错误] 前端目录不存在，请先克隆或创建前端项目")
        return issues
    
    if not api_ts.exists():
        issues.append("[错误] src/lib/api.ts 不存在")
    else:
        print("[OK] src/lib/api.ts 存在")
        
        # 检查 API 配置
        with open(api_ts, 'r', encoding='utf-8') as f:
            content = f.read()
            if '127.0.0.1:8000' in content or 'localhost:8000' in content:
                print("[OK] API 基础 URL 配置正确（指向本地后端）")
            else:
                issues.append("[警告] API 基础 URL 可能不正确")
    
    if not package_json.exists():
        issues.append("[错误] package.json 不存在")
    else:
        print("[OK] package.json 存在")
    
    if not node_modules.exists():
        issues.append("[警告] node_modules 不存在，请运行 'npm install'")
    else:
        print("[OK] node_modules 存在")
    
    if env_local.exists():
        print("[OK] .env.local 文件存在")
        
        # 检查环境变量
        with open(env_local, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'NEXT_PUBLIC_API_BASE_URL' in content:
                print("[OK] NEXT_PUBLIC_API_BASE_URL 已配置")
            else:
                issues.append("[警告] .env.local 中缺少 NEXT_PUBLIC_API_BASE_URL")
    else:
        issues.append("[警告] .env.local 文件不存在，建议创建并配置 API 地址")
    
    return issues

def check_ports():
    """检查端口是否被占用"""
    print("\n" + "="*60)
    print("[检查] 端口占用")
    print("="*60)
    
    import socket
    
    ports_to_check = {
        8000: "后端 API",
        3000: "前端 Next.js",
    }
    
    issues = []
    
    for port, name in ports_to_check.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        
        if result == 0:
            print(f"[OK] 端口 {port} ({name}) 正在使用中（服务可能正在运行）")
        else:
            print(f"[信息] 端口 {port} ({name}) 未被占用（服务未运行）")
    
    return issues

def print_summary(backend_issues, frontend_issues):
    """打印总结"""
    print("\n" + "="*60)
    print("📊 检查总结")
    print("="*60)
    
    all_issues = backend_issues + frontend_issues
    
    if not all_issues:
        print("\n[OK] 所有配置检查通过！")
        print("\n下一步：")
        print("1. 启动后端: cd backend && python -m uvicorn app.main:app --reload")
        print("2. 启动前端: cd uae-match-web && npm run dev")
        print("3. 访问前端: http://localhost:3000")
    else:
        print(f"\n[警告] 发现 {len(all_issues)} 个问题：")
        for issue in all_issues:
            print(f"   {issue}")
        
        print("\n建议：")
        if any("CORS" in issue for issue in all_issues):
            print("- 检查 backend/app/main.py 中的 CORS 配置")
        if any("node_modules" in issue for issue in all_issues):
            print("- 运行: cd uae-match-web && npm install")
        if any(".env.local" in issue for issue in all_issues):
            print("- 创建 uae-match-web/.env.local 文件并配置 NEXT_PUBLIC_API_BASE_URL")

def main():
    """主函数"""
    import sys
    # 设置输出编码为 UTF-8（Windows 兼容）
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    print("\n" + "="*60)
    print("前后端对接配置检查")
    print("="*60)
    
    backend_issues = check_backend_config()
    frontend_issues = check_frontend_config()
    check_ports()
    
    print_summary(backend_issues, frontend_issues)
    
    print("\n" + "="*60)
    print("[信息] 详细部署指南请查看: DEPLOYMENT_GUIDE.md")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()










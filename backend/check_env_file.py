"""
检查并修复 .env 文件
"""
from pathlib import Path
import sys

# 设置输出编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

env_file = Path(__file__).parent / ".env"

print("=" * 60)
print("检查 .env 文件")
print("=" * 60)
print(f"文件路径: {env_file.absolute()}")
print(f"文件存在: {env_file.exists()}")

if env_file.exists():
    # 尝试多种编码读取
    for encoding in ["utf-8-sig", "utf-8", "gbk"]:
        try:
            content = env_file.read_text(encoding=encoding)
            print(f"\n使用编码 {encoding} 成功读取文件")
            print(f"文件内容 (前500字符):")
            print("-" * 60)
            print(content[:500])
            print("-" * 60)
            
            # 查找 OPENAI_API_KEY
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                line_stripped = line.strip()
                if "OPENAI_API_KEY" in line_stripped:
                    print(f"\n找到 OPENAI_API_KEY 在第 {i} 行:")
                    print(f"  原始内容: {line}")
                    print(f"  去除空格: {line_stripped}")
                    
                    if line_stripped.startswith("OPENAI_API_KEY="):
                        key_value = line_stripped.split("=", 1)[1].strip()
                        # 移除引号
                        if key_value.startswith('"') and key_value.endswith('"'):
                            key_value = key_value[1:-1]
                        elif key_value.startswith("'") and key_value.endswith("'"):
                            key_value = key_value[1:-1]
                        
                        if key_value:
                            print(f"  提取的Key长度: {len(key_value)}")
                            print(f"  前20个字符: {key_value[:20]}...")
                            print(f"  后20个字符: ...{key_value[-20:]}")
                        else:
                            print(f"  [ERROR] Key值为空")
                    else:
                        print(f"  [WARNING] 格式不正确，应该以 OPENAI_API_KEY= 开头")
            break
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"读取失败 ({encoding}): {e}")
else:
    print("\n[ERROR] .env 文件不存在！")

print("\n" + "=" * 60)














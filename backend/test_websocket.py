"""
WebSocket连接测试脚本
使用方法: python test_websocket.py
需要先安装: pip install websockets
"""
import asyncio
import websockets
import json
import sys

async def test_websocket(token: str, match_pair_id: int, base_url: str = "ws://localhost:8000"):
    """
    测试WebSocket连接
    
    Args:
        token: JWT token
        match_pair_id: 配对ID
        base_url: WebSocket服务器地址
    """
    url = f"{base_url}/api/v1/ws/chat/{match_pair_id}?token={token}"
    
    print(f"正在连接到: {url}")
    print("-" * 60)
    
    try:
        async with websockets.connect(url) as websocket:
            print("✓ WebSocket连接成功")
            
            # 接收连接确认消息
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                print(f"收到消息: {json.dumps(data, indent=2, ensure_ascii=False)}")
            except asyncio.TimeoutError:
                print("⚠ 未收到连接确认消息")
            
            # 发送测试消息
            test_message = {
                "type": "message",
                "content": "这是一条测试消息"
            }
            print(f"\n发送消息: {json.dumps(test_message, ensure_ascii=False, indent=2)}")
            await websocket.send(json.dumps(test_message))
            
            # 接收响应
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                print(f"收到响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
            except asyncio.TimeoutError:
                print("⚠ 未收到响应")
            
            # 发送ping
            print("\n发送ping...")
            await websocket.send(json.dumps({"type": "ping"}))
            
            try:
                pong = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(pong)
                print(f"收到pong: {json.dumps(data, indent=2, ensure_ascii=False)}")
            except asyncio.TimeoutError:
                print("⚠ 未收到pong响应")
            
            print("\n✓ 测试完成")
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"✗ 连接失败: HTTP {e.status_code}")
        if e.status_code == 403:
            print("  可能原因: 权限不足或配对不存在")
        elif e.status_code == 401:
            print("  可能原因: Token无效或过期")
    except Exception as e:
        print(f"✗ 错误: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("WebSocket连接测试工具")
    print("=" * 60)
    
    if len(sys.argv) < 3:
        print("\n使用方法:")
        print("  python test_websocket.py <token> <match_pair_id>")
        print("\n示例:")
        print("  python test_websocket.py eyJ0eXAiOiJKV1QiLCJhbGc... 1")
        print("\n或者交互式输入:")
        token = input("请输入JWT Token: ").strip()
        match_pair_id = input("请输入配对ID: ").strip()
    else:
        token = sys.argv[1]
        match_pair_id = int(sys.argv[2])
    
    asyncio.run(test_websocket(token, match_pair_id))

"""
WebSocket实时聊天端点
"""
import json
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from app.api.deps import get_db
from app.core.config import settings
from app.models.user import User
from app.models.chat_message import ChatMessage
from app.models.match_pair import MatchPair
from app.models.user_block import UserBlock
from app.core.safety import get_moderation_result
from app.core.risk import log_event

router = APIRouter()

# 存储活跃的WebSocket连接: {user_id: {match_pair_id: websocket}}
active_connections: Dict[int, Dict[int, WebSocket]] = {}


async def get_user_from_token(token: str, db: Session) -> User:
    """从WebSocket token中获取用户"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise ValueError("无效的token")
    except JWTError:
        raise ValueError("无法验证凭证")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise ValueError("用户不存在或已被禁用")
    return user


async def send_to_user(user_id: int, match_pair_id: int, message: dict):
    """向特定用户的特定配对发送消息"""
    if user_id in active_connections:
        if match_pair_id in active_connections[user_id]:
            try:
                await active_connections[user_id][match_pair_id].send_json(message)
            except Exception as e:
                print(f"发送消息失败: {e}")


@router.websocket("/ws/chat/{match_pair_id}")
async def websocket_chat(
    websocket: WebSocket,
    match_pair_id: int,
):
    """
    WebSocket聊天端点
    连接格式: ws://host/api/v1/ws/chat/{match_pair_id}?token=JWT_TOKEN
    """
    await websocket.accept()
    
    # 从查询参数获取token
    query_params = dict(websocket.query_params)
    token = query_params.get("token")
    
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="缺少token")
        return

    # 获取数据库会话
    from app.db.session import SessionLocal
    db = SessionLocal()
    current_user = None
    
    try:
        try:
            current_user = await get_user_from_token(token, db)
        except ValueError as e:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=str(e))
            db.close()
            return
        
        # 验证用户是否在该配对中
        pair = db.query(MatchPair).filter(MatchPair.id == match_pair_id).first()
        if not pair:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="配对不存在")
            return
        
        if current_user.id not in (pair.user1_id, pair.user2_id):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="无权访问此配对")
            return
        
        if pair.status != "active":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="配对已不可用")
            return
        
        # 获取对方用户ID
        other_user_id = pair.user1_id if pair.user2_id == current_user.id else pair.user2_id
        
        # 检查拉黑状态
        block = db.query(UserBlock).filter(
            ((UserBlock.blocker_id == current_user.id) & (UserBlock.blocked_id == other_user_id))
            | ((UserBlock.blocker_id == other_user_id) & (UserBlock.blocked_id == current_user.id))
        ).first()
        if block:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="已被拉黑")
            return
        
        # 注册连接
        if current_user.id not in active_connections:
            active_connections[current_user.id] = {}
        active_connections[current_user.id][match_pair_id] = websocket
        
        # 发送连接成功消息
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket连接成功",
            "match_pair_id": match_pair_id
        })
        
        # 监听消息
        while True:
            try:
                data = await websocket.receive_json()
                
                if data.get("type") == "message":
                    content = data.get("content", "").strip()
                    if not content:
                        await websocket.send_json({
                            "type": "error",
                            "message": "消息内容不能为空"
                        })
                        continue
                    
                    if len(content) > 1000:
                        await websocket.send_json({
                            "type": "error",
                            "message": "消息太长了，请控制在1000字以内"
                        })
                        continue
                    
                    # AI内容审核
                    moderation_result = get_moderation_result(content)
                    if moderation_result["should_block"]:
                        # 记录违规事件
                        log_event(
                            db,
                            user_id=current_user.id,
                            event_type="content_blocked",
                            match_pair_id=match_pair_id,
                            metadata={
                                "reason": moderation_result["message"],
                                "categories": moderation_result["categories"],
                                "risk_level": moderation_result["risk_level"],
                                "content_preview": content[:50],
                            },
                        )
                        db.commit()
                        
                        await websocket.send_json({
                            "type": "error",
                            "message": f"消息包含违规内容：{moderation_result['message']}"
                        })
                        continue
                    
                    # 保存消息到数据库
                    msg = ChatMessage(
                        match_pair_id=match_pair_id,
                        sender_user_id=current_user.id,
                        content=content,
                        is_read=False,
                    )
                    db.add(msg)
                    db.commit()
                    db.refresh(msg)
                    
                    # 构建消息对象
                    message_data = {
                        "type": "new_message",
                        "message": {
                            "id": msg.id,
                            "match_pair_id": msg.match_pair_id,
                            "sender_user_id": msg.sender_user_id,
                            "content": msg.content,
                            "is_read": msg.is_read,
                            "created_at": msg.created_at.isoformat(),
                            "is_me": False,
                            "from_me": False,
                        }
                    }
                    
                    # 发送给自己（确认发送成功）
                    await websocket.send_json({
                        "type": "new_message",
                        "message": {
                            **message_data["message"],
                            "is_me": True,
                            "from_me": True,
                        }
                    })
                    
                    # 发送给对方（如果对方在线）
                    await send_to_user(other_user_id, match_pair_id, message_data)
                    
                elif data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"处理消息错误: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"处理消息时出错: {str(e)}"
                })
                
    except Exception as e:
        print(f"WebSocket错误: {e}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass
    finally:
        # 清理连接
        if current_user and current_user.id in active_connections:
            if match_pair_id in active_connections[current_user.id]:
                del active_connections[current_user.id][match_pair_id]
            if not active_connections[current_user.id]:
                del active_connections[current_user.id]
        db.close()

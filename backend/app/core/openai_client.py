"""
OpenAI API 客户端封装
提供统一的AI对话接口，包括Token追踪、错误重试、模型降级等功能
"""
import os
import json
import time
from typing import Optional, List, Dict, Any
from openai import OpenAI
from fastapi import HTTPException, status
from app.core.config import settings


class OpenAIClient:
    """OpenAI API 客户端封装"""
    
    def __init__(self):
        api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 未配置，请在环境变量或配置文件中设置")
        
        # 创建 OpenAI 客户端，设置超时时间
        self.client = OpenAI(
            api_key=api_key,
            timeout=30.0,  # 30秒超时
            max_retries=2,  # 默认重试2次
        )
        self.model_gpt4o_mini = settings.OPENAI_MODEL_GPT4O_MINI  # 主要模型：成本低、速度快
        self.model_gpt4 = settings.OPENAI_MODEL_GPT4
        self.model_gpt35 = settings.OPENAI_MODEL_GPT35
        self.model_gpt4_turbo = settings.OPENAI_MODEL_GPT4_TURBO  # 核心功能使用
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_retries: int = 3,
        fallback_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        发送聊天请求到OpenAI API
        
        Args:
            messages: 对话消息列表，格式：[{"role": "user", "content": "..."}]
            model: 使用的模型（gpt-4/gpt-3.5-turbo）
            temperature: 温度参数（0-2）
            max_tokens: 最大输出token数
            max_retries: 最大重试次数
            fallback_model: 降级模型（如果主模型失败，使用此模型）
        
        Returns:
            {
                "content": "AI回复内容",
                "tokens_used": 使用的token数,
                "model": 实际使用的模型
            }
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=30.0,  # 设置30秒超时
                )
                
                content = response.choices[0].message.content
                tokens_used = response.usage.total_tokens
                actual_model = response.model
                
                return {
                    "content": content,
                    "tokens_used": tokens_used,
                    "model": actual_model,
                }
            
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # 打印详细错误信息用于调试
                print(f"[DEBUG] OpenAI API 错误 (尝试 {attempt + 1}/{max_retries}):")
                print(f"  错误类型: {type(e).__name__}")
                print(f"  错误信息: {str(e)}")
                if hasattr(e, 'response'):
                    print(f"  响应对象: {type(e.response)}")
                    if hasattr(e.response, 'status_code'):
                        print(f"  HTTP状态码: {e.response.status_code}")
                
                # 检查错误类型
                # OpenAI API 返回的错误格式可能是：
                # - 模型错误：'code': 'model_not_found'
                # - 配额错误：'code': 'insufficient_quota'
                # - 其他错误：网络、认证等
                is_model_error = False
                is_quota_error = False
                
                # 检查错误字符串（最常见的情况）
                if "model" in error_str:
                    if any(keyword in error_str for keyword in ["not found", "does not exist", "do not have access", "model_not_found", "does not exist or you do not have access"]):
                        is_model_error = True
                        print(f"  [检测到] 模型错误（字符串匹配）")
                
                # 检查 OpenAI API 错误对象（OpenAI Python SDK 的错误结构）
                if hasattr(e, 'response'):
                    try:
                        # 尝试获取响应体
                        error_data = {}
                        if hasattr(e.response, 'json'):
                            error_data = e.response.json()
                        elif hasattr(e.response, 'text'):
                            error_data = json.loads(e.response.text)
                        elif hasattr(e.response, 'body'):
                            error_data = json.loads(e.response.body) if isinstance(e.response.body, str) else e.response.body
                        
                        if error_data:
                            print(f"  错误数据: {error_data}")
                            # 检查错误代码
                            error_obj = error_data.get('error', {})
                            if isinstance(error_obj, dict):
                                error_code = error_obj.get('code')
                                error_type = error_obj.get('type')
                                
                                # 检查配额错误
                                if error_code == 'insufficient_quota' or error_type == 'insufficient_quota':
                                    is_quota_error = True
                                    print(f"  [检测到] 配额错误（code: insufficient_quota）")
                                # 检查模型错误
                                elif error_code == 'model_not_found':
                                    is_model_error = True
                                    print(f"  [检测到] 模型错误（code: model_not_found）")
                                elif error_type == 'invalid_request_error' and 'model' in error_str:
                                    is_model_error = True
                                    print(f"  [检测到] 模型错误（type: invalid_request_error）")
                    except Exception as parse_error:
                        print(f"  [WARNING] 解析错误响应失败: {parse_error}")
                
                # 检查 HTTP 状态码
                if hasattr(e, 'status_code'):
                    if e.status_code == 404:
                        is_model_error = True
                        print(f"  [检测到] 模型错误（HTTP 404）")
                    elif e.status_code == 429:
                        is_quota_error = True
                        print(f"  [检测到] 配额错误（HTTP 429）")
                elif hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                    if e.response.status_code == 404:
                        is_model_error = True
                        print(f"  [检测到] 模型错误（响应 HTTP 404）")
                    elif e.response.status_code == 429:
                        is_quota_error = True
                        print(f"  [检测到] 配额错误（响应 HTTP 429）")
                
                # 检查错误字符串中的配额信息
                if "quota" in error_str or "billing" in error_str or "exceeded" in error_str:
                    is_quota_error = True
                    print(f"  [检测到] 配额错误（字符串匹配）")
                
                # 如果是配额错误，直接抛出，不进行降级（因为这是账户问题，不是模型问题）
                if is_quota_error:
                    raise Exception(
                        f"OpenAI API配额不足：您的账户已超出当前使用配额。"
                        f"请检查您的OpenAI账户账单和使用限制。"
                        f"错误详情: {str(last_error)}"
                    )
                
                # 如果是模型错误，且配置了降级模型，立即降级（带重试）
                if is_model_error and fallback_model and model != fallback_model:
                    print(f"[WARNING] 模型 {model} 不可用，降级到 {fallback_model}")
                    
                    # 对降级模型进行重试（最多3次）
                    fallback_last_error = None
                    for fallback_attempt in range(3):
                        try:
                            print(f"[DEBUG] 降级尝试 {fallback_attempt + 1}/3，使用模型: {fallback_model}")
                            # 直接调用 OpenAI API，不再递归调用 chat_completion，避免无限递归
                            fallback_response = self.client.chat.completions.create(
                                model=fallback_model,
                                messages=messages,
                                temperature=temperature,
                                max_tokens=max_tokens,
                                timeout=30.0,  # 设置30秒超时
                            )
                            
                            content = fallback_response.choices[0].message.content
                            tokens_used = fallback_response.usage.total_tokens
                            actual_model = fallback_response.model
                            
                            print(f"[OK] 降级模型 {fallback_model} 调用成功")
                            return {
                                "content": content,
                                "tokens_used": tokens_used,
                                "model": actual_model,
                            }
                        except Exception as fallback_error:
                            fallback_last_error = fallback_error
                            fallback_error_str = str(fallback_error).lower()
                            
                            print(f"[DEBUG] 降级尝试 {fallback_attempt + 1}/3 失败: {type(fallback_error).__name__} - {str(fallback_error)[:200]}")
                            
                            # 检查错误类型
                            is_connection_error = any(keyword in fallback_error_str for keyword in [
                                "connection", "connect", "timeout", "network", 
                                "unreachable", "refused", "reset", "broken pipe"
                            ])
                            
                            is_fallback_model_error = (
                                "model" in fallback_error_str and 
                                any(keyword in fallback_error_str for keyword in ["not found", "does not exist", "do not have access", "model_not_found"])
                            )
                            
                            is_fallback_quota_error = (
                                "quota" in fallback_error_str or 
                                "billing" in fallback_error_str or 
                                "exceeded" in fallback_error_str or
                                "insufficient_quota" in fallback_error_str or
                                (hasattr(fallback_error, 'response') and 
                                 hasattr(fallback_error.response, 'status_code') and 
                                 fallback_error.response.status_code == 429)
                            )
                            
                            # 检查错误响应中的配额信息
                            if hasattr(fallback_error, 'response'):
                                try:
                                    if hasattr(fallback_error.response, 'json'):
                                        error_data = fallback_error.response.json()
                                        error_obj = error_data.get('error', {})
                                        if isinstance(error_obj, dict):
                                            if error_obj.get('code') == 'insufficient_quota':
                                                is_fallback_quota_error = True
                                except:
                                    pass
                            
                            # 如果是最后一次尝试，抛出错误
                            if fallback_attempt == 2:
                                if is_fallback_model_error:
                                    raise Exception(
                                        f"OpenAI API调用失败: 主模型 {model} 和降级模型 {fallback_model} 都不可用。"
                                        f"请检查API Key是否有访问这些模型的权限。"
                                        f"原始错误: {str(last_error)}"
                                    )
                                elif is_fallback_quota_error:
                                    raise Exception(
                                        f"OpenAI API调用失败: 主模型 {model} 不可用，降级到 {fallback_model} 时发现配额不足。"
                                        f"请检查您的OpenAI账户账单和使用限制。"
                                        f"错误详情: {str(fallback_last_error)}"
                                    )
                                elif is_connection_error:
                                    raise Exception(
                                        f"OpenAI API调用失败: 主模型 {model} 不可用，降级到 {fallback_model} 时遇到网络连接问题。"
                                        f"请检查网络连接或稍后重试。"
                                        f"连接错误: {str(fallback_last_error)}"
                                    )
                                else:
                                    raise Exception(
                                        f"OpenAI API调用失败: 主模型 {model} 不可用，降级到 {fallback_model} 时遇到错误: {str(fallback_last_error)}"
                                    )
                            
                            # 如果是连接错误，等待后重试
                            if is_connection_error:
                                wait_time = 2 * (fallback_attempt + 1)  # 2秒、4秒、6秒
                                print(f"[WARNING] 连接错误，等待 {wait_time} 秒后重试...")
                                time.sleep(wait_time)
                            elif is_fallback_quota_error:
                                # 配额错误，不重试，直接抛出
                                raise Exception(
                                    f"OpenAI API调用失败: 主模型 {model} 不可用，降级到 {fallback_model} 时发现配额不足。"
                                    f"请检查您的OpenAI账户账单和使用限制。"
                                    f"错误详情: {str(fallback_last_error)}"
                                )
                            else:
                                # 其他错误，等待后重试（可能是临时错误）
                                wait_time = 1 * (fallback_attempt + 1)  # 1秒、2秒、3秒
                                print(f"[WARNING] 降级失败，等待 {wait_time} 秒后重试...")
                                time.sleep(wait_time)
                    
                    # 如果所有降级尝试都失败（不应该到达这里，因为应该在循环内抛出异常）
                    raise Exception(f"降级模型 {fallback_model} 所有重试都失败: {str(fallback_last_error)}")
                
                # 注意：如果已经在上面处理了模型错误的降级，这里不应该再执行
                # 这个逻辑只处理非模型错误的情况
                if attempt == max_retries - 1 and fallback_model and model != fallback_model and not is_model_error:
                    print(f"[WARNING] 主模型 {model} 失败（非模型错误），尝试降级到 {fallback_model}")
                    try:
                        return self.chat_completion(
                            messages=messages,
                            model=fallback_model,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            max_retries=1,  # 降级模型只重试1次
                            fallback_model=None,  # 不再降级
                        )
                    except:
                        pass
                
                # 指数退避重试
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
        
        # 所有重试都失败
        raise Exception(f"OpenAI API调用失败（重试{max_retries}次）: {str(last_error)}")
    
    def get_system_prompt_for_user(
        self,
        user_id: int,
        user_profile: Optional[Dict] = None,
        recent_conversations: Optional[List[Dict]] = None,
        memory_summary: Optional[str] = None,  # 改为字符串（滚动摘要）
        conversation_type: str = "consultation",
        user_style_preference: Optional[str] = None,  # 用户风格偏好：活泼幽默/温柔知性/干练直接
    ) -> str:
        """
        为特定用户生成个性化的System Prompt
        
        Args:
            user_id: 用户ID
            user_profile: 用户基本信息
            recent_conversations: 最近对话历史
            memory_summary: 记忆摘要
        
        Returns:
            个性化的System Prompt字符串
        """
        prompt_parts = [
            "你是用户专属的AI红娘，名字叫'小缘'。",
            "你只服务这一个用户，要记住：",
            "",
        ]
        
        # 添加用户基本信息
        if user_profile:
            name = user_profile.get("display_name", "朋友")
            prompt_parts.append(f"- 用户的名字：{name}")
            if user_profile.get("age"):
                prompt_parts.append(f"- 用户的年龄：{user_profile.get('age')}岁")
            if user_profile.get("current_city"):
                prompt_parts.append(f"- 用户所在城市：{user_profile.get('current_city')}")
            if user_profile.get("occupation"):
                prompt_parts.append(f"- 用户的职业：{user_profile.get('occupation')}")
            prompt_parts.append("")
        
        # 添加滚动摘要（长期记忆）
        if memory_summary:
            prompt_parts.append("=== 用户档案（重要记忆）===")
            prompt_parts.append(memory_summary)
            prompt_parts.append("")
        
        # 性格适配
        style_instruction = "温暖亲切、专业但不死板"
        if user_style_preference:
            if "活泼" in user_style_preference or "幽默" in user_style_preference:
                style_instruction = "活泼幽默、轻松有趣，偶尔用emoji增加亲和力"
            elif "温柔" in user_style_preference or "知性" in user_style_preference:
                style_instruction = "温柔知性、细腻体贴，用词文雅"
            elif "干练" in user_style_preference or "直接" in user_style_preference:
                style_instruction = "干练直接、高效专业，少废话"
        
        prompt_parts.append(f"你的对话风格应该是：{style_instruction}。")
        prompt_parts.append("")
        
        # 根据对话类型添加特殊指令
        if conversation_type == "registration":
            prompt_parts.extend([
                "当前任务：注册引导对话",
                "",
                "重要：",
                "1. 用温暖、自然的语言与用户对话，像朋友一样聊天",
                "2. 根据用户的回答，自然地引出下一个话题",
                "3. 需要收集的信息包括：",
                "   - 基本信息：昵称、年龄、性别、所在城市、职业、学历",
                "   - 个人介绍：兴趣爱好、生活方式、价值观",
                "   - 择偶偏好：期望对象性别、年龄范围、结婚时间线",
                "4. 当你觉得已经收集到足够的信息时，主动总结并询问：",
                "   '我已经了解得差不多了，让我为你总结一下...（列出已收集的信息）'",
                "   '还有什么想补充的吗？如果没有，我就帮你保存资料了～'",
                "5. 如果用户说'差不多了'、'就这些'、'没有了'等，立即总结并确认保存",
                "6. 记住用户之前说过的话，让对话有连贯性",
            ])
        else:
            prompt_parts.extend([
                "任务：情感咨询和陪伴",
                "",
                "核心原则：",
                "1. 用温暖、自然的语言与用户对话，像朋友一样关心用户",
                "2. 懂得欲擒故纵：不要直接给答案，而是引导用户思考",
                "3. 根据用户的回答，自然地引出下一个话题",
                "4. 适时给予鼓励和肯定",
                "5. 记住用户之前说过的话，让对话有连贯性",
                "6. 能够分析用户情感状态，给出专业建议",
            ])
        
        # Few-Shot 示例（教会AI如何回答）
        prompt_parts.extend([
            "",
            "=== 回答示例（Few-Shot Learning）===",
            "",
            "示例1 - 用户说'没遇到合适的'：",
            "❌ 不好的回答：'哦，好的，继续加油。'",
            "✅ 好的回答：'别灰心呀（拍肩），缘分有时候就是这么来的。具体的哪里觉得不合适呢？是眼缘还是话题不投机？'",
            "",
            "示例2 - 用户说'不知道要不要继续聊'：",
            "❌ 不好的回答：'根据我的分析，建议你继续。'",
            "✅ 好的回答：'我理解你的犹豫。能告诉我，是什么让你觉得不确定吗？是聊天的感觉，还是其他方面？'",
            "",
            "示例3 - 用户说'最近工作很忙'：",
            "❌ 不好的回答：'工作重要，但也要注意感情。'",
            "✅ 好的回答：'工作确实重要，但感情也需要时间经营。你觉得是时间不够，还是对感情这件事本身有点疲惫？'",
            "",
            "关键技巧：",
            "- 不要只说'哦好的'、'继续加油'这种敷衍的话",
            "- 要引导话题，问具体的问题，让用户深入思考",
            "- 用emoji要适度，不要滥用（每3-5句话用1-2个）",
            "- 不要说出'作为一个AI语言模型...'这种出戏的话",
            "- 要像真正的红娘一样，有温度、有智慧",
        ])
        
        prompt_parts.extend([
            "",
            "边界设定：",
            "- 不提供医疗建议",
            "- 不提供法律建议",
            "- 不鼓励危险行为",
            "- 遇到严重心理问题时，建议寻求专业帮助",
        ])
        
        return "\n".join(prompt_parts)
    
    def build_conversation_messages(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        current_message: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        构建完整的对话消息列表（用于OpenAI API）
        
        Args:
            system_prompt: System提示词
            conversation_history: 历史对话列表
            current_message: 当前用户消息（可选）
        
        Returns:
            完整的消息列表
        """
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # 添加历史对话
        for conv in conversation_history:
            messages.append({
                "role": conv.get("role", "user"),
                "content": conv.get("content", "")
            })
        
        # 添加当前消息
        if current_message:
            messages.append({
                "role": "user",
                "content": current_message
            })
        
        return messages


# 全局单例
_openai_client: Optional[OpenAIClient] = None


def get_openai_client() -> OpenAIClient:
    """获取OpenAI客户端单例"""
    global _openai_client
    if _openai_client is None:
        try:
            _openai_client = OpenAIClient()
        except ValueError as e:
            # API Key 未配置时，抛出更友好的错误
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"AI服务配置错误：{str(e)}。请检查后端配置。"
            )
    return _openai_client
















from typing import List, Optional, Dict

from pydantic import BaseModel


class MatchInsightRequest(BaseModel):
    target_user_id: int


class MatchInsightResponse(BaseModel):
    explanation: str                 # 总体说明
    key_points: List[str]            # 匹配亮点（可选，AI分析时可能为空）
    suggested_openers: List[str]     # 建议的开场白
    safety_tips: List[str]           # 线下见面安全提示
    match_score_breakdown: Optional[Dict[str, float]] = None  # 多维度兼容性评分

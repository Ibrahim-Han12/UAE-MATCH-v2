"""
AI文本内容审核模块
检测诈骗、色情、赌博、毒品等敏感内容
"""
import re
from typing import Dict, List, Optional, Tuple
from enum import Enum


class ContentRiskLevel(str, Enum):
    """内容风险等级"""
    SAFE = "safe"  # 安全
    LOW = "low"  # 低风险
    MEDIUM = "medium"  # 中风险
    HIGH = "high"  # 高风险
    BLOCKED = "blocked"  # 需要阻止


class ContentCategory(str, Enum):
    """内容类别"""
    SCAM = "scam"  # 诈骗
    PORNOGRAPHY = "pornography"  # 色情
    GAMBLING = "gambling"  # 赌博
    DRUGS = "drugs"  # 毒品
    VIOLENCE = "violence"  # 暴力
    SPAM = "spam"  # 垃圾信息
    OTHER = "other"  # 其他


# 诈骗相关关键词
SCAM_KEYWORDS = [
    # 投资理财类
    "投资", "理财", "赚钱", "高收益", "稳赚", "包赚", "日赚", "月赚", "年赚",
    "刷单", "兼职", "代购", "代付", "充值", "返利", "提现", "套现",
    "贷款", "借款", "放贷", "利息", "本金", "保证金", "押金",
    "中奖", "抽奖", "免费", "领取", "红包", "转账", "汇款",
    # 敏感信息类
    "验证码", "密码", "账号", "银行卡", "身份证", "护照", "信用卡",
    # 联系方式类（引流）
    "加微信", "加我微信", "加QQ", "加我QQ", "私聊", "私下交易", "线下交易",
    "微信", "QQ", "联系方式", "加好友", "加v", "加V", "加微",
    "扫码", "二维码", "收款码", "付款码", "收款", "付款",
    # 虚拟货币类
    "比特币", "虚拟币", "数字货币", "区块链", "加密货币",
    # 其他诈骗相关
    "代理", "加盟", "招商", "推广", "拉人头", "发展下线",
    "快速", "轻松", "简单", "无风险", "保本",
]

# 色情相关关键词
PORNOGRAPHY_KEYWORDS = [
    # 约相关
    "约炮", "约吗", "约", "约不", "约一下", "约吗？", "约不约",
    "约p", "约P", "约pao", "约跑", "约pao吗",
    # 性相关
    "一夜情", "包养", "援交", "性服务", "特殊服务",
    "裸照", "裸体", "性爱", "做爱", "上床", "开房",
    "情趣", "成人", "色情", "黄色", "AV", "三级", "小电影",
    # 陪相关
    "陪睡", "陪玩", "陪聊", "陪酒", "陪游",
    # 其他
    "包夜", "过夜", "酒店", "宾馆", "开房", "开房吗",
    "上门", "服务", "特殊", "私密",
]

# 赌博相关关键词
GAMBLING_KEYWORDS = [
    "赌博", "赌场", "博彩", "下注", "押注", "投注",
    "彩票", "六合彩", "体彩", "福彩", "竞彩",
    "老虎机", "轮盘", "百家乐", "21点", "德州扑克",
    "赌球", "赌马", "赌钱", "赢钱", "输钱",
]

# 毒品相关关键词
DRUGS_KEYWORDS = [
    "毒品", "吸毒", "大麻", "可卡因", "海洛因", "冰毒",
    "摇头丸", "K粉", "白粉", "麻古", "摇头",
    "吸毒", "贩毒", "制毒", "毒品交易",
]

# 暴力相关关键词
VIOLENCE_KEYWORDS = [
    "杀人", "砍人", "打人", "暴力", "威胁", "恐吓",
    "报复", "报仇", "伤害", "攻击", "打死", "弄死",
    "砍死", "杀你", "弄你", "搞你",
]

# 垃圾信息关键词
SPAM_KEYWORDS = [
    "广告", "推广", "营销", "代理", "加盟", "招商",
    "加群", "进群", "微信群", "QQ群", "拉群", "扫码进群",
    "关注", "订阅", "点赞", "转发",
]


def detect_content_risk(text: str) -> Tuple[ContentRiskLevel, List[ContentCategory], Dict]:
    """
    检测文本内容风险
    
    Args:
        text: 待检测的文本内容
        
    Returns:
        (风险等级, 检测到的类别列表, 详细信息)
    """
    if not text or not text.strip():
        return ContentRiskLevel.SAFE, [], {}
    
    text_lower = text.lower()
    detected_categories = []
    category_scores = {}
    details = {}
    
    # 检测各类别
    scam_matches = _check_keywords(text_lower, SCAM_KEYWORDS)
    if scam_matches:
        detected_categories.append(ContentCategory.SCAM)
        category_scores[ContentCategory.SCAM] = len(scam_matches)
        details["scam_keywords"] = scam_matches
    
    porn_matches = _check_keywords(text_lower, PORNOGRAPHY_KEYWORDS)
    if porn_matches:
        detected_categories.append(ContentCategory.PORNOGRAPHY)
        category_scores[ContentCategory.PORNOGRAPHY] = len(porn_matches)
        details["pornography_keywords"] = porn_matches
    
    gambling_matches = _check_keywords(text_lower, GAMBLING_KEYWORDS)
    if gambling_matches:
        detected_categories.append(ContentCategory.GAMBLING)
        category_scores[ContentCategory.GAMBLING] = len(gambling_matches)
        details["gambling_keywords"] = gambling_matches
    
    drugs_matches = _check_keywords(text_lower, DRUGS_KEYWORDS)
    if drugs_matches:
        detected_categories.append(ContentCategory.DRUGS)
        category_scores[ContentCategory.DRUGS] = len(drugs_matches)
        details["drugs_keywords"] = drugs_matches
    
    violence_matches = _check_keywords(text_lower, VIOLENCE_KEYWORDS)
    if violence_matches:
        detected_categories.append(ContentCategory.VIOLENCE)
        category_scores[ContentCategory.VIOLENCE] = len(violence_matches)
        details["violence_keywords"] = violence_matches
    
    spam_matches = _check_keywords(text_lower, SPAM_KEYWORDS)
    if spam_matches:
        detected_categories.append(ContentCategory.SPAM)
        category_scores[ContentCategory.SPAM] = len(spam_matches)
        details["spam_keywords"] = spam_matches
    
    # 检测高风险模式（如包含联系方式+诈骗关键词）
    if _detect_high_risk_patterns(text_lower):
        detected_categories.append(ContentCategory.SCAM)
        details["high_risk_pattern"] = True
    
    # 根据检测结果确定风险等级
    if not detected_categories:
        return ContentRiskLevel.SAFE, [], {}
    
    # 计算总风险分数
    total_score = sum(category_scores.values())
    
    # 高风险类别（毒品、色情、暴力）直接判定为高风险
    high_risk_categories = [ContentCategory.DRUGS, ContentCategory.PORNOGRAPHY, ContentCategory.VIOLENCE]
    if any(cat in detected_categories for cat in high_risk_categories):
        return ContentRiskLevel.BLOCKED, detected_categories, details
    
    # 诈骗类别：更严格的判断
    if ContentCategory.SCAM in detected_categories:
        # 如果包含联系方式（high_risk_pattern），直接阻止
        if details.get("high_risk_pattern"):
            return ContentRiskLevel.BLOCKED, detected_categories, details
        # 如果匹配到2个或以上诈骗关键词，阻止
        if total_score >= 2:
            return ContentRiskLevel.BLOCKED, detected_categories, details
        # 即使只有1个关键词，也标记为高风险（需要阻止）
        return ContentRiskLevel.BLOCKED, detected_categories, details
    
    # 赌博类别
    if ContentCategory.GAMBLING in detected_categories:
        if total_score >= 2:
            return ContentRiskLevel.HIGH, detected_categories, details
        else:
            return ContentRiskLevel.MEDIUM, detected_categories, details
    
    # 垃圾信息
    if ContentCategory.SPAM in detected_categories:
        if total_score >= 3:
            return ContentRiskLevel.MEDIUM, detected_categories, details
        else:
            return ContentRiskLevel.LOW, detected_categories, details
    
    # 默认中等风险
    return ContentRiskLevel.MEDIUM, detected_categories, details


def _check_keywords(text: str, keywords: List[str]) -> List[str]:
    """检查文本中是否包含关键词（支持部分匹配和变体）"""
    matches = []
    text_lower = text.lower()
    
    for keyword in keywords:
        keyword_lower = keyword.lower()
        # 直接包含检查
        if keyword_lower in text_lower:
            matches.append(keyword)
        # 处理一些常见变体
        elif keyword_lower == "约" and ("约吗" in text_lower or "约不" in text_lower or "约一下" in text_lower):
            matches.append(keyword)
        elif keyword_lower == "加微信" and ("加我微信" in text_lower or "加微信" in text_lower or "微信加" in text_lower):
            matches.append(keyword)
        elif keyword_lower == "加我微信" and ("加我微信" in text_lower or "加微信" in text_lower):
            matches.append(keyword)
    
    return matches


def _detect_high_risk_patterns(text: str) -> bool:
    """检测高风险模式"""
    text_lower = text.lower()
    
    # 模式1: 联系方式（更严格的检测）
    contact_patterns = [
        r'微信[：:：]\s*\w+',
        r'加.*微信',
        r'加我.*微信',
        r'微信.*加',
        r'qq[：:：]\s*\d+',
        r'加.*qq',
        r'电话[：:：]\s*[\d\-]+',
        r'手机[：:：]\s*[\d\-]+',
        r'联系方式',
        r'加好友',
        r'加v',
        r'加V',
        r'扫码',
        r'二维码',
    ]
    
    # 诈骗关键词（扩展）
    scam_indicators = [
        '投资', '赚钱', '理财', '刷单', '兼职', '代购', '返利',
        '中奖', '免费', '领取', '红包', '转账', '汇款',
        '贷款', '借款', '高收益', '稳赚',
    ]
    
    has_contact = any(re.search(pattern, text_lower, re.IGNORECASE) for pattern in contact_patterns)
    has_scam = any(indicator in text_lower for indicator in scam_indicators)
    
    # 如果包含联系方式，即使没有明确的诈骗关键词，也视为高风险（防止引流）
    if has_contact:
        return True
    
    if has_contact and has_scam:
        return True
    
    # 模式2: 多个高风险关键词组合
    high_risk_combos = [
        (['转账', '汇款'], ['验证码', '密码']),
        (['免费', '领取'], ['中奖', '抽奖']),
        (['加', '微信'], ['赚钱', '投资', '兼职']),
    ]
    
    for combo in high_risk_combos:
        if all(any(kw in text_lower for kw in group) for group in combo):
            return True
    
    return False


def should_block_content(risk_level: ContentRiskLevel) -> bool:
    """判断是否应该阻止内容"""
    return risk_level in [ContentRiskLevel.BLOCKED, ContentRiskLevel.HIGH]


def get_moderation_result(text: str) -> Dict:
    """
    获取内容审核结果（供API使用）
    
    Returns:
        {
            "risk_level": "safe|low|medium|high|blocked",
            "categories": ["scam", "pornography", ...],
            "should_block": bool,
            "details": {...},
            "message": str
        }
    """
    risk_level, categories, details = detect_content_risk(text)
    should_block = should_block_content(risk_level)
    
    messages = {
        ContentRiskLevel.SAFE: "内容安全",
        ContentRiskLevel.LOW: "内容包含低风险内容，请注意",
        ContentRiskLevel.MEDIUM: "内容包含中等风险内容，请谨慎",
        ContentRiskLevel.HIGH: "内容包含高风险内容，已被阻止",
        ContentRiskLevel.BLOCKED: "内容包含违规信息，已被阻止",
    }
    
    return {
        "risk_level": risk_level.value,
        "categories": [cat.value for cat in categories],
        "should_block": should_block,
        "details": details,
        "message": messages.get(risk_level, "内容审核完成"),
    }

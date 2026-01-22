"""
AI文本审核功能测试脚本
使用方法: python test_moderation.py
"""
from app.core.safety import get_moderation_result, ContentRiskLevel

def test_moderation(text: str):
    """测试文本审核"""
    result = get_moderation_result(text)
    
    print(f"测试文本: {text}")
    print("-" * 60)
    print(f"风险等级: {result['risk_level']}")
    print(f"检测类别: {', '.join(result['categories']) if result['categories'] else '无'}")
    print(f"是否阻止: {'是' if result['should_block'] else '否'}")
    print(f"提示信息: {result['message']}")
    if result['details']:
        print(f"详细信息: {result['details']}")
    print("=" * 60)


if __name__ == "__main__":
    print("=" * 60)
    print("AI文本审核功能测试")
    print("=" * 60)
    
    # 测试用例
    test_cases = [
        ("你好，很高兴认识你", "正常消息"),
        ("加我微信，一起投资赚钱", "诈骗关键词"),
        ("刷单兼职，日赚500", "诈骗关键词"),
        ("约炮吗", "色情关键词"),
        ("一起赌博吧", "赌博关键词"),
        ("要不要试试毒品", "毒品关键词"),
        ("我不喜欢赌博，觉得不好", "包含关键词但上下文正常"),
        ("投资理财需要谨慎", "包含关键词但上下文正常"),
        ("免费领取中奖红包，加我微信", "高风险组合"),
    ]
    
    for text, description in test_cases:
        print(f"\n【{description}】")
        test_moderation(text)
        print()

"""
测试风控功能
"""
from app.core.safety import get_moderation_result

test_cases = [
    "约吗",
    "加我微信",
    "加微信",
    "约炮",
    "投资赚钱",
    "加我微信一起赚钱",
    "你好，很高兴认识你",
    "约吗？",
    "加我微信吧",
]

print("=" * 60)
print("风控功能测试")
print("=" * 60)

for text in test_cases:
    result = get_moderation_result(text)
    status = "[阻止]" if result["should_block"] else "[通过]"
    print(f"\n测试文本: {text}")
    print(f"  状态: {status}")
    print(f"  风险等级: {result['risk_level']}")
    print(f"  检测类别: {', '.join(result['categories']) if result['categories'] else '无'}")
    print(f"  提示: {result['message']}")

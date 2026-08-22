"""开发期状态推进工具：把某个测试账号沿真实状态机推到指定状态。

用途：产品负责人在深访没聊满 25 项时，也要能看到下游页面（核验 / 付费墙 / 主应用）
长什么样。这是**开发期查看工具，不是产品后门**——它只存在于 scripts/，前端与 API
都无法触达，因此不违反"三道闸顺序不可跳"（PRD 2.2）与 DEC-028。

它走 state_machine.transition() 逐级跃迁，而不是直接改 users.status：
每一步都受合法性校验，且在 user_state_transitions 留痕（source=dev_tool），
所以事后能看出这条链是人工推的，不会被误当成真实漏斗数据。

用法（在 backend/ 目录下）：
    python -m scripts.dev_set_state --phone 0559876543 --to S3
    python -m scripts.dev_set_state --user-id 30 --to S4
    python -m scripts.dev_set_state --phone 0559876543 --show
"""
import argparse
import sys

from app.core import state_machine as sm
from app.db.session import SessionLocal
from app.models.user import User

# 正向链路（三道闸）。反向降级不在本工具范围内。
FORWARD = [sm.S1, sm.S2, sm.S3, sm.S4, sm.S5]

SCREEN = {
    sm.S1: "深访页",
    sm.S2: "身份核验页",
    sm.S3: "候补池 / 会员开通页（付费墙）",
    sm.S4: "主应用（推荐 / 消息 / 通知 / 我的）",
    sm.S5: "主应用（配对中）",
}


def _normalize_phone(raw: str) -> list:
    """返回几种可能的存储形态，避免因 +971 前缀写法不同而找不到人。"""
    digits = raw.lstrip("+").lstrip("0")
    return [raw, "+" + digits, "+971" + raw.lstrip("0"), "0" + digits]


def _find_user(db, phone: str = None, user_id: int = None) -> User:
    if user_id:
        u = db.query(User).filter_by(id=user_id).first()
        if u is None:
            sys.exit(f"找不到 user_id={user_id}")
        return u
    for cand in _normalize_phone(phone):
        u = db.query(User).filter_by(phone=cand).first()
        if u is not None:
            return u
    sys.exit(f"找不到手机号 {phone} 对应的账号（试过 {_normalize_phone(phone)}）")


def main() -> None:
    ap = argparse.ArgumentParser(description="开发期把测试账号推到指定状态")
    ap.add_argument("--phone")
    ap.add_argument("--user-id", type=int)
    ap.add_argument("--to", help="目标状态，如 S2 / S3 / S4")
    ap.add_argument("--show", action="store_true", help="只看当前状态，不改")
    args = ap.parse_args()

    if not args.phone and not args.user_id:
        sys.exit("要么给 --phone，要么给 --user-id")

    db = SessionLocal()
    try:
        user = _find_user(db, args.phone, args.user_id)
        current = sm.effective_state(user)
        print(f"账号 id={user.id} phone={user.phone} 当前状态 {current}"
              f"（{SCREEN.get(current, '?')}）")

        if args.show or not args.to:
            return

        target = args.to.upper()
        if target not in FORWARD:
            sys.exit(f"本工具只支持推进到 {FORWARD} 之一，收到 {target}")
        if FORWARD.index(target) <= FORWARD.index(current):
            sys.exit(f"{current} → {target} 不是前进方向；本工具不做降级")

        for nxt in FORWARD[FORWARD.index(current) + 1: FORWARD.index(target) + 1]:
            sm.transition(db, user, nxt, reason="dev_tool_forced", source="dev_tool")
            print(f"  → {nxt}（{SCREEN[nxt]}）")
        db.commit()
        print(f"完成。刷新前端即可看到「{SCREEN[target]}」。")
        print("提示：真实漏斗数据里这几条留痕的 source=dev_tool，可据此排除。")
    finally:
        db.close()


if __name__ == "__main__":
    main()

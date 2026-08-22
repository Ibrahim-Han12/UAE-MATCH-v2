"""
推荐信用户端点（BR-301, BR-303 / PRD 6.2-6.5）。

付费墙（DEC-004）：查看详情与回应需 S4；S3 只见 teaser。
三动作（PRD 6.3）：愿意认识 / 想再了解(延48h一次) / 这次不合适(强制结构化理由)。
双方接受 → 建 MatchPair + S4→S5 + 通知（永不披露被谁拒绝及理由）。
"""
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.api.deps import get_db, get_current_active_user, require_state
from app.core import notify
from app.core import photos as photo_display
from app.core import state_machine as sm
from app.core.matching.config import load as load_matching_config
from app.core.memory import writer as memory_writer
from app.core.risk import log_event
from app.models.user import User
from app.models.reco_pair import RecoPair
from app.models.match_pair import MatchPair
from app.models.profile import UserProfile

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

DECLINE_REASONS = ("timeline_mismatch", "lifestyle_difference", "appearance_preference", "other")


def _my_side(pair: RecoPair, user_id: int) -> Optional[str]:
    if pair.user_low_id == user_id:
        return "low"
    if pair.user_high_id == user_id:
        return "high"
    return None


def _letter_view(pair: RecoPair, side: str, db: Optional[Session] = None) -> dict:
    letter = pair.letter_for_low if side == "low" else pair.letter_for_high
    other_id = pair.user_high_id if side == "low" else pair.user_low_id
    my_response = pair.response_low if side == "low" else pair.response_high
    # 照片在推荐理由之后展示（PRD 6.2）；只给过审照片，没有则为 None 由前端给空态
    photo_url = photo_display.primary_photo_url(db, other_id) if db is not None else None
    return {
        "reco_pair_id": pair.id, "batch_id": pair.batch_id,
        "status": pair.status, "letter": letter,
        "target_user_id": other_id,
        "target_photo_url": photo_url,
        "my_response": my_response,
        "delivered_at": pair.delivered_at, "expires_at": pair.expires_at,
    }


@router.get("")
def list_my_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """我的推荐信列表。S3 候补只返回 teaser 计数（付费墙）。"""
    pairs = (
        db.query(RecoPair)
        .filter(or_(RecoPair.user_low_id == current_user.id,
                    RecoPair.user_high_id == current_user.id),
                RecoPair.status.in_(("delivered", "matched", "closed", "expired")))
        .order_by(RecoPair.delivered_at.desc())
        .all()
    )
    state = sm.effective_state(current_user)
    if state not in ("S4", "S5"):
        active = [p for p in pairs if p.status == "delivered"]
        return {"paywalled": True, "teaser_count": len(active),
                "message": "有人想认识你——开通会员即可查看与回应"}
    return {"paywalled": False,
            "items": [_letter_view(p, _my_side(p, current_user.id), db) for p in pairs]}


@router.get("/{pair_id}")
def get_recommendation(
    pair_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_state("S4")),
) -> Any:
    pair = db.query(RecoPair).filter_by(id=pair_id).first()
    side = _my_side(pair, current_user.id) if pair else None
    if pair is None or side is None or pair.status not in ("delivered", "matched", "closed", "expired"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="推荐不存在")
    log_event(db, user_id=current_user.id, event_type="reco_viewed",
              metadata={"reco_pair_id": pair.id})
    db.commit()
    return _letter_view(pair, side, db)


class RespondIn(BaseModel):
    action: str                       # accept / more_info / decline
    note: Optional[str] = None        # accept 可附一句话
    decline_reason: Optional[str] = None   # decline 必填（结构化理由）


@router.post("/{pair_id}/respond")
def respond(
    pair_id: int,
    body: RespondIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_state("S4")),
) -> Any:
    pair = db.query(RecoPair).filter_by(id=pair_id).first()
    side = _my_side(pair, current_user.id) if pair else None
    if pair is None or side is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="推荐不存在")
    if pair.status != "delivered":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该推荐已关闭或已处理")
    if pair.expires_at and pair.expires_at.replace(tzinfo=None) < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该推荐已超时关闭")
    my_resp = pair.response_low if side == "low" else pair.response_high
    if my_resp in ("accept", "decline"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="你已回应过本次推荐")

    other_id = pair.user_high_id if side == "low" else pair.user_low_id

    if body.action == "more_info":
        # 想再了解：时限自动延长 48h，仅一次（PRD 6.3）；追问咨询走小缘会话
        if pair.more_info_extended >= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="时限已延长过一次")
        cfg = load_matching_config()
        pair.expires_at = pair.expires_at + timedelta(hours=cfg["allocation"]["more_info_extension_hours"])
        pair.more_info_extended = 1
        setattr(pair, f"response_{side}", "more_info")
        log_event(db, user_id=current_user.id, event_type="reco_more_info",
                  metadata={"reco_pair_id": pair.id})
        db.commit()
        return {"message": "已为你延长 48 小时，可向小缘追问对方情况", "expires_at": pair.expires_at}

    if body.action == "decline":
        if body.decline_reason not in DECLINE_REASONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "reason_required", "options": DECLINE_REASONS,
                        "message": "请选择不合适的原因（用于改进推荐，不会告知对方）"},
            )
        setattr(pair, f"response_{side}", "decline")
        setattr(pair, f"decline_reason_{side}", body.decline_reason)
        pair.status = "closed"
        # 理由回流事件层（匹配模型迭代养料，BR-303, BR-304）
        memory_writer.append_event(db, current_user.id, "reco_declined",
                                   payload={"reco_pair_id": pair.id, "reason": body.decline_reason})
        log_event(db, user_id=current_user.id, event_type="reco_declined",
                  metadata={"reco_pair_id": pair.id, "reason": body.decline_reason})
        # 对方仅收到脱敏通知（永不披露被谁拒绝及理由，PRD 6.3）
        notify.send(db, other_id, type="reco_closed",
                    title="本次未配对成功",
                    body="小缘已在为你物色下一位。", payload={"reco_pair_id": pair.id})
        db.commit()
        return {"message": "已记录。小缘会参考你的反馈优化下次推荐"}

    if body.action == "accept":
        setattr(pair, f"response_{side}", "accept")
        memory_writer.append_event(db, current_user.id, "reco_accepted",
                                   payload={"reco_pair_id": pair.id, "note": body.note})
        log_event(db, user_id=current_user.id, event_type="reco_accepted",
                  metadata={"reco_pair_id": pair.id})
        other_resp = pair.response_high if side == "low" else pair.response_low

        if other_resp == "accept":
            # 双方接受 → 配对（PRD 6.3）
            pair.status = "matched"
            lo, hi = pair.user_low_id, pair.user_high_id
            mp = db.query(MatchPair).filter_by(user1_id=lo, user2_id=hi).first()
            if mp is None:
                mp = MatchPair(user1_id=lo, user2_id=hi, status="active")
                db.add(mp)
                db.flush()
            for uid in (lo, hi):
                u = db.query(User).filter_by(id=uid).first()
                if u is not None and sm.effective_state(u) == sm.S4:
                    sm.transition(db, u, sm.S5, reason="match_created")
                notify.send(db, uid, type="match_created",
                            title="恭喜，你们互相愿意认识！",
                            body="可以开始聊天了，小缘已为你准备了破冰建议。",
                            payload={"match_pair_id": mp.id},
                            channels=["inapp", "push", "email"])
                log_event(db, user_id=uid, event_type="match_created",
                          metadata={"match_pair_id": mp.id, "reco_pair_id": pair.id})
            db.commit()
            return {"message": "配对成功！可以开始聊天了", "matched": True, "match_pair_id": mp.id}

        db.commit()
        return {"message": "已表达愿意认识，等待对方回应", "matched": False}

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="action 须为 accept / more_info / decline")


# ===== 画像速写确认（PRD 6.5：未确认不进他人推荐）=====

@router.post("/sketch/confirm")
def confirm_sketch(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """确认"对方视角的画像速写"。进入候补池（可被推荐）的前置。"""
    profile = db.query(UserProfile).filter_by(user_id=current_user.id).first()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先完成深访")
    from app.core.interview.report import get_latest_report
    report = get_latest_report(db, current_user.id)
    if report is None or not (report.sections or {}).get("sketch"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="画像速写尚未生成")
    profile.sketch_confirmed_at = datetime.utcnow()
    log_event(db, user_id=current_user.id, event_type="sketch_confirmed", metadata={})
    db.commit()
    return {"message": "已确认，你的画像速写将用于向合适的人介绍你", "sketch": report.sections["sketch"]}

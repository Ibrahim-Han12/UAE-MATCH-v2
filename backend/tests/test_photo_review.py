"""照片人工审核（BR-101/102 · DEC-002 种子期人工核验）。

这是三道闸第二道的最后一环：没有审核动作，任何用户的照片都永远停在 pending，
S2→S3 永远不通 —— 实测中产品负责人就卡在这里。
"""
import pytest

from app.core import photo_review
from app.core import state_machine as sm
from app.models.kyc_result import KycResult
from app.models.user import User
from app.models.user_photo import UserPhoto


def _user(db, status=sm.S2, phone="+971500000001"):
    u = User(email=f"{phone}@t.local", hashed_password="x", status=status, is_active=True)
    db.add(u)
    db.flush()
    return u


def _photo(db, user_id, status="pending", order=0):
    p = UserPhoto(user_id=user_id, file_path=f"/p/{user_id}_{order}.jpg",
                  file_url=f"/photos/file/{user_id}_{order}.jpg", status=status,
                  display_order=order)
    db.add(p)
    db.flush()
    return p


def _passed_kyc(db, user_id):
    db.add(KycResult(user_id=user_id, provider="mock", transaction_id=f"tx{user_id}",
                     result="passed"))
    db.flush()


def test_queue_returns_only_pending_oldest_first(db):
    u = _user(db)
    first = _photo(db, u.id, order=0)
    second = _photo(db, u.id, order=1)
    _photo(db, u.id, status="approved", order=2)
    _photo(db, u.id, status="rejected", order=3)

    queue = photo_review.pending_queue(db)

    assert [p.id for p in queue] == [first.id, second.id]


def test_approve_marks_photo_approved(db):
    u = _user(db)
    p = _photo(db, u.id)

    result = photo_review.review(db, p, action="approve", admin_id=1)

    assert p.status == "approved"
    assert result["status"] == "approved"


def test_approve_promotes_to_candidate_pool_when_kyc_passed(db):
    """过审是 S2→S3 的最后一块拼图（kyc.py 的注释说这里会调用，但此前调用点不存在）。"""
    u = _user(db, status=sm.S2)
    _passed_kyc(db, u.id)
    p = _photo(db, u.id)

    result = photo_review.review(db, p, action="approve", admin_id=1)

    assert result["promoted"] is True
    assert sm.effective_state(u) == sm.S3


def test_approve_does_not_promote_without_kyc(db):
    """KYC 没过就不能进候补池——三道闸缺一不可。"""
    u = _user(db, status=sm.S2)
    p = _photo(db, u.id)

    result = photo_review.review(db, p, action="approve", admin_id=1)

    assert result["promoted"] is False
    assert sm.effective_state(u) == sm.S2


def test_reject_records_reason(db):
    u = _user(db)
    p = _photo(db, u.id)

    photo_review.review(db, p, action="reject", reason="不是本人正脸", admin_id=1)

    assert p.status == "rejected"
    assert p.rejection_reason == "不是本人正脸"


def test_reject_requires_a_reason(db):
    """打回必须给理由——用户要知道重拍什么，否则只能反复瞎试。"""
    u = _user(db)
    p = _photo(db, u.id)

    with pytest.raises(ValueError):
        photo_review.review(db, p, action="reject", admin_id=1)

    assert p.status == "pending"


def test_reject_never_promotes(db):
    u = _user(db, status=sm.S2)
    _passed_kyc(db, u.id)
    p = _photo(db, u.id)

    result = photo_review.review(db, p, action="reject", reason="模糊", admin_id=1)

    assert result["promoted"] is False
    assert sm.effective_state(u) == sm.S2


def test_unknown_action_is_rejected(db):
    u = _user(db)
    p = _photo(db, u.id)

    with pytest.raises(ValueError):
        photo_review.review(db, p, action="maybe", admin_id=1)


def test_already_reviewed_photo_cannot_be_reviewed_again(db):
    """幂等保护：避免重复过审重复触发升级与埋点。"""
    u = _user(db)
    p = _photo(db, u.id, status="approved")

    with pytest.raises(ValueError):
        photo_review.review(db, p, action="reject", reason="改主意了", admin_id=1)

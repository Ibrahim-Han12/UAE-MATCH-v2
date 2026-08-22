"""照片展示口径：只展示过审照片（BR-101/102）。

推荐信里"先理由后照片"（PRD 6.2）要展示的那张必须是**人工过审过的**——
否则等于绕过第二道闸：谁都能上传一张陌生人照片直接出现在别人的推荐信里。
"""
from app.core import photos as photo_display
from app.models.user import User
from app.models.user_photo import UserPhoto


def _user(db, tag="a"):
    u = User(email=f"{tag}@t.local", hashed_password="x", status="S4", is_active=True)
    db.add(u)
    db.flush()
    return u


def _photo(db, user_id, status="approved", order=0, primary=False):
    p = UserPhoto(user_id=user_id, file_path=f"/p/{order}.jpg",
                  file_url=f"/photos/file/{user_id}_{order}.jpg",
                  status=status, display_order=order, is_primary=primary)
    db.add(p)
    db.flush()
    return p


def test_no_photos_returns_none(db):
    u = _user(db)

    assert photo_display.primary_photo_url(db, u.id) is None


def test_pending_photos_are_never_shown(db):
    """核验未过的照片绝不展示——否则第二道闸形同虚设。"""
    u = _user(db)
    _photo(db, u.id, status="pending", primary=True)

    assert photo_display.primary_photo_url(db, u.id) is None


def test_rejected_photos_are_never_shown(db):
    u = _user(db)
    _photo(db, u.id, status="rejected", primary=True)

    assert photo_display.primary_photo_url(db, u.id) is None


def test_approved_primary_is_returned(db):
    u = _user(db)
    _photo(db, u.id, status="approved", order=1, primary=True)

    url = photo_display.primary_photo_url(db, u.id)

    assert url is not None and url.endswith("_1.jpg")


def test_falls_back_to_lowest_order_when_no_primary_flag(db):
    u = _user(db)
    _photo(db, u.id, status="approved", order=2)
    _photo(db, u.id, status="approved", order=0)

    url = photo_display.primary_photo_url(db, u.id)

    assert url.endswith("_0.jpg")


def test_primary_flag_wins_over_order(db):
    u = _user(db)
    _photo(db, u.id, status="approved", order=0)
    _photo(db, u.id, status="approved", order=3, primary=True)

    url = photo_display.primary_photo_url(db, u.id)

    assert url.endswith("_3.jpg")


def test_ensure_primary_marks_first_photo(db):
    """首张上传自动成为主图，用户不必先懂"主图"这个概念。"""
    u = _user(db)
    p = _photo(db, u.id, status="pending", order=0)

    photo_display.ensure_primary(db, u.id)

    assert p.is_primary is True


def test_ensure_primary_does_not_override_existing_choice(db):
    u = _user(db)
    chosen = _photo(db, u.id, status="approved", order=0, primary=True)
    later = _photo(db, u.id, status="pending", order=1)

    photo_display.ensure_primary(db, u.id)

    assert chosen.is_primary is True
    assert later.is_primary is False


def test_ensure_primary_ignores_rejected_photos(db):
    """被打回的照片不该成为主图。"""
    u = _user(db)
    rejected = _photo(db, u.id, status="rejected", order=0)
    ok = _photo(db, u.id, status="pending", order=1)

    photo_display.ensure_primary(db, u.id)

    assert rejected.is_primary is False
    assert ok.is_primary is True

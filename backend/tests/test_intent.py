"""意图层：每轮一次 mini 分类，取代关键词 if-else（hld-dialogue-system.md §2）。"""
from app.core.dialogue import intent


def test_keyword_fallback_detects_explicit_stop():
    got = intent.classify_by_keyword("今天不聊了，改天吧")

    assert got.kind == "stop"
    assert got.source == "keyword_fallback"


def test_keyword_fallback_detects_proceed_not_stop():
    """真人测试 round 4 的缺陷：想前进被当成想停止。"""
    got = intent.classify_by_keyword("我还差多少能进下一步？")

    assert got.kind == "proceed"


def test_keyword_fallback_defaults_to_answer():
    got = intent.classify_by_keyword("我来迪拜六年了，在 DIFC 做 audit")

    assert got.kind == "answer"


def test_stop_wins_over_proceed():
    """“不聊了，跳过吧”同时命中两个词表，停止意愿更强。"""
    got = intent.classify_by_keyword("不聊了，跳过吧")

    assert got.kind == "stop"


def test_model_classification_carries_target_field(monkeypatch):
    """refusal_field 必须带 field_id，否则编排器不知道拒的是哪一题。"""
    class FakeGateway:
        def chat(self, db, **kw):
            return {"content": '{"intent":"refusal_field","field_id":"A7","confidence":0.91}',
                    "tokens_used": 12, "model": "fake-mini"}

    monkeypatch.setattr(intent, "get_ai_gateway", lambda: FakeGateway())

    got = intent.classify(db=None, user_id=1, message="这个不想说", current_field_id="A7")

    assert got.kind == "refusal_field"
    assert got.field_id == "A7"
    assert got.source == "model"


def test_unparsable_model_output_falls_back_to_keywords(monkeypatch):
    """分类失败不能让整轮对话挂掉。"""
    class BrokenGateway:
        def chat(self, db, **kw):
            return {"content": "抱歉我不太确定", "tokens_used": 5, "model": "fake-mini"}

    monkeypatch.setattr(intent, "get_ai_gateway", lambda: BrokenGateway())

    got = intent.classify(db=None, user_id=1, message="不聊了", current_field_id=None)

    assert got.kind == "stop"
    assert got.source == "keyword_fallback"


def test_gateway_exception_falls_back_to_keywords(monkeypatch):
    class ExplodingGateway:
        def chat(self, db, **kw):
            raise RuntimeError("upstream 503")

    monkeypatch.setattr(intent, "get_ai_gateway", lambda: ExplodingGateway())

    got = intent.classify(db=None, user_id=1, message="我住阿布扎比", current_field_id=None)

    assert got.kind == "answer"
    assert got.source == "keyword_fallback"


def test_unknown_intent_value_is_rejected(monkeypatch):
    """模型胡编一个意图名时必须回落，否则编排器路由到不存在的分支。"""
    class WeirdGateway:
        def chat(self, db, **kw):
            return {"content": '{"intent":"banana","confidence":0.99}',
                    "tokens_used": 8, "model": "fake-mini"}

    monkeypatch.setattr(intent, "get_ai_gateway", lambda: WeirdGateway())

    got = intent.classify(db=None, user_id=1, message="嗯", current_field_id=None)

    assert got.kind in intent.KINDS
    assert got.source == "keyword_fallback"

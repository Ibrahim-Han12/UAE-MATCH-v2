# 对话系统 SL1 实施计划

> **给执行者：** 用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans` 按任务逐个实施。步骤用 `- [ ]` 勾选跟踪。
> 规格来源：[hld-dialogue-system.md](hld-dialogue-system.md) ｜ 编号约定：[glossary.md](glossary.md) ｜ 人格与验收：[persona-voice-guide.md](persona-voice-guide.md)
> 日期：2026-08-22 ｜ 裁决：意图层并入 SL1（不按 HLD 原定的 SL1→SL2 顺序）

**Goal：** 让深访漏斗**可完成**——C 类择偶条件与 D 类情境题从"颗粒无收"变为可采齐，且拒答有字段级处理。

**Architecture：** 把"希望 LLM 听话"变成"结构上让它只能听话"。一轮对话的通路：意图层（每轮 mini 分类）→ 会话状态机（三幕）→ 幕策略（每幕独立交互模式与抽取契约）→ 生成 → 输出校验（已完成）。幕状态持久化在新表 `interview_state`，跨天恢复。

**Tech Stack：** Python 3.10 / FastAPI / SQLAlchemy 2.x / PostgreSQL（dev 可 SQLite）/ pytest 9.1.1 / OpenAI API 经 `app.core.ai` 模型抽象层

## Global Constraints

- **禁止硬编码模型名**：一切调用走 `app.core.ai.get_ai_gateway().chat(db, user_id=..., task=Task.X, ...)`，档位由 `app/core/ai/routing.py` 的 `TASK_TIER` 决定（PRD 5.6.4 / BR-209）。
- **字段清单与问法禁入系统 prompt**（PRD 5.3.5）：只能由编排器在 user/system 轮指令里运行时注入。
- **完成度只计 A–D 类必采**，`declined` 视为"已处理"计入完成度（DEC-028）。
- **地板字段不允许 declined**：`C1` 对方年龄范围、`C5` 免谈项清单、`B3` 子女计划（DEC-033）。拒答处理为"换问法重试**恰好 1 次**"，仍拒则明确告知影响且**完成度不推进**。
- **幕命名**：`act1` / `act2` / `act3`，禁用 `D` 前缀（`D1–D4` 是 Schema 情境题字段）。用户状态 `S1–S7` 语义不变，本计划不触碰。
- **意图分类成本**：每轮 +1 次 mini 调用，`count_user_quota=False`（系统侧不占用户配额），全程深访约 +0.05 AED（DEC-031）。
- **幕状态存新表** `interview_state`（DEC-032），不塞 `user_profiles` JSON。
- **输出校验层已完成**，复用 `app.core.dialogue.output_check`，本计划不重写。
- **测试**：pytest 从 `backend/` 目录跑（`backend/pytest.ini` 已配 `testpaths=tests`、`pythonpath=.`）。所有测试用真实配置文件，不 mock 配置。
- **不 commit**：`app/core/**` 的函数一律不调用 `db.commit()`，由调用方提交（全仓约定）。

---

## 文件结构

| 文件 | 责任 |
|---|---|
| `backend/config/interview/interview_schema.yaml` | 改：给 `C1`/`C5`/`B3` 加 `refusal_floor: true`（DEC-033 落配置，不写进代码） |
| `backend/app/core/interview/config.py` | 改：加 `floor_field_ids()` |
| `backend/app/core/dialogue/acts.py` | 新：幕定义与切幕策略。纯函数，从 Schema 推导幕字段集，无 DB 依赖 |
| `backend/app/models/interview_state.py` | 新：`interview_state` 表（DEC-032） |
| `backend/app/core/dialogue/state.py` | 新：`interview_state` 的读写原语（get_or_create / 切幕 / 记 declined / 记拒答次数） |
| `backend/app/core/dialogue/refusal.py` | 新：拒答决策纯函数（retry / decline / block），含地板线 |
| `backend/app/core/dialogue/intent.py` | 新：意图层。mini 分类 + 关键词 fallback |
| `backend/app/core/ai/routing.py` | 改：加 `Task.INTENT_CLASSIFY`（mini 档） |
| `backend/app/core/memory/extractor.py` | 改：抽取契约注入 `coding_rubric`（D 类颗粒无收的第二根因） |
| `backend/app/core/interview/orchestrator.py` | 改：接线——意图层替换关键词路由、按幕取目标、幕交互模式指令、拒答分支、完成度计入 declined |
| `backend/scripts/dev_migrate.py` | 改：新表进 `create_all`（`app.main` 导入模型即可，只需在 `app/models/__init__.py` 登记） |
| `backend/app/models/__init__.py` | 改：登记 `InterviewState` |
| `backend/tests/test_acts.py` | 新：幕推导与切幕 |
| `backend/tests/test_refusal.py` | 新：拒答决策与地板线 |
| `backend/tests/test_intent.py` | 新：意图层（fallback 用真实词表，模型分类用注入的假网关） |
| `backend/tests/test_extraction_rubric.py` | 新：抽取契约含 rubric |
| `backend/tests/test_dialogue_state.py` | 新：幕状态读写（内存 SQLite） |
| `backend/tests/test_orchestrator_acts.py` | 新：幕交互模式指令与意图指令的自身合规 |

---

## Task 1: 地板字段进配置

**Files:**
- Modify: `backend/config/interview/interview_schema.yaml`（`C1` / `C5` / `B3` 三处字段块）
- Modify: `backend/app/core/interview/config.py`
- Test: `backend/tests/test_acts.py`

**Interfaces:**
- Consumes: 无
- Produces: `config.floor_field_ids() -> Set[str]`，返回 `{"B3", "C1", "C5"}`

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_acts.py`：

```python
"""幕状态机与地板字段（DEC-033）。"""
from app.core.interview import config as ic


def test_floor_fields_come_from_schema_not_code():
    """DEC-033 的三个地板字段必须由 Schema 的 refusal_floor 标记推导，不得硬编码。"""
    assert ic.floor_field_ids() == {"C1", "C5", "B3"}
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_acts.py -v`
Expected: FAIL —— `AttributeError: module 'app.core.interview.config' has no attribute 'floor_field_ids'`

- [ ] **Step 3: 配置加标记**

在 `interview_schema.yaml` 的 `C1` 字段块内、`recalc_trigger` 之后加一行（`C5`、`B3` 同样处理）：

```yaml
    refusal_floor: true             # DEC-033：不允许 declined；拒答换问法重试 1 次后明确告知影响
```

三处的准确位置：
- `- id: C1`（`key: partner_age_range`）块内
- `- id: C5`（`key: dealbreakers`）块内
- `- id: B3`（`key: children_plan`）块内

- [ ] **Step 4: 实现 floor_field_ids**

在 `backend/app/core/interview/config.py` 末尾（`validate()` 之前）加：

```python
def floor_field_ids() -> Set[str]:
    """拒答地板字段（DEC-033）：不允许 declined，缺失则完成度不推进。"""
    return {f["id"] for f in schema_fields() if f.get("refusal_floor") is True}
```

文件头 import 补 `Set`：

```python
from typing import Any, Dict, List, Optional, Set
```

- [ ] **Step 5: 跑测试确认通过**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_acts.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add backend/config/interview/interview_schema.yaml backend/app/core/interview/config.py backend/tests/test_acts.py
git commit -m "feat(interview): 地板字段进 Schema 配置（DEC-033 / BR-201）"
```

---

## Task 2: 幕定义与切幕策略

**Files:**
- Create: `backend/app/core/dialogue/acts.py`
- Test: `backend/tests/test_acts.py`（追加）

**Interfaces:**
- Consumes: `config.floor_field_ids()`、`config.schema_fields()`
- Produces:
  - `ACTS: tuple = ("act1", "act2", "act3")`
  - `act_field_ids(act: str) -> List[str]` —— 该幕的必采访谈字段，按 Schema 顺序
  - `act_of(field_id: str) -> Optional[str]`
  - `act_complete(act: str, handled: Set[str]) -> bool` —— `handled` = filled ∪ declined
  - `current_act(handled: Set[str]) -> str` —— 第一个未完成的幕；全完成返回 `"act3"`
  - `next_target(handled: Set[str], sensitive_ok: bool) -> Optional[dict]` —— 当前幕内 Schema 顺序的第一个缺口字段

- [ ] **Step 1: 写失败测试**

追加到 `backend/tests/test_acts.py`：

```python
from app.core.dialogue import acts


def test_act_field_ids_are_derived_from_schema_categories():
    """幕字段集从 Schema 的 category 推导：act1=A/B、act2=C、act3=D，只取必采访谈字段。"""
    assert acts.act_field_ids("act2") == ["C1", "C2", "C3", "C4", "C5"]
    assert acts.act_field_ids("act3") == ["D1", "D2", "D3", "D4"]
    # A1/A2/A3 来源是 eid/declaration，不由访谈采集，不该进 act1
    act1 = acts.act_field_ids("act1")
    assert "A4" in act1 and "B6" in act1
    assert "A1" not in act1 and "A2" not in act1 and "A3" not in act1


def test_current_act_is_first_incomplete_act():
    """A+B 全部处理完才进 act2；C 全部处理完才进 act3。"""
    assert acts.current_act(set()) == "act1"

    act1_done = set(acts.act_field_ids("act1"))
    assert acts.current_act(act1_done) == "act2"

    act2_done = act1_done | set(acts.act_field_ids("act2"))
    assert acts.current_act(act2_done) == "act3"


def test_declined_counts_as_handled_for_act_exit():
    """DEC-028：declined 视为已处理，否则拒答一个字段就永远卡在这一幕。"""
    handled = set(acts.act_field_ids("act1"))
    assert acts.act_complete("act1", handled) is True

    partial = handled - {"A4"}
    assert acts.act_complete("act1", partial) is False


def test_next_target_stays_within_current_act():
    """幕内按 Schema 顺序取缺口；不得跨幕取。"""
    act1_done = set(acts.act_field_ids("act1"))
    target = acts.next_target(act1_done, sensitive_ok=True)

    assert target is not None
    assert target["id"] == "C1"


def test_next_target_skips_high_sensitivity_without_consent():
    """未获敏感授权时跳过 sensitivity: high 字段（沿用既有行为）。"""
    act1_done = set(acts.act_field_ids("act1"))
    act2_done = act1_done | set(acts.act_field_ids("act2"))
    target = acts.next_target(act2_done, sensitive_ok=False)

    # act3 全部是 sensitivity high/medium 的情境题；D1/D2/D3 为 high
    assert target is None or target.get("sensitivity") != "high"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_acts.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'app.core.dialogue.acts'`

- [ ] **Step 3: 实现 acts.py**

创建 `backend/app/core/dialogue/acts.py`：

```python
"""幕状态机的幕定义与切幕策略（hld-dialogue-system.md §3）。

纯函数、无 DB 依赖：幕字段集从 Schema 的 category 推导，不在代码里重复字段清单。
act1 = A/B 类事实（自由对话）｜act2 = C 类择偶条件（逐项快问）｜act3 = D 类情境题。
"""
from typing import Dict, List, Optional, Set

from app.core.interview import config as ic

ACTS = ("act1", "act2", "act3")

# 幕 → Schema category。act1 合并 A/B 两类（同为事实层，交互模式相同）。
_ACT_CATEGORIES: Dict[str, tuple] = {
    "act1": ("A", "B"),
    "act2": ("C",),
    "act3": ("D",),
}


def act_field_ids(act: str) -> List[str]:
    """该幕的必采访谈字段，按 Schema 顺序。系统带入字段（eid/declaration）不计。"""
    cats = _ACT_CATEGORIES[act]
    return [
        f["id"] for f in ic.schema_fields()
        if f.get("category") in cats
        and f.get("source") == "interview"
        and f.get("required_level") == "must"
    ]


def act_of(field_id: str) -> Optional[str]:
    for act in ACTS:
        if field_id in act_field_ids(act):
            return act
    return None


def act_complete(act: str, handled: Set[str]) -> bool:
    """handled = filled ∪ declined（DEC-028：declined 视为已处理）。"""
    return all(fid in handled for fid in act_field_ids(act))


def current_act(handled: Set[str]) -> str:
    for act in ACTS:
        if not act_complete(act, handled):
            return act
    return ACTS[-1]


def next_target(handled: Set[str], sensitive_ok: bool) -> Optional[dict]:
    """当前幕内 Schema 顺序的第一个缺口字段；未获敏感授权时跳过 high。"""
    act = current_act(handled)
    for fid in act_field_ids(act):
        if fid in handled:
            continue
        field = ic.field_by_id(fid)
        if field is None:
            continue
        if not sensitive_ok and field.get("sensitivity") == "high":
            continue
        return field
    return None
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_acts.py -v`
Expected: PASS（6 项）

- [ ] **Step 5: 提交**

```bash
git add backend/app/core/dialogue/acts.py backend/tests/test_acts.py
git commit -m "feat(dialogue): 幕定义与切幕策略，幕字段集从 Schema 推导（BR-201）"
```

---

## Task 3: interview_state 表与读写原语

**Files:**
- Create: `backend/app/models/interview_state.py`
- Create: `backend/app/core/dialogue/state.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_dialogue_state.py`

**Interfaces:**
- Consumes: `acts.current_act`
- Produces:
  - `InterviewState` 模型：`user_id` / `current_act` / `act_entered_at` / `declined_fields`(JSON list) / `refusal_counts`(JSON dict) / `updated_at`
  - `state.get_or_create(db, user_id) -> InterviewState`
  - `state.declined_set(st) -> Set[str]`
  - `state.mark_declined(db, st, field_id) -> None`
  - `state.bump_refusal(db, st, field_id) -> int` —— 返回累计拒答次数（含本次）
  - `state.refusal_count(st, field_id) -> int`
  - `state.sync_act(db, st, handled) -> str` —— 按 handled 重算当前幕，切幕时刷新 `act_entered_at`，返回幕名

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_dialogue_state.py`：

```python
"""interview_state 读写原语（DEC-032：状态机语义清晰、可查询）。"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.core.dialogue import acts, state


@pytest.fixture()
def db():
    """内存 SQLite：本任务只验状态读写，不依赖 Postgres。"""
    import app.models  # noqa: F401  # 登记全部模型
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_get_or_create_is_idempotent(db):
    a = state.get_or_create(db, user_id=1)
    db.flush()
    b = state.get_or_create(db, user_id=1)

    assert a.id == b.id
    assert a.current_act == "act1"


def test_mark_declined_accumulates(db):
    st = state.get_or_create(db, user_id=1)

    state.mark_declined(db, st, "A7")
    state.mark_declined(db, st, "A9")
    state.mark_declined(db, st, "A7")   # 重复不应产生重复项

    assert state.declined_set(st) == {"A7", "A9"}


def test_bump_refusal_returns_running_count(db):
    st = state.get_or_create(db, user_id=1)

    assert state.bump_refusal(db, st, "C1") == 1
    assert state.bump_refusal(db, st, "C1") == 2
    assert state.refusal_count(st, "C5") == 0


def test_sync_act_advances_and_stamps_entry_time(db):
    st = state.get_or_create(db, user_id=1)
    first_stamp = st.act_entered_at

    handled = set(acts.act_field_ids("act1"))
    assert state.sync_act(db, st, handled) == "act2"
    assert st.current_act == "act2"
    assert st.act_entered_at != first_stamp

    # 幕不变时不重新盖时间戳（否则"幕停留时长"指标失真）
    stamp_in_act2 = st.act_entered_at
    assert state.sync_act(db, st, handled) == "act2"
    assert st.act_entered_at == stamp_in_act2
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_dialogue_state.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'app.core.dialogue.state'`

- [ ] **Step 3: 建模型**

创建 `backend/app/models/interview_state.py`：

```python
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.sql import func

from app.db.session import Base


class InterviewState(Base):
    """
    深访幕状态机（DEC-032 / hld-dialogue-system.md §3）。

    独立表而非塞 user_profiles JSON：状态机语义清晰、可查询（幕停留时长等指标直接出）。
    """
    __tablename__ = "interview_state"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True, nullable=False)

    current_act = Column(String(10), default="act1", nullable=False)   # act1 / act2 / act3
    act_entered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    declined_fields = Column(JSON, nullable=True)   # list[str]：拒答且已放弃追问的字段（DEC-028 计完成度）
    refusal_counts = Column(JSON, nullable=True)    # {field_id: int}：换问法重试的计数（DEC-033 上限 1）

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
```

在 `backend/app/models/__init__.py` 末尾追加：

```python
from app.models.interview_state import InterviewState  # noqa: F401
```

- [ ] **Step 4: 实现读写原语**

创建 `backend/app/core/dialogue/state.py`：

```python
"""interview_state 读写原语。约定：本模块不 commit，由调用方提交。"""
from datetime import datetime, timezone
from typing import Set

from sqlalchemy.orm import Session

from app.core.dialogue import acts
from app.models.interview_state import InterviewState


def get_or_create(db: Session, user_id: int) -> InterviewState:
    st = db.query(InterviewState).filter_by(user_id=user_id).first()
    if st is None:
        st = InterviewState(user_id=user_id, current_act="act1",
                            act_entered_at=datetime.now(timezone.utc),
                            declined_fields=[], refusal_counts={})
        db.add(st)
        db.flush()
    return st


def declined_set(st: InterviewState) -> Set[str]:
    return set(st.declined_fields or [])


def mark_declined(db: Session, st: InterviewState, field_id: str) -> None:
    current = list(st.declined_fields or [])
    if field_id not in current:
        current.append(field_id)
        st.declined_fields = current
        db.add(st)


def refusal_count(st: InterviewState, field_id: str) -> int:
    return int((st.refusal_counts or {}).get(field_id, 0))


def bump_refusal(db: Session, st: InterviewState, field_id: str) -> int:
    counts = dict(st.refusal_counts or {})
    counts[field_id] = int(counts.get(field_id, 0)) + 1
    st.refusal_counts = counts
    db.add(st)
    return counts[field_id]


def sync_act(db: Session, st: InterviewState, handled: Set[str]) -> str:
    """按已处理字段重算当前幕；只在真正切幕时刷新 act_entered_at。"""
    act = acts.current_act(handled)
    if act != st.current_act:
        st.current_act = act
        st.act_entered_at = datetime.now(timezone.utc)
        db.add(st)
    return act
```

- [ ] **Step 5: 跑测试确认通过**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_dialogue_state.py -v`
Expected: PASS（4 项）

- [ ] **Step 6: 全量回归 + 提交**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest`
Expected: 之前的 49 项 + 本任务新增全部 PASS

```bash
git add backend/app/models/interview_state.py backend/app/models/__init__.py backend/app/core/dialogue/state.py backend/tests/test_dialogue_state.py
git commit -m "feat(dialogue): interview_state 幕状态持久化，跨天恢复（DEC-032 / BR-201）"
```

---

## Task 4: 字段级拒答决策（含 DEC-033 地板线）

**Files:**
- Create: `backend/app/core/dialogue/refusal.py`
- Test: `backend/tests/test_refusal.py`

**Interfaces:**
- Consumes: `config.floor_field_ids()`
- Produces:
  - `RETRY = "retry"` / `DECLINE = "decline"` / `BLOCK = "block"`
  - `decide(field_id: str, prior_refusals: int) -> str` —— `prior_refusals` 是本次之前的累计次数
  - `instruction_for(decision: str, field: dict) -> str` —— 给编排器注入的轮指令文本

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_refusal.py`：

```python
"""字段级拒答决策（DEC-028 豁免 + DEC-033 地板线）。"""
from app.core.dialogue import refusal
from app.core.interview import config as ic


def test_normal_field_first_refusal_triggers_rephrase():
    assert refusal.decide("A7", prior_refusals=0) == refusal.RETRY


def test_normal_field_second_refusal_is_declined():
    """DEC-028：重试一次后不再问，标 declined 并视为已处理。"""
    assert refusal.decide("A7", prior_refusals=1) == refusal.DECLINE


def test_floor_field_also_gets_exactly_one_rephrase():
    assert refusal.decide("C1", prior_refusals=0) == refusal.RETRY


def test_floor_field_second_refusal_blocks_instead_of_declining():
    """DEC-033：地板字段不允许 declined，否则 25 项全拒也能过闸。"""
    for fid in sorted(ic.floor_field_ids()):
        assert refusal.decide(fid, prior_refusals=1) == refusal.BLOCK, fid


def test_floor_and_normal_field_decisions_must_diverge():
    """验收 #12 的单元层对应：同样是二次拒答，行为必须分叉。"""
    assert refusal.decide("A7", prior_refusals=1) != refusal.decide("B3", prior_refusals=1)


def test_block_instruction_states_impact_without_pressure():
    field = ic.field_by_id("C1")
    text = refusal.instruction_for(refusal.BLOCK, field)

    assert "没法" in text or "无法" in text     # 必须说明后果
    for pressure in ("必须", "请您配合", "否则无法继续使用"):
        assert pressure not in text


def test_retry_instruction_demands_one_different_phrasing():
    field = ic.field_by_id("A7")
    text = refusal.instruction_for(refusal.RETRY, field)

    assert "换一种" in text
    assert "只" in text or "一次" in text


def test_decline_instruction_drops_topic_permanently():
    field = ic.field_by_id("A7")
    text = refusal.instruction_for(refusal.DECLINE, field)

    assert "跳过" in text or "翻篇" in text
    assert "不再" in text
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_refusal.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'app.core.dialogue.refusal'`

- [ ] **Step 3: 实现 refusal.py**

创建 `backend/app/core/dialogue/refusal.py`：

```python
"""字段级拒答决策（hld-dialogue-system.md §2）。

DEC-028：普通必采字段拒答 → 换问法重试一次 → 仍拒则标 declined，视为已处理。
DEC-033：地板字段（C1/C5/B3）不允许 declined → 仍拒则明确告知影响，完成度不推进。
本模块是纯函数，不碰 DB；轮指令文本由编排器注入生成层。
"""
from app.core.interview import config as ic

RETRY = "retry"
DECLINE = "decline"
BLOCK = "block"

MAX_REPHRASE = 1   # 换问法重试上限（问法库 global_rules.max_probe_depth 同轨）


def decide(field_id: str, prior_refusals: int) -> str:
    """prior_refusals = 本次拒答之前该字段已累计的拒答次数。"""
    if prior_refusals < MAX_REPHRASE:
        return RETRY
    if field_id in ic.floor_field_ids():
        return BLOCK
    return DECLINE


def instruction_for(decision: str, field: dict) -> str:
    label = field.get("label_zh", field.get("id", ""))
    if decision == RETRY:
        return (
            f"【拒答处理·换问法】用户回避了「{label}」。先一句自然带过，不追问、不评价；"
            "然后换一种完全不同的问法再问一次——只这一次。"
            "可用更具体的情境或更小的切口，禁止重复刚才被拒的那种问法。"
        )
    if decision == DECLINE:
        return (
            f"【拒答处理·翻篇】用户第二次回避「{label}」。一句轻轻跳过，"
            "明确表示这个不影响什么，此后整段对话不再提这个话题（也不要变相打探）。"
            "本轮接着聊下一个话题。"
        )
    return (
        f"【拒答处理·说明影响】「{label}」是你干活的地基之一，用户第二次回避。"
        "老实告诉他：这一项你不知道就没法给他介绍人；今天不想说没关系，"
        "什么时候想说了再跟你讲。语气是诚实，不是施压——不要说教，不要重复劝，"
        "不要暗示他不配合。说完本轮就停在这里，不要再问别的。"
    )
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_refusal.py -v`
Expected: PASS（8 项）

- [ ] **Step 5: 语气闸交叉验证**

把三条指令文本过一遍输出校验层，确认它们本身不含禁用表达（否则模型会照抄）。追加到 `backend/tests/test_refusal.py`：

```python
def test_refusal_instructions_are_themselves_clean():
    """指令会进 prompt，若含"您/请问"模型会照抄。"""
    from app.core.dialogue import output_check as oc

    for decision in (refusal.RETRY, refusal.DECLINE, refusal.BLOCK):
        text = refusal.instruction_for(decision, ic.field_by_id("C1"))
        assert oc.check(text).has_hard is False, f"{decision} 指令含禁用表达"
```

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_refusal.py -v`
Expected: PASS（9 项）

- [ ] **Step 6: 提交**

```bash
git add backend/app/core/dialogue/refusal.py backend/tests/test_refusal.py
git commit -m "feat(dialogue): 字段级拒答决策 + 地板线（DEC-028, DEC-033 / BR-201）"
```

---

## Task 5: 意图层

**Files:**
- Create: `backend/app/core/dialogue/intent.py`
- Modify: `backend/app/core/ai/routing.py`
- Test: `backend/tests/test_intent.py`

**Interfaces:**
- Consumes: `get_ai_gateway().chat`、`Task.INTENT_CLASSIFY`
- Produces:
  - `Intent` dataclass：`kind: str` / `field_id: Optional[str]` / `confidence: float` / `source: str`
  - `KINDS: tuple` —— 8 个意图
  - `classify_by_keyword(message: str) -> Intent` —— 纯函数 fallback
  - `classify(db, user_id: int, message: str, current_field_id: Optional[str] = None) -> Intent`

- [ ] **Step 1: 加 Task 常量**

在 `backend/app/core/ai/routing.py` 的 `Task` 类里，`MODERATION` 之后加一行：

```python
    INTENT_CLASSIFY = "intent_classify"              # 对话意图分类 —— mini
```

在同文件的 `TASK_TIER` 字典里加：

```python
    Task.INTENT_CLASSIFY: "mini",
```

- [ ] **Step 2: 写失败测试**

创建 `backend/tests/test_intent.py`：

```python
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
    """"不聊了，跳过吧"同时命中两个词表，停止意愿更强。"""
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
```

- [ ] **Step 3: 跑测试确认失败**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_intent.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'app.core.dialogue.intent'`

- [ ] **Step 4: 实现 intent.py**

创建 `backend/app/core/dialogue/intent.py`：

```python
"""意图层（hld-dialogue-system.md §2）：每轮一次 mini 分类，取代关键词 if-else。

意图先于生成——先知道用户这轮想干什么，再决定问什么。分类失败一律回落关键词兜底，
绝不因分类不可用而中断对话。危机识别是硬规则，由编排器在进入本层之前前置处理。
"""
import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

from app.core.ai import get_ai_gateway, Task

logger = logging.getLogger(__name__)

KINDS = ("answer", "correction", "refusal_field", "stop",
         "proceed", "ask_ai", "smalltalk", "crisis")

# 关键词兜底词表（原编排器的 STOP/PROCEED 词表降级至此，仅用于分类失败与 crisis 兜底）
STOP_PHRASES = ("不想聊", "不想回答", "不聊了", "不说了", "先到这里", "改天", "下次再",
                "暂停", "停一下", "别问了")
PROCEED_PHRASES = ("下一步", "下一个页面", "换个页面", "进入下一", "还差什么", "还差多少",
                   "还要聊多久", "什么时候能", "进度怎么", "跳过")

_SYSTEM = (
    "你是对话意图分类器。判断用户这一轮想做什么，只返回 JSON，不要解释。\n"
    "intent 取值：answer(在回答问题) / correction(在纠正之前的信息) / "
    "refusal_field(不愿回答当前这个问题) / stop(想结束本次对话) / "
    "proceed(想知道进度或想进入下一步) / ask_ai(在反问红娘本人) / "
    "smalltalk(闲聊，与当前问题无关) / crisis(表达自伤或严重情绪危机)。\n"
    "输出格式：{\"intent\":\"...\",\"field_id\":\"当前问题的字段号或 null\","
    "\"confidence\":0.0-1.0}"
)


@dataclass(frozen=True)
class Intent:
    kind: str
    field_id: Optional[str] = None
    confidence: float = 0.0
    source: str = "model"          # model | keyword_fallback


def classify_by_keyword(message: str) -> Intent:
    """纯函数兜底。停止优先于前进：停止意愿比想推进更强，误判代价更大。"""
    if any(p in message for p in STOP_PHRASES):
        return Intent("stop", source="keyword_fallback")
    if any(p in message for p in PROCEED_PHRASES):
        return Intent("proceed", source="keyword_fallback")
    return Intent("answer", source="keyword_fallback")


def _parse(content: str, current_field_id: Optional[str]) -> Optional[Intent]:
    m = re.search(r"\{.*\}", content, re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except (ValueError, TypeError):
        return None
    kind = data.get("intent")
    if kind not in KINDS:
        return None
    field_id = data.get("field_id") or current_field_id
    try:
        conf = float(data.get("confidence", 0.0))
    except (ValueError, TypeError):
        conf = 0.0
    return Intent(kind, field_id, conf, source="model")


def classify(db, user_id: int, message: str,
             current_field_id: Optional[str] = None) -> Intent:
    """每轮 +1 次 mini 调用（DEC-031）。系统侧调用，不占用户配额。"""
    prompt = f"当前正在问的字段：{current_field_id or '无'}\n用户这一轮说：{message}"
    try:
        resp = get_ai_gateway().chat(
            db, user_id=user_id, task=Task.INTENT_CLASSIFY,
            messages=[{"role": "system", "content": _SYSTEM},
                      {"role": "user", "content": prompt}],
            scene="intent_classify", temperature=0.0, count_user_quota=False,
        )
    except Exception:
        logger.exception("意图分类失败，回落关键词 user_id=%s", user_id)
        return classify_by_keyword(message)

    parsed = _parse(resp.get("content", ""), current_field_id)
    if parsed is None:
        logger.warning("意图分类结果不可用，回落关键词 user_id=%s", user_id)
        return classify_by_keyword(message)
    return parsed
```

- [ ] **Step 5: 跑测试确认通过**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_intent.py -v`
Expected: PASS（8 项）

- [ ] **Step 6: 提交**

```bash
git add backend/app/core/dialogue/intent.py backend/app/core/ai/routing.py backend/tests/test_intent.py
git commit -m "feat(dialogue): 意图层取代关键词路由，分类失败回落兜底（DEC-031 / BR-201）"
```

---

## Task 6: D 类抽取契约注入 coding_rubric

**Files:**
- Modify: `backend/app/core/memory/extractor.py:63-92`（`_build_extraction_prompt`）
- Test: `backend/tests/test_extraction_rubric.py`

**Interfaces:**
- Consumes: `config.bank_entry_for(field_id)` 的 `coding_rubric` 键
- Produces: `_build_extraction_prompt` 的输出对 D 类字段附带 rubric 与 `unclear` 规则

**背景：** 问法库里 D 类每题都有 `coding_rubric`（secure/anxious/avoidant 的行为特征），但抽取 prompt 根本没带——这是 D 类颗粒无收的第二根因。

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_extraction_rubric.py`：

```python
"""D 类抽取必须携带行为编码规则（hld-dialogue-system.md §4）。"""
from app.core.interview import config as ic
from app.core.memory import extractor


def test_d_class_extraction_contract_includes_coding_rubric():
    d1 = ic.field_by_id("D1")
    prompt = extractor._build_extraction_prompt("用户: 他不回我我就一直看手机", [d1])

    rubric = ic.bank_entry_for("D1")["coding_rubric"]
    assert rubric["anxious"] in prompt
    assert rubric["secure"] in prompt


def test_d_class_extraction_requires_unclear_when_uncertain():
    """强行编码比留空更糟：会污染匹配算法的心理维度。"""
    d2 = ic.field_by_id("D2")
    prompt = extractor._build_extraction_prompt("用户: 看情况吧", [d2])

    assert "unclear" in prompt


def test_non_d_class_field_gets_no_rubric():
    """成本纪律：A 类事实字段没有编码规则，不该被撑长。"""
    a7 = ic.field_by_id("A7")
    prompt = extractor._build_extraction_prompt("用户: 月薪三万多", [a7])

    assert "行为编码" not in prompt
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_extraction_rubric.py -v`
Expected: FAIL —— 前两项断言失败（rubric 文本不在 prompt 里）

- [ ] **Step 3: 实现注入**

在 `backend/app/core/memory/extractor.py` 的 `_build_extraction_prompt` 里，字段描述循环内、追加到该字段描述之后：

```python
        rubric = (interview_config.bank_entry_for(f["id"]) or {}).get("coding_rubric")
        if rubric:
            pairs = "；".join(
                f"{k}={v}" for k, v in rubric.items() if k != "note"
            )
            desc += (f"\n  行为编码规则（按用户实际做法归类，不按自我评价）：{pairs}"
                     f"\n  不确定就输出 unclear，绝不硬编码——错的编码比缺失更糟")
```

注意 `interview_config` 是该文件已有的 import 别名（`from app.core.interview import config as interview_config`）；若别名不同，用文件内既有名称。

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_extraction_rubric.py -v`
Expected: PASS（3 项）

- [ ] **Step 5: 提交**

```bash
git add backend/app/core/memory/extractor.py backend/tests/test_extraction_rubric.py
git commit -m "feat(interview): D 类抽取注入 coding_rubric，修 D 类颗粒无收第二根因（BR-201）"
```

---

## Task 7: 编排器接线

**Files:**
- Modify: `backend/app/core/interview/orchestrator.py`
- Test: `backend/tests/test_orchestrator_acts.py`

**Interfaces:**
- Consumes: `acts` / `state` / `refusal` / `intent` / `output_check` 全部前述接口
- Produces:
  - `act_instruction(act: str) -> str` —— 幕交互模式指令（act1 自由对话 / act2 明示环节逐项快问 / act3 情境题）
  - `compute_progress(db, user_id)` 的 `handled` 计入 `declined`

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_orchestrator_acts.py`：

```python
"""编排器的幕交互模式指令与完成度口径。"""
from app.core.dialogue import output_check as oc
from app.core.interview import orchestrator


def test_act2_instruction_announces_stage_and_bans_mechanical_transitions():
    text = orchestrator.act_instruction("act2")

    assert "择偶条件" in text
    assert "机械过渡" in text or "好的" in text     # 必须点名要避开的过渡句
    assert "弹性" in text                           # post_step 弹性确认不可跳过


def test_act3_instruction_demands_casual_tone_and_bans_assessment_words():
    text = orchestrator.act_instruction("act3")

    assert "情境" in text or "场景" in text
    for banned in ("评估", "测试", "量表"):
        assert f"不要说{banned}" in text or banned in text


def test_all_act_instructions_are_themselves_clean():
    """指令进 prompt，含"您/请问"模型会照抄。"""
    for act in ("act1", "act2", "act3"):
        result = oc.check(orchestrator.act_instruction(act))
        assert result.has_hard is False, f"{act} 指令含禁用表达：{result.violations}"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_orchestrator_acts.py -v`
Expected: FAIL —— `AttributeError: module 'app.core.interview.orchestrator' has no attribute 'act_instruction'`

- [ ] **Step 3: 实现幕指令**

在 `backend/app/core/interview/orchestrator.py` 的 `_build_suggestion_block` 之前加：

```python
_ACT_INSTRUCTIONS = {
    "act1": (
        "【本幕模式·自由对话】现在是了解他基本情况的阶段。顺着他的话聊，"
        "一轮一个问题，先回应再问。他跑题聊到别的照常顺势采集，不用拉回来。"
    ),
    "act2": (
        "【本幕模式·择偶条件】现在进入最关键的一段：他想找什么样的人。"
        "这一段有几项要连着聊，所以每两项之间必须垫一句有信息量的反应——"
        "对他上一个答案的判断、你的经验、或者本地的实际情况。"
        "禁止机械过渡：不要说「好的」「那接下来」「下一个问题」这类衔接。"
        "每项采到值之后，追加确认一次弹性：这条是硬线，还是遇到合适的人可以松一松。"
    ),
    "act3": (
        "【本幕模式·情境题】最后几个轻松的小场景。"
        "用闲聊的口吻抛出场景（「问个日常的」「聊个场景」），一题一答，答完自然接一句就好。"
        "绝不要说评估、测试、量表、题目、性格分析这类词，也不要暗示他在被判断。"
    ),
}


def act_instruction(act: str) -> str:
    return _ACT_INSTRUCTIONS[act]
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest tests/test_orchestrator_acts.py -v`
Expected: PASS（3 项）

- [ ] **Step 5: 接线 —— 完成度计入 declined**

把 `compute_progress` 改为接收已处理集合。修改 `backend/app/core/interview/orchestrator.py` 的 `compute_progress`：

```python
def compute_progress(db: Session, user_id: int,
                     declined: Optional[Set[str]] = None) -> Dict[str, Any]:
    """完成度按 filled ∪ declined 计（DEC-028：declined 视为已处理）。

    地板字段（DEC-033）不进 declined，因此永远计入缺口——这是"25 项全拒也能过闸"的堵口。
    """
    filled = field_mapping.get_filled_field_ids(db, user_id)
    handled = set(filled) | set(declined or ())
    completion = ic.compute_completion(handled)
    missing = [
        f["id"] for f in ic.completion_fields()
        if f.get("source") == "interview" and f["id"] not in handled
    ]
    return {"completion": completion, "filled": sorted(filled),
            "handled": sorted(handled), "missing_must": missing}
```

文件头 import 补 `Set`：

```python
from typing import Any, Dict, List, Optional, Set
```

- [ ] **Step 6: 接线 —— 幕状态与意图层前置（顺序关键）**

在 `handle_message` 里，**紧接危机分支之后、抽取之前**插入幕状态读取与意图分类。
顺序必须是「读状态 → 算幕 → 分类意图 → 抽取（按幕限定）→ 重算进度」，因为抽取要
按幕限定范围，而进度要在抽取后才准。

把原本这一段：

```python
    history = _recent_history(db, user.id)
    _save_msg(db, user.id, "user", message)
```

替换为：

```python
    history = _recent_history(db, user.id)
    _save_msg(db, user.id, "user", message)

    # 幕状态（DEC-032）与本轮意图（DEC-031）——都要在抽取之前，抽取按幕限定范围
    st = dstate.get_or_create(db, user.id)
    declined = dstate.declined_set(st)
    pre = compute_progress(db, user.id, declined=declined)
    current_act = dstate.sync_act(db, st, set(pre["handled"]))
    pre_target = acts.next_target(set(pre["handled"]), sensitive_ok)
    turn_intent = intent.classify(db, user.id, message,
                                 current_field_id=(pre_target or {}).get("id"))
```

模块头补 import：

```python
from app.core.dialogue import acts, intent, output_check, refusal
from app.core.dialogue import state as dstate
```

删除模块顶部的 `STOP_PHRASES` 与 `PROCEED_PHRASES` 两个常量（已迁至 `intent.py`）。

- [ ] **Step 7: 接线 —— 抽取按幕限定范围，然后重算进度**

把「2) 抽取本轮信息」的调用改为只抽当前幕 + 上一幕补漏（HLD §4 act-scoped targets，
现状每轮抽全 Schema 25+ 项导致 prompt 长、命中散）：

```python
    scoped = acts.act_field_ids(current_act)
    idx = acts.ACTS.index(current_act)
    if idx > 0:
        scoped = acts.act_field_ids(acts.ACTS[idx - 1]) + scoped
    try:
        extracted = extractor.extract_from_conversation(
            db, user.id, recent_text, field_ids=scoped)
        if extracted:
            extractor.apply_extracted(db, user.id, extracted, mode="interview")
            db.flush()
    except Exception:
        logger.exception("深访抽取失败（不阻塞对话） user_id=%s", user.id)
```

把「3) 缺口与状态」整段替换为（抽取后重算，并去掉关键词判定）：

```python
    progress = compute_progress(db, user.id, declined=declined)
    current_act = dstate.sync_act(db, st, set(progress["handled"]))
    target = acts.next_target(set(progress["handled"]), sensitive_ok)

    stop_intent = turn_intent.kind == "stop"
    proceed_intent = turn_intent.kind == "proceed"
    fatigue = detect_fatigue(history + [type("M", (), {"role": "user", "content": message})()])
    session_turns = sum(1 for h in history if h.role == "user") + 1
    wrap_up = stop_intent or fatigue or session_turns >= SESSION_SOFT_CAP_TURNS
```

- [ ] **Step 8: 接线 —— 意图路由表（拒答／纠正／反问／闲聊）**

HLD §2 的意图 → 策略路由表要完整落地，不能只接 stop/proceed。在指令组装的
`if completed:` 链里，`elif stop_intent:` **之前**依次插入三个分支：

```python
    elif turn_intent.kind == "refusal_field" and turn_intent.field_id:
        fid = turn_intent.field_id
        prior = dstate.refusal_count(st, fid)
        decision = refusal.decide(fid, prior_refusals=prior)
        dstate.bump_refusal(db, st, fid)
        if decision == refusal.DECLINE:
            dstate.mark_declined(db, st, fid)
        instruction = refusal.instruction_for(decision, ic.field_by_id(fid) or {"id": fid})
        log_event(db, user_id=user.id, event_type="field_refused",
                  metadata={"field_id": fid, "decision": decision,
                            "prior_refusals": prior, "act": current_act})
    elif turn_intent.kind in _INTENT_INSTRUCTIONS:
        instruction = intent_instruction(turn_intent.kind)
```

把 `else:` 分支（正常取目标问）改为带上幕交互模式指令：

```python
    else:
        if target is not None:
            instruction = (act_instruction(current_act) + "
"
                           + _build_suggestion_block(db, user.id, target))
        else:
            instruction = "【本轮建议】剩余待采信息均为敏感项，但用户尚未授权敏感画像采集。自然地聊当前话题，并在合适时机说明授权的价值（不施压）。"
```

在 `act_instruction` 之后加意图指令表（与幕指令同一写法，便于测试与替换）：

```python
_INTENT_INSTRUCTIONS = {
    "correction": (
        "【纠正指令】用户在更正之前的信息或你的假设。先明确确认这个更正"
        "（说清你记下的是什么），绝不装作没听见、也不要辩解。确认之后再自然地"
        "接着往下聊，本轮可以不提新问题。"
    ),
    "ask_ai": (
        "【反问指令】用户在问你本人的事。先如实、简短地答他这个问题——"
        "不要绕开，不要反过来先问他。答完再自然回到刚才的话题。"
    ),
    "smalltalk": (
        "【闲聊指令】用户聊的是与当前话题无关的事。接住它，给一句短而有内容的回应，"
        "然后顺势回到刚才的话题——不要生硬拉回，也不要陪着无目的地聊下去。"
    ),
}


def intent_instruction(kind: str) -> str:
    return _INTENT_INSTRUCTIONS[kind]
```

**补测试**（这三条指令都会进 prompt，必须自身干净）。追加到 `backend/tests/test_orchestrator_acts.py`：

```python
def test_intent_routing_covers_hld_table():
    """HLD §2 的路由表里由指令承载的三种意图必须都有指令。"""
    for kind in ("correction", "ask_ai", "smalltalk"):
        assert orchestrator.intent_instruction(kind)


def test_intent_instructions_are_themselves_clean():
    """指令进 prompt，含禁用表达模型会照抄。"""
    for kind in ("correction", "ask_ai", "smalltalk"):
        result = oc.check(orchestrator.intent_instruction(kind))
        assert result.has_hard is False, f"{kind} 指令含禁用表达：{result.violations}"
```

- [ ] **Step 9: 全量回归**

Run: `cd backend && ../.venv/Scripts/python.exe -m pytest`
Expected: 全部 PASS（此前 49 项 + Task 1–7 新增）

Run: `cd backend && python -m compileall -q app && echo OK`
Expected: `OK`

Run: `cd backend && ../.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'.'); from app.core.interview import orchestrator; from app.core.dialogue import acts, intent, refusal, state; print('导入 OK')"`
Expected: `导入 OK`

- [ ] **Step 10: 建表**

Run: `cd backend && ../.venv/Scripts/python.exe -m scripts.dev_migrate`
Expected: 无异常；`interview_state` 表建出。**若本地无 Postgres，本步跳过并在提交说明里注明未验证。**

- [ ] **Step 11: 提交**

```bash
git add backend/app/core/interview/orchestrator.py backend/tests/test_orchestrator_acts.py
git commit -m "feat(dialogue): 编排器接入意图层与三幕状态机，抽取按幕限定（BR-201）"
```

---

## 完成后需要的人工验证

代码测试覆盖的是"结构上让它只能听话"，覆盖不到"它说得像不像人"。以下必须由产品负责人实测：

| 项 | 对应验收 |
|---|---|
| 完整跑一轮深访，看 act2 五项是否连贯不像表单 | persona-voice-guide.md §二 #13、#14 |
| act3 四题是否像闲聊 | #15 |
| 对 `C1` 说"没想过"两次，看是否明确告知影响且不施压 | #11 |
| 先拒答收入、再拒答子女计划，看行为是否分叉 | #12 |
| 全程"您"字计数 = 0 | #17 |

## 本计划不做（留给 SL3）

- 回放 harness `scripts/eval_dialogue.py` 与黄金对话集
- 半自动验收项（#1/#2/#4/#5/#6/#8/#9/#10）的真实模型抽样
- 幕停留时长等线上指标看板

## 已知依赖缺口

`act1 → act2` 与 `act2 → act3` 的**幕切换话术**未在人格资产 v1.1 中提供（见 persona-voice-guide.md「已知缺口」）。Task 7 的 `act2` 指令里用工程口吻写了"现在进入最关键的一段"作为占位；产品负责人补出正式话术后，替换 `_ACT_INSTRUCTIONS["act2"]` 的首句即可，不动其余逻辑。

"""Voice Guide 一致性测试：禁用词表必须抓住所有已知坏句，且不误伤任何好句。

规格来源即 docs/persona-voice-guide.md §一 的对照表本身——文档是权威，本测试是它的执行版。
产品负责人往 Voice Guide 加一行 ❌，本测试会立刻告诉你禁用词表有没有覆盖到。
"""
import re
from pathlib import Path

import pytest

from app.core.dialogue import output_check as oc

_GUIDE = Path(__file__).resolve().parents[2] / "docs" / "persona-voice-guide.md"


def _voice_guide_rows():
    """解析 §一 的 | # | 幕 | ❌ | ✅ | 四列表格，返回 (编号, 幕, 坏句, 好句)。

    只取 §一：§二 验收规格也是四列表，混进来会把测试动作当句子测。
    """
    text = _GUIDE.read_text(encoding="utf-8")
    start = text.index("## 一、Voice Guide")
    end = text.index("## 二、")
    rows = []
    for line in text[start:end].splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4 or not re.fullmatch(r"\d+", cells[0]):
            continue
        rows.append((int(cells[0]), cells[1], cells[2], cells[3]))
    return rows


ROWS = _voice_guide_rows()


def test_voice_guide_table_was_parsed():
    """先证明解析有效——否则下面两组参数化测试会因为零条目而假通过。"""
    assert len(ROWS) == 17, f"解析到 {len(ROWS)} 行，Voice Guide 应有 17 行"


@pytest.mark.parametrize("num,act,bad", [(r[0], r[1], r[2]) for r in ROWS],
                         ids=[f"row{r[0]}-{r[1]}" for r in ROWS])
def test_every_bad_example_is_caught(num, act, bad):
    result = oc.check(bad)
    assert result.has_hard is True, f"Voice Guide #{num}（{act}）的 ❌ 句未被禁用词表拦住：{bad}"


@pytest.mark.parametrize("num,act,good", [(r[0], r[1], r[3]) for r in ROWS],
                         ids=[f"row{r[0]}-{r[1]}" for r in ROWS])
def test_no_good_example_is_false_flagged(num, act, good):
    result = oc.check(good)
    hard = [v for v in result.violations if v.type == oc.HARD]
    assert hard == [], f"Voice Guide #{num}（{act}）的 ✅ 句被误伤：{hard}"

"""对话处理层（hld-dialogue-system.md）。

一轮对话的处理管道：意图层 → 会话状态机 → 幕策略 → 生成 → 输出校验。
本包目前只含**输出校验**（纯代码、零模型成本）；其余层随对话系统 SL1 落地。
深访、军师（能力分层 L2）、主动触达（L3）共用本层。
"""
from app.core.dialogue import acts  # noqa: F401
from app.core.dialogue import output_check  # noqa: F401
from app.core.dialogue import state  # noqa: F401

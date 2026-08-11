"""
模型包。

BR-202 三层记忆体系的新表在此显式登记，确保 Base.metadata.create_all 能发现它们
（事实层 UserPsychProfile / 事件层 MemoryEvent / 情感层 UserCommProfile /
 向量库 MemoryVector / 待确认队列 MemoryPendingChange）。
"""
from app.models.user_psych_profile import UserPsychProfile  # noqa: F401
from app.models.memory_event import MemoryEvent  # noqa: F401
from app.models.user_comm_profile import UserCommProfile  # noqa: F401
from app.models.memory_vector import MemoryVector  # noqa: F401
from app.models.memory_pending_change import MemoryPendingChange  # noqa: F401
from app.models.user_state_transition import UserStateTransition  # noqa: F401
from app.models.phone_otp import PhoneOtp  # noqa: F401
from app.models.kyc_result import KycResult, BannedIdentity, AccountDeletionAudit  # noqa: F401

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Index
from sqlalchemy.sql import func
from app.db.session import Base


class KycResult(Base):
    """
    EID 核验结论（BR-107）。合规红线：平台只存"结论 + 最小字段 + 事务 ID"，
    证件图像与活体视频零留存（由持牌服务商处理）。
    eid_hash 为证件号单向哈希：用于一人多号去重与封禁者重注册拦截（PRD 3.5），不可逆推。
    """
    __tablename__ = "kyc_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    provider = Column(String(30), nullable=False)            # mock / uqudo / idwise ...
    transaction_id = Column(String(100), nullable=False)     # 服务商事务 ID（注销后审计保留）

    result = Column(String(20), nullable=False)              # passed / failed / needs_review
    full_name_verified = Column(String(200), nullable=True)  # 姓名核验值
    birth_date = Column(Date, nullable=True)
    gender = Column(String(10), nullable=True)               # male / female
    document_expiry = Column(Date, nullable=True)

    eid_hash = Column(String(64), nullable=True, index=True)  # sha256(EID号)，单向

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_kyc_results_user_time", "user_id", "created_at"),
    )


class BannedIdentity(Base):
    """
    永久拦截名单（A5 裁决 / PRD 3.5）：实锤欺诈/严重违规者的 EID 单向哈希。
    同一身份重新注册在 KYC 环节即拦截；不受注销审计 12 个月清除影响。
    """
    __tablename__ = "banned_identities"

    id = Column(Integer, primary_key=True, index=True)
    eid_hash = Column(String(64), unique=True, index=True, nullable=False)
    reason_code = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AccountDeletionAudit(Base):
    """
    注销最小合规审计记录（A5 裁决）：脱敏哈希 + 时间 + 原因码 + KYC 事务 ID，保留 12 个月。
    级联删除执行后本表是该用户唯一残留。
    """
    __tablename__ = "account_deletion_audits"

    id = Column(Integer, primary_key=True, index=True)
    contact_hash = Column(String(64), nullable=False)         # sha256(手机或邮箱)
    reason_code = Column(String(50), nullable=True)
    kyc_transaction_id = Column(String(100), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

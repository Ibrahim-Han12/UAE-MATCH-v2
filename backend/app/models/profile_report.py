from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.sql import func
from app.db.session import Base


class ProfileReport(Base):
    """
    画像报告（BR-201 双产物之用户交付物）。
    注意：表名 profile_reports——user_reports 是 v1.0 的举报表，勿混淆。
    铁律：基于结构化画像生成，禁止从对话原文一步直出（PRD 5.3）。
    基础版免费（A4 裁决）：你的故事/画像速写/寻找的人/匹配策略 四板块；
    深度版（高级会员，M3）追加盲区提示/依恋详解/交互追问。
    版本历史保留（报告生长机制，PRD 5.3.3）。
    """
    __tablename__ = "profile_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    version = Column(Integer, nullable=False, default=1)
    tier = Column(String(10), nullable=False, default="basic")   # basic / deep
    sections = Column(JSON, nullable=False)                      # {story, sketch, seeking, strategy}

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserConsent(Base):
    """
    分层同意记录（PRD 5.1 / BRD 11.2 PDPL）：基础服务数据 / 敏感画像数据 / AI 处理，
    分别授权、可分别撤回。敏感采集的硬前置。同意书文案为 C5 资产（待法务终稿）。
    """
    __tablename__ = "user_consents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    consent_type = Column(String(20), nullable=False)   # basic / sensitive / ai_processing
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

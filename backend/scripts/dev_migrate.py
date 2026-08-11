"""
开发库幂等迁移：create_all 建新表 + ALTER 补新列（Postgres）。
用法：python -m scripts.dev_migrate   （在 backend/ 目录下）
生产环境将由 Alembic 取代（HLD 已列），当前 dev 用本脚本保持库与模型同步。
"""
import app.main  # noqa: F401  # 加载全部模型
from app.db.session import engine, Base
from sqlalchemy import text, inspect

ALTERS = [
    # ③ 账户层
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS current_session_id VARCHAR(36)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_verified_at TIMESTAMPTZ",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS cancellation_requested_at TIMESTAMPTZ",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS cancel_reason_code VARCHAR(50)",
    # ② 记忆
    "ALTER TABLE user_psych_profile ADD COLUMN IF NOT EXISTS family_role_expectation JSON",
    # ④ 深访 Schema A/B 类 → user_profiles
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS education_institution VARCHAR(200)",
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS occupation_industry VARCHAR(50)",
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS occupation_role_type VARCHAR(30)",
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS income_band_aed VARCHAR(20)",
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS residence_emirate VARCHAR(20)",
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS residence_district VARCHAR(100)",
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS visa_type VARCHAR(40)",
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS has_children JSON",
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS relocation_plan VARCHAR(30)",
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS return_horizon_years INTEGER",
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS marriage_timeline VARCHAR(20)",
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS children_plan JSON",
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS parents_care_plan VARCHAR(30)",
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS cross_cultural_openness JSON",
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS distance_tolerance JSON",
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS interview_completed_at TIMESTAMPTZ",
    # ④ C 类 → match_preferences
    "ALTER TABLE match_preferences ADD COLUMN IF NOT EXISTS education_floor VARCHAR(20)",
    "ALTER TABLE match_preferences ADD COLUMN IF NOT EXISTS income_floor_band VARCHAR(20)",
    "ALTER TABLE match_preferences ADD COLUMN IF NOT EXISTS same_emirate_only BOOLEAN",
    "ALTER TABLE match_preferences ADD COLUMN IF NOT EXISTS dealbreakers JSON",
    "ALTER TABLE match_preferences ADD COLUMN IF NOT EXISTS elasticity JSON",
]


def run():
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        for stmt in ALTERS:
            conn.execute(text(stmt))
    tables = inspect(engine).get_table_names()
    print(f"migrated OK: {len(tables)} tables")


if __name__ == "__main__":
    run()

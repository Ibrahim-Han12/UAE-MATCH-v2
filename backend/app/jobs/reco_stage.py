"""
推荐流水线 cron 入口（D4=B：OS cron 触发独立脚本，幂等按周批次 ID）。

排程（PRD 6.1）：
    T-3 周二   python -m app.jobs.reco_stage --stage t3
    T-2 周三   python -m app.jobs.reco_stage --stage t2
    (T-1 周四 人工终审，走管理后台，无自动任务)
    T0  周五20:00  python -m app.jobs.reco_stage --stage t0
    到期关闭(每小时) python -m app.jobs.reco_stage --stage expire
batch_id 缺省 = 当前 ISO 周（如 2026-W33）；可 --batch 指定重跑。
"""
import argparse
import logging
from datetime import date

from app.db.session import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jobs.reco_stage")


def current_batch_id() -> str:
    y, w, _ = date.today().isocalendar()
    return f"{y}-W{w:02d}"


def run(stage: str, batch_id: str) -> dict:
    from app.core.matching import engine, letters, delivery
    db = SessionLocal()
    try:
        if stage == "t3":
            result = engine.run_stage_t3(db, batch_id)
        elif stage == "t2":
            result = letters.run_stage_t2(db, batch_id)
        elif stage == "t0":
            result = delivery.run_stage_t0(db, batch_id)
        elif stage == "expire":
            result = delivery.run_expire(db)
        else:
            raise SystemExit(f"未知 stage: {stage}")
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=["t3", "t2", "t0", "expire"])
    parser.add_argument("--batch", default=None)
    args = parser.parse_args()
    out = run(args.stage, args.batch or current_batch_id())
    logger.info("stage=%s result=%s", args.stage, out)

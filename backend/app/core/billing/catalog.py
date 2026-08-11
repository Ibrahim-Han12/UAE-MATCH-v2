"""商品目录加载（config/products.yaml 为唯一价格来源，BR-501）。"""
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

CONFIG_FILE = Path(__file__).resolve().parents[3] / "config" / "products.yaml"


@lru_cache(maxsize=1)
def load() -> dict:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_sku(sku_id: str) -> Optional[dict]:
    return load()["skus"].get(sku_id)


def get_coupon(code: str) -> Optional[dict]:
    return (load().get("coupons") or {}).get(code)


def currency() -> str:
    return load()["meta"]["currency"]

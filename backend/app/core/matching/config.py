"""匹配配置加载（config/matching_config.yaml 为唯一权重/阈值来源）。"""
from functools import lru_cache
from pathlib import Path

import yaml

CONFIG_FILE = Path(__file__).resolve().parents[3] / "config" / "matching_config.yaml"


@lru_cache(maxsize=1)
def load() -> dict:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def reload() -> dict:
    load.cache_clear()
    return load()

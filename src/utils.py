from __future__ import annotations

from typing import Any, Dict, List
import orjson


def to_pretty_json(data: Any) -> str:
    try:
        return orjson.dumps(data, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS).decode()
    except Exception:
        return str(data)


def clamp_days(num_days: int, min_days: int = 1, max_days: int = 30) -> int:
    return max(min_days, min(max_days, num_days))



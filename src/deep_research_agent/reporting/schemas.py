"""Phase 01 JSON Schema 加载与校验辅助。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCHEMAS_DIR = PROJECT_ROOT / "schemas"


def _schema_path(schema_name: str) -> Path:
    return SCHEMAS_DIR / f"{schema_name}.schema.json"


@lru_cache(maxsize=None)
def load_schema(schema_name: str) -> dict[str, Any]:
    """加载指定 schema。"""
    path = _schema_path(schema_name)
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=None)
def _validator(schema_name: str) -> Draft202012Validator:
    schema = load_schema(schema_name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_instance(schema_name: str, instance: Any) -> None:
    """按 schema 校验实例。"""
    _validator(schema_name).validate(instance)

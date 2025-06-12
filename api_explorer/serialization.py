"""
JSON serialization utilities for high-performance data transmission.
"""

import json
import logging
from typing import Dict, Any

# Try to import orjson for faster JSON serialization
try:
    import orjson

    HAS_ORJSON = True
    print("Using orjson for high-performance JSON serialization")
except ImportError:
    HAS_ORJSON = False
    print("orjson not available, using standard json with optimizations")


class FastJSONSerializer:
    """Optimized JSON serializer with caching and performance optimizations."""

    def __init__(self) -> None:
        self._template_cache: Dict[str, Dict[str, Any]] = {}
        self._field_cache: Dict[str, Any] = {}

    def serialize_event(self, event_data: Dict[str, Any], compact: bool = False) -> str:
        """Serialize event data with optimizations."""
        try:
            if HAS_ORJSON:
                return self._serialize_with_orjson(event_data, compact)
            else:
                return self._serialize_with_stdlib(event_data, compact)
        except Exception as e:
            logging.error(f"JSON serialization error: {e}")
            # Fallback to safe serialization
            return self._safe_serialize(event_data)

    def _serialize_with_orjson(self, data: Dict[str, Any], compact: bool) -> str:
        """Serialize using orjson (fastest option)."""
        if compact:
            return orjson.dumps(data, option=orjson.OPT_SERIALIZE_NUMPY).decode()
        else:
            return orjson.dumps(data).decode()

    def _serialize_with_stdlib(self, data: Dict[str, Any], compact: bool) -> str:
        """Optimized stdlib JSON serialization."""
        if compact:
            return json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        else:
            return json.dumps(data, ensure_ascii=False)

    def _safe_serialize(self, data: Any) -> str:
        """Safe fallback serialization that handles any data type."""
        try:
            clean_data = self._sanitize_for_json(data)
            return json.dumps(clean_data, separators=(",", ":"), ensure_ascii=False)
        except Exception:
            return json.dumps({"error": "serialization_failed", "data": str(data)})

    def _sanitize_for_json(self, obj: Any) -> Any:
        """Sanitize data to make it JSON serializable."""
        if isinstance(obj, dict):
            return {k: self._sanitize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._sanitize_for_json(item) for item in obj]
        elif isinstance(obj, (int, float, str, bool)) or obj is None:
            return obj
        elif hasattr(obj, "__dict__"):
            return self._sanitize_for_json(obj.__dict__)
        else:
            return str(obj)

    def precompile_template(
        self, template_name: str, template_structure: Dict[str, Any]
    ) -> None:
        """Precompile common JSON templates for even faster serialization."""
        self._template_cache[template_name] = template_structure

    def serialize_from_template(self, template_name: str, data: Dict[str, Any]) -> str:
        """Serialize using a precompiled template."""
        if template_name not in self._template_cache:
            return self.serialize_event(data, compact=True)

        template = self._template_cache[template_name].copy()
        self._fill_template(template, data)

        return self.serialize_event(template, compact=True)

    def _fill_template(self, template: Any, data: Dict[str, Any]) -> None:
        """Fill template with actual data."""
        if isinstance(template, dict):
            for key, value in template.items():
                if (
                    isinstance(value, str)
                    and value.startswith("${")
                    and value.endswith("}")
                ):
                    var_name = value[2:-1]
                    template[key] = data.get(var_name, None)
                elif isinstance(value, (dict, list)):
                    self._fill_template(value, data)
        elif isinstance(template, list):
            for item in template:
                self._fill_template(item, data)

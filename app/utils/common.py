import json
import hashlib
import uuid
from datetime import datetime, date
from typing import Any, Optional, Union, List, Dict
from pathlib import Path
import re

class CommonUtils:
    @staticmethod
    def generate_uuid() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def md5(s: str) -> str:
        return hashlib.md5(s.encode("utf-8")).hexdigest()

    @staticmethod
    def sha256(s: str) -> str:
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

    @staticmethod
    def to_json(obj: Any, indent: int = 2) -> str:
        def default(obj):
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            if hasattr(obj, "__dict__"):
                return obj.__dict__
            return str(obj)
        return json.dumps(obj, default=default, ensure_ascii=False, indent=indent)

    @staticmethod
    def from_json(s: str) -> Any:
        return json.loads(s)

    @staticmethod
    def safe_get(d: dict, key: str, default: Any = None) -> Any:
        if not isinstance(d, dict):
            return default
        keys = key.split(".")
        value = d
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    @staticmethod
    def ensure_dir(path: Union[str, Path]) -> Path:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @staticmethod
    def is_none_or_empty(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str) and value.strip() == "":
            return True
        if isinstance(value, (list, dict)) and len(value) == 0:
            return True
        return False

class StringUtils:
    @staticmethod
    def is_blank(s: Optional[str]) -> bool:
        return s is None or s.strip() == ""

    @staticmethod
    def is_not_blank(s: Optional[str]) -> bool:
        return not StringUtils.is_blank(s)

    @staticmethod
    def truncate(s: str, max_length: int, suffix: str = "...") -> str:
        if len(s) <= max_length:
            return s
        return s[:max_length - len(suffix)] + suffix

    @staticmethod
    def camel_to_snake(s: str) -> str:
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", s)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    @staticmethod
    def snake_to_camel(s: str) -> str:
        parts = s.split("_")
        return parts[0] + "".join(p.title() for p in parts[1:])

    @staticmethod
    def mask_email(email: str) -> str:
        if "@" not in email:
            return email
        parts = email.split("@")
        name = parts[0]
        if len(name) <= 2:
            return name[0] + "*" + "@" + parts[1]
        return name[0] + "*" * (len(name) - 2) + name[-1] + "@" + parts[1]

    @staticmethod
    def mask_phone(phone: str) -> str:
        if len(phone) < 7:
            return phone
        return phone[:3] + "****" + phone[-4:]

class NumberUtils:
    @staticmethod
    def is_numeric(s: str) -> bool:
        try:
            float(s)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def is_integer(s: str) -> bool:
        try:
            int(s)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def safe_int(value: Any, default: int = 0) -> int:
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_float(value: Any, default: float = 0.0) -> float:
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def clamp(value: Union[int, float], min_val: Union[int, float], max_val: Union[int, float]) -> Union[int, float]:
        return max(min_val, min(max_val, value))

class DateTimeUtils:
    @staticmethod
    def now() -> datetime:
        return datetime.now()

    @staticmethod
    def now_str(format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        return datetime.now().strftime(format_str)

    @staticmethod
    def today() -> date:
        return date.today()

    @staticmethod
    def today_str(format_str: str = "%Y-%m-%d") -> str:
        return date.today().strftime(format_str)

    @staticmethod
    def to_str(dt: Union[datetime, date], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        return dt.strftime(format_str)

    @staticmethod
    def from_str(s: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
        return datetime.strptime(s, format_str)

    @staticmethod
    def timestamp() -> int:
        return int(datetime.now().timestamp())

    @staticmethod
    def timestamp_ms() -> int:
        return int(datetime.now().timestamp() * 1000)

    @staticmethod
    def from_timestamp(ts: int) -> datetime:
        return datetime.fromtimestamp(ts / 1000 if ts > 9999999999 else ts)

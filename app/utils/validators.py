import re
from typing import Any, Optional, List, Dict, Callable, TypeVar
from dataclasses import dataclass
from ..core.exceptions import raise_validation

T = TypeVar("T")

@dataclass
class ValidationRule:
    name: str
    validator: Callable[[Any], bool]
    message: str

class Validator:
    def __init__(self):
        self.rules: Dict[str, List[ValidationRule]] = {}
        self.errors: Dict[str, str] = {}

    def add_rule(self, field: str, rule: ValidationRule) -> "Validator":
        if field not in self.rules:
            self.rules[field] = []
        self.rules[field].append(rule)
        return self

    def validate(self, data: Dict[str, Any], raise_exception: bool = True) -> bool:
        self.errors.clear()

        for field, rules in self.rules.items():
            value = data.get(field) if isinstance(data, dict) else getattr(data, field, None)

            for rule in rules:
                if not rule.validator(value):
                    if field not in self.errors:
                        self.errors[field] = rule.message
                    if raise_exception:
                        raise_validation(f"{field}: {rule.message}")

        return len(self.errors) == 0

    def get_errors(self) -> Dict[str, str]:
        return self.errors.copy()

def validate_required(value: Any, field_name: str = "此字段") -> bool:
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    if isinstance(value, (list, dict)) and len(value) == 0:
        return False
    return True

def validate_range(value: Any, min_val: Optional[float] = None, max_val: Optional[float] = None) -> bool:
    if value is None:
        return True

    try:
        num = float(value)
        if min_val is not None and num < min_val:
            return False
        if max_val is not None and num > max_val:
            return False
        return True
    except (ValueError, TypeError):
        return False

def validate_pattern(value: Any, pattern: str) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    return bool(re.match(pattern, value))

def validate_length(value: Any, min_len: Optional[int] = None, max_len: Optional[int] = None) -> bool:
    if value is None:
        return True

    length = len(str(value)) if isinstance(value, (str, int, float)) else len(value)

    if min_len is not None and length < min_len:
        return False
    if max_len is not None and length > max_len:
        return False
    return True

def validate_email(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, value))

def validate_phone(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    pattern = r"^1[3-9]\d{9}$"
    return bool(re.match(pattern, value))

def validate_list(value: Any, min_count: Optional[int] = None, max_count: Optional[int] = None) -> bool:
    if value is None:
        return True
    if not isinstance(value, list):
        return False
    if min_count is not None and len(value) < min_count:
        return False
    if max_count is not None and len(value) > max_count:
        return False
    return True

def validate_enum(value: Any, allowed: List[Any]) -> bool:
    if value is None:
        return True
    return value in allowed

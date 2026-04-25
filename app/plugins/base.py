from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Type
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class PluginContext:
    plugin_name: str
    plugin_version: str = "1.0.0"
    request_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    extra: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.extra.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.extra[key] = value

@dataclass
class PluginResult:
    success: bool = True
    data: Optional[Any] = None
    message: str = "执行成功"
    code: int = 0
    error_details: Optional[Dict[str, Any]] = None

    @classmethod
    def ok(cls, data: Any = None, message: str = "执行成功") -> "PluginResult":
        return cls(success=True, data=data, message=message)

    @classmethod
    def fail(cls, message: str = "执行失败", code: int = -1, details: Optional[Dict[str, Any]] = None) -> "PluginResult":
        return cls(success=False, message=message, code=code, error_details=details)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "code": self.code,
            "error_details": self.error_details,
        }

@dataclass
class PluginParam:
    name: str
    type: Type = str
    required: bool = True
    default: Any = None
    description: str = ""
    validators: List = field(default_factory=list)

@dataclass
class PluginMeta:
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    params: List[PluginParam] = field(default_factory=list)
    enabled: bool = True
    deprecated: bool = False

class BasePlugin(ABC):
    meta: PluginMeta

    def __init__(self):
        if not hasattr(self, "meta") or self.meta is None:
            raise ValueError(f"Plugin {self.__class__.__name__} must define 'meta'")

    @abstractmethod
    async def execute(self, params: Dict[str, Any], context: PluginContext) -> PluginResult:
        pass

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        errors = []
        for param_meta in self.meta.params:
            value = params.get(param_meta.name, param_meta.default)

            if param_meta.required and value is None:
                errors.append(f"参数 '{param_meta.name}' 是必需的")
                continue

            if value is not None and not isinstance(value, param_meta.type):
                try:
                    value = param_meta.type(value)
                except (ValueError, TypeError):
                    errors.append(f"参数 '{param_meta.name}' 类型错误，期望 {param_meta.type.__name__}")

            for validator in param_meta.validators:
                if hasattr(validator, "__call__"):
                    if not validator(value):
                        errors.append(f"参数 '{param_meta.name}' 校验失败")

        return errors

    def get_info(self) -> Dict[str, Any]:
        return {
            "name": self.meta.name,
            "version": self.meta.version,
            "description": self.meta.description,
            "author": self.meta.author,
            "category": self.meta.category,
            "tags": self.meta.tags,
            "params": [
                {
                    "name": p.name,
                    "type": p.type.__name__,
                    "required": p.required,
                    "default": p.default,
                    "description": p.description,
                }
                for p in self.meta.params
            ],
            "enabled": self.meta.enabled,
            "deprecated": self.meta.deprecated,
        }

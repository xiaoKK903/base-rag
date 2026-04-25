from enum import Enum
from typing import Optional

class ErrorCodeEnum(Enum):
    SUCCESS = (0, "操作成功")
    FAIL = (-1, "操作失败")

    SYSTEM_ERROR = (500, "系统异常")
    SERVICE_ERROR = (501, "服务异常")
    INTERNAL_ERROR = (502, "内部错误")

    PARAM_ERROR = (400, "参数错误")
    VALIDATION_ERROR = (401, "参数校验失败")
    NOT_FOUND = (404, "资源不存在")
    METHOD_NOT_ALLOWED = (405, "方法不允许")

    PLUGIN_NOT_FOUND = (1001, "插件不存在")
    PLUGIN_DISABLED = (1002, "插件已禁用")
    PLUGIN_EXECUTE_ERROR = (1003, "插件执行错误")

    UNAUTHORIZED = (2001, "未授权访问")
    FORBIDDEN = (2002, "禁止访问")

class ErrorCode:
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message

    def with_message(self, message: str) -> "ErrorCode":
        return ErrorCode(self.code, message)

    def __eq__(self, other):
        if isinstance(other, ErrorCode):
            return self.code == other.code
        return False

    def __hash__(self):
        return hash(self.code)

for member in ErrorCodeEnum:
    setattr(ErrorCode, member.name, ErrorCode(*member.value))

def get_error_message(code: int) -> str:
    for member in ErrorCodeEnum:
        if member.value[0] == code:
            return member.value[1]
    return "未知错误"

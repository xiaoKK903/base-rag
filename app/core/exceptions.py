from .error_codes import ErrorCode, ErrorCodeEnum
from typing import Optional, Any

class BusinessException(Exception):
    def __init__(self, code: int, message: str, detail: Optional[Any] = None):
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(message)

    def __str__(self):
        return f"[{self.code}] {self.message}"

class ServiceException(BusinessException):
    def __init__(self, message: str = "服务异常", detail: Optional[Any] = None):
        super().__init__(ErrorCodeEnum.SERVICE_ERROR.value[0], message, detail)

class ValidationException(BusinessException):
    def __init__(self, message: str = "参数校验失败", detail: Optional[Any] = None):
        super().__init__(ErrorCodeEnum.VALIDATION_ERROR.value[0], message, detail)

class NotFoundException(BusinessException):
    def __init__(self, message: str = "资源不存在", detail: Optional[Any] = None):
        super().__init__(ErrorCodeEnum.NOT_FOUND.value[0], message, detail)

class PluginException(BusinessException):
    def __init__(self, code: int = ErrorCodeEnum.PLUGIN_EXECUTE_ERROR.value[0], 
                 message: str = "插件执行错误", detail: Optional[Any] = None):
        super().__init__(code, message, detail)

def raise_business(code: int, message: str, detail: Optional[Any] = None):
    raise BusinessException(code, message, detail)

def raise_not_found(message: str = "资源不存在", detail: Optional[Any] = None):
    raise NotFoundException(message, detail)

def raise_validation(message: str = "参数校验失败", detail: Optional[Any] = None):
    raise ValidationException(message, detail)

def raise_plugin(message: str = "插件执行错误", detail: Optional[Any] = None):
    raise PluginException(message=message, detail=detail)

from typing import Any, Generic, Optional, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field
from .error_codes import ErrorCode, ErrorCodeEnum

T = TypeVar("T")

class R(BaseModel, Generic[T]):
    code: int = Field(default=0, description="状态码")
    message: str = Field(default="操作成功", description="消息")
    data: Optional[T] = Field(default=None, description="数据")
    timestamp: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000), description="时间戳")

    @classmethod
    def ok(cls, data: T = None, message: str = "操作成功") -> "R[T]":
        return cls(code=ErrorCodeEnum.SUCCESS.value[0], message=message, data=data)

    @classmethod
    def fail(cls, code: int = ErrorCodeEnum.FAIL.value[0], message: str = "操作失败", data: T = None) -> "R[T]":
        return cls(code=code, message=message, data=data)

    @classmethod
    def error(cls, error_code: ErrorCode, data: T = None) -> "R[T]":
        return cls(code=error_code.code, message=error_code.message, data=data)

    @classmethod
    def not_found(cls, message: str = "资源不存在") -> "R[T]":
        return cls(code=ErrorCodeEnum.NOT_FOUND.value[0], message=message)

    @classmethod
    def param_error(cls, message: str = "参数错误") -> "R[T]":
        return cls(code=ErrorCodeEnum.PARAM_ERROR.value[0], message=message)

    @classmethod
    def unauthorized(cls, message: str = "未授权访问") -> "R[T]":
        return cls(code=ErrorCodeEnum.UNAUTHORIZED.value[0], message=message)

class PageInfo(BaseModel):
    page: int = Field(ge=1, default=1, description="当前页码")
    page_size: int = Field(ge=1, le=100, default=10, description="每页数量")
    total: int = Field(ge=0, default=0, description="总记录数")
    total_pages: int = Field(ge=0, default=0, description="总页数")

class PageResult(R[T], Generic[T]):
    page: Optional[PageInfo] = Field(default=None, description="分页信息")

    @classmethod
    def ok_page(cls, data: T, page: int, page_size: int, total: int) -> "PageResult[T]":
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        page_info = PageInfo(page=page, page_size=page_size, total=total, total_pages=total_pages)
        return cls(code=ErrorCodeEnum.SUCCESS.value[0], message="操作成功", data=data, page=page_info)

class ErrorResponse(BaseModel):
    code: int
    message: str
    detail: Optional[str] = None
    timestamp: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000))

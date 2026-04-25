from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from pathlib import Path
from typing import Any, Dict

from .config import settings
from .router import router
from .rag.router import rag_router
from .middleware import setup_middleware
from .core import (
    R, ErrorResponse,
    BusinessException, ServiceException, ValidationException, PluginException,
    logger, ErrorCodeEnum
)
from .plugins import plugin_manager, plugin_registry
from .rag.service import get_rag_service

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

setup_middleware(app)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(router, prefix="/api")
app.include_router(rag_router, prefix="/api/rag")

@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException) -> JSONResponse:
    logger.warning(f"业务异常 [{exc.code}]: {exc.message}")
    response = R.fail(code=exc.code, message=exc.message, data=exc.detail)
    return JSONResponse(status_code=200, content=response.model_dump())

@app.exception_handler(ServiceException)
async def service_exception_handler(request: Request, exc: ServiceException) -> JSONResponse:
    logger.error(f"服务异常: {exc.message}", exc_info=True)
    response = R.error(exc.code if hasattr(exc, 'code') else ErrorCodeEnum.SERVICE_ERROR.value[0], exc.detail)
    return JSONResponse(status_code=500, content=response.model_dump())

@app.exception_handler(ValidationException)
async def validation_exception_handler(request: Request, exc: ValidationException) -> JSONResponse:
    logger.warning(f"参数校验失败: {exc.message}")
    response = R.param_error(exc.message)
    response.code = exc.code
    response.data = exc.detail
    return JSONResponse(status_code=400, content=response.model_dump())

@app.exception_handler(PluginException)
async def plugin_exception_handler(request: Request, exc: PluginException) -> JSONResponse:
    logger.error(f"插件异常: {exc.message}", exc_info=True)
    response = R.fail(code=exc.code, message=exc.message, data=exc.detail)
    return JSONResponse(status_code=200, content=response.model_dump())

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for error in exc.errors():
        loc = ".".join(str(x) for x in error["loc"]) if error["loc"] else ""
        msg = f"{loc}: {error['msg']}" if loc else error["msg"]
        errors.append(msg)

    message = "; ".join(errors)
    logger.warning(f"请求参数验证失败: {message}")

    response = R.param_error(message)
    response.data = {"errors": exc.errors()}
    return JSONResponse(status_code=400, content=response.model_dump())

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"未处理异常: {str(exc)}", exc_info=True)
    response = R.fail(
        code=ErrorCodeEnum.SYSTEM_ERROR.value[0],
        message=ErrorCodeEnum.SYSTEM_ERROR.value[1] if not settings.DEBUG else str(exc),
    )
    return JSONResponse(status_code=500, content=response.model_dump())

@app.get("/")
async def serve_index():
    return FileResponse(BASE_DIR / "static" / "index.html")

@app.get("/tools")
async def serve_tools():
    return FileResponse(BASE_DIR / "static" / "tools.html")

@app.get("/settings")
async def serve_settings():
    return FileResponse(BASE_DIR / "static" / "settings.html")

@app.get("/rag")
async def serve_rag():
    return FileResponse(BASE_DIR / "static" / "rag.html")

def custom_openapi() -> Dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="插件化AI工具综合平台 - 支持RAG检索",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.on_event("startup")
async def startup_event():
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    logger.info(f"配置: DEBUG={settings.DEBUG}, PORT={settings.PORT}")

    plugin_count = len(plugin_registry.list_plugins())
    logger.info(f"已注册插件数量: {plugin_count}")

    rag_service = get_rag_service()
    logger.info(f"RAG服务初始化完成: {rag_service.get_document_count()} 个文档, {rag_service.get_vector_count()} 个向量")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"{settings.APP_NAME} 关闭中...")
    rag_service = get_rag_service()
    await rag_service.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )

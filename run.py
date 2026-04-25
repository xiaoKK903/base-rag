import os
import sys

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_PATH)

from app.config import settings

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print(f"  AI工具平台 v{settings.APP_VERSION}")
    print("=" * 60)
    print(f"  首页:     http://localhost:{settings.PORT}/")
    print(f"  RAG:      http://localhost:{settings.PORT}/rag")
    print(f"  API文档:  http://localhost:{settings.PORT}/docs")
    print(f"  ReDoc:    http://localhost:{settings.PORT}/redoc")
    print(f"  健康检查: http://localhost:{settings.PORT}/api/health")
    print("=" * 60)
    print(f"  HOST: {settings.HOST}")
    print(f"  PORT: {settings.PORT}")
    print(f"  DEBUG: {settings.DEBUG}")
    print(f"  热重载: 已启用 (修改代码后自动重启)")
    print("=" * 60)
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        reload_dirs=[os.path.join(BASE_PATH, "app")],
        log_level="debug" if settings.DEBUG else "info",
    )

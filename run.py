import os
import sys

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_PATH)

print(f"Working directory: {BASE_PATH}")
print(f"Static files path: {os.path.join(BASE_PATH, 'static')}")
print(f"Python path: {sys.path[:3]}")

from app.main import app
from app.config import settings

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print(f"  AI工具平台 v{settings.APP_VERSION}")
    print("=" * 60)
    print(f"  首页:     http://localhost:{settings.PORT}/")
    print(f"  API文档:  http://localhost:{settings.PORT}/docs")
    print(f"  ReDoc:    http://localhost:{settings.PORT}/redoc")
    print(f"  健康检查: http://localhost:{settings.PORT}/api/health")
    print("=" * 60)
    print(f"  HOST: {settings.HOST}")
    print(f"  PORT: {settings.PORT}")
    print(f"  DEBUG: {settings.DEBUG}")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level="debug",
        access_log=True,
    )

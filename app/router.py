from fastapi import APIRouter, Query
from typing import Optional
from .core import R, logger
from .plugins import plugin_manager, plugin_registry

router = APIRouter()

@router.get("/health")
async def health_check():
    logger.info("健康检查请求")
    return R.ok(data={"status": "ok"})

@router.get("/info")
async def get_info():
    return R.ok(data={
        "app_name": "AI工具平台",
        "version": "0.1.0",
        "plugin_count": len(plugin_registry.list_plugins()),
        "categories": plugin_manager.list_categories(),
    })

@router.get("/plugins")
async def list_plugins(
    category: Optional[str] = Query(None, description="按分类筛选"),
    include_disabled: bool = Query(False, description="是否包含已禁用插件")
):
    logger.info(f"获取插件列表: category={category}, include_disabled={include_disabled}")
    plugins = plugin_manager.list_plugins(category=category, include_disabled=include_disabled)
    return R.ok(data=plugins)

@router.get("/plugins/{plugin_name}")
async def get_plugin(plugin_name: str):
    logger.info(f"获取插件信息: {plugin_name}")
    info = plugin_manager.get_plugin_info(plugin_name)
    if not info:
        return R.not_found(f"插件 '{plugin_name}' 不存在")
    return R.ok(data=info)

@router.get("/categories")
async def list_categories():
    categories = plugin_manager.list_categories()
    return R.ok(data=categories)

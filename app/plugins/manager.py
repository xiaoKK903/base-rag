from typing import Dict, Any, Optional, List
from ..core.logger import logger
from ..core.exceptions import PluginException, raise_plugin
from ..core.error_codes import ErrorCodeEnum
from .base import BasePlugin, PluginResult, PluginContext, PluginMeta
from .registry import plugin_registry

class PluginManager:
    def __init__(self):
        self._registry = plugin_registry

    def list_plugins(self, category: Optional[str] = None, include_disabled: bool = False) -> List[Dict[str, Any]]:
        plugins = []

        if category:
            instances = self._registry.get_by_category(category)
        else:
            instances = list(self._registry.get_all().values())

        for instance in instances:
            if not include_disabled and not instance.meta.enabled:
                continue
            plugins.append(instance.get_info())

        return plugins

    def get_plugin_info(self, name: str) -> Optional[Dict[str, Any]]:
        plugin = self._registry.get(name)
        return plugin.get_info() if plugin else None

    def plugin_exists(self, name: str) -> bool:
        return self._registry.exists(name)

    async def execute_plugin(self, name: str, params: Dict[str, Any],
                              request_id: str = "", extra: Optional[Dict[str, Any]] = None) -> PluginResult:
        logger.info(f"执行插件: {name}, 请求ID: {request_id}")

        plugin = self._registry.get(name)
        if not plugin:
            logger.error(f"插件不存在: {name}")
            raise_plugin(f"插件 '{name}' 不存在")

        if not plugin.meta.enabled:
            logger.error(f"插件已禁用: {name}")
            raise_plugin(f"插件 '{name}' 已禁用", code=ErrorCodeEnum.PLUGIN_DISABLED.value[0])

        errors = plugin.validate_params(params)
        if errors:
            error_msg = "; ".join(errors)
            logger.error(f"参数校验失败: {name} - {error_msg}")
            raise_plugin(error_msg, code=ErrorCodeEnum.VALIDATION_ERROR.value[0])

        context = PluginContext(
            plugin_name=name,
            plugin_version=plugin.meta.version,
            request_id=request_id,
            extra=extra or {},
        )

        try:
            logger.info(f"开始执行插件: {name}")
            result = await plugin.execute(params, context)

            if result.success:
                logger.info(f"插件执行成功: {name}")
            else:
                logger.warning(f"插件执行失败: {name} - {result.message}")

            return result

        except Exception as e:
            logger.error(f"插件执行异常: {name} - {str(e)}", exc_info=True)
            raise_plugin(f"插件执行异常: {str(e)}", details={"error": str(e)})

    def enable_plugin(self, name: str) -> bool:
        plugin = self._registry.get(name)
        if plugin:
            plugin.meta.enabled = True
            logger.info(f"插件已启用: {name}")
            return True
        return False

    def disable_plugin(self, name: str) -> bool:
        plugin = self._registry.get(name)
        if plugin:
            plugin.meta.enabled = False
            logger.info(f"插件已禁用: {name}")
            return True
        return False

    def list_categories(self) -> List[str]:
        return self._registry.list_categories()

plugin_manager = PluginManager()

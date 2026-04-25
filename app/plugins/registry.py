from typing import Dict, Type, Optional, List, Any
from ..core.logger import logger
from .base import BasePlugin

class PluginRegistry:
    def __init__(self):
        self._plugins: Dict[str, Type[BasePlugin]] = {}
        self._instances: Dict[str, BasePlugin] = {}
        self._categories: Dict[str, List[str]] = {}

    def register(self, plugin_class: Type[BasePlugin]) -> None:
        if not issubclass(plugin_class, BasePlugin):
            raise ValueError(f"{plugin_class} 必须继承自 BasePlugin")

        instance = plugin_class()
        name = instance.meta.name

        if name in self._plugins:
            logger.warning(f"插件 '{name}' 已存在，将被覆盖")

        self._plugins[name] = plugin_class
        self._instances[name] = instance

        category = instance.meta.category
        if category not in self._categories:
            self._categories[category] = []
        if name not in self._categories[category]:
            self._categories[category].append(name)

        logger.info(f"插件 '{name}' 已注册")

    def unregister(self, name: str) -> bool:
        if name in self._plugins:
            del self._plugins[name]
            if name in self._instances:
                del self._instances[name]

            for category, plugins in self._categories.items():
                if name in plugins:
                    plugins.remove(name)

            logger.info(f"插件 '{name}' 已注销")
            return True
        return False

    def get(self, name: str) -> Optional[BasePlugin]:
        return self._instances.get(name)

    def get_class(self, name: str) -> Optional[Type[BasePlugin]]:
        return self._plugins.get(name)

    def get_all(self) -> Dict[str, BasePlugin]:
        return self._instances.copy()

    def list_plugins(self) -> List[str]:
        return list(self._plugins.keys())

    def list_categories(self) -> List[str]:
        return list(self._categories.keys())

    def get_by_category(self, category: str) -> List[BasePlugin]:
        names = self._categories.get(category, [])
        return [self._instances[name] for name in names if name in self._instances]

    def exists(self, name: str) -> bool:
        return name in self._plugins

    def clear(self) -> None:
        self._plugins.clear()
        self._instances.clear()
        self._categories.clear()
        logger.info("插件注册表已清空")

plugin_registry = PluginRegistry()

def register_plugin(plugin_class: Type[BasePlugin]) -> Type[BasePlugin]:
    plugin_registry.register(plugin_class)
    return plugin_class

def plugin(name: str = "", version: str = "1.0.0", description: str = "",
           category: str = "general", tags: List[str] = None):
    def decorator(cls):
        if not hasattr(cls, "meta"):
            from .base import PluginMeta
            cls.meta = PluginMeta(
                name=name or cls.__name__.lower().replace("plugin", ""),
                version=version,
                description=description,
                category=category,
                tags=tags or [],
            )
        plugin_registry.register(cls)
        return cls
    return decorator

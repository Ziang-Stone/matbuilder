# -*- coding: utf-8 -*-
"""
插件管理器：发现、加载、管理插件
"""

import os
import importlib
import pkgutil
from typing import Dict, Type, List, Optional

from matbuilder.plugins.base import PluginBase
from matbuilder.utils.logging import Logger


class PluginManager:
    """插件管理器（单例）"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._plugins: Dict[str, PluginBase] = {}
            cls._instance._loaded = False
        return cls._instance

    def discover_and_load(self):
        """发现并加载所有内置及外部插件"""
        if self._loaded:
            return

        Logger.info("Loading plugins...")

        # 1. 加载内置插件 (matbuilder.plugins.builtin)
        try:
            import matbuilder.plugins.builtin as builtin_pkg
            for _, modname, _ in pkgutil.iter_modules(builtin_pkg.__path__, builtin_pkg.__name__ + "."):
                self._load_module(modname)
        except Exception as e:
            Logger.warn(f"Failed to load builtin plugins: {e}")

        # 2. 加载外部插件 (~/.matbuilder/plugins/)
        user_plugin_dir = os.path.expanduser("~/.matbuilder/plugins")
        if os.path.exists(user_plugin_dir):
            sys_path_added = False
            if user_plugin_dir not in sys.path:
                sys.path.insert(0, user_plugin_dir)
                sys_path_added = True
            try:
                for fname in os.listdir(user_plugin_dir):
                    if fname.endswith(".py") and not fname.startswith("_"):
                        modname = fname[:-3]
                        self._load_module(modname)
            finally:
                if sys_path_added and user_plugin_dir in sys.path:
                    sys.path.remove(user_plugin_dir)

        self._loaded = True
        Logger.info(f"Loaded {len(self._plugins)} plugin(s): {list(self._plugins.keys())}")

    def _load_module(self, modname: str):
        """加载单个模块，并注册其中的插件类"""
        try:
            module = importlib.import_module(modname)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, PluginBase) and 
                    attr != PluginBase and
                    attr.name != "abstract_plugin"):
                    plugin_instance = attr()
                    if plugin_instance.enabled:
                        self._plugins[plugin_instance.name] = plugin_instance
                        Logger.info(f"  Loaded plugin: {plugin_instance.name} v{plugin_instance.version}")
        except Exception as e:
            Logger.warn(f"  Failed to load plugin {modname}: {e}")

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        return self._plugins.get(name)

    def list_plugins(self) -> Dict[str, PluginBase]:
        return self._plugins

    def enable_plugin(self, name: str):
        if name in self._plugins:
            self._plugins[name].enabled = True

    def disable_plugin(self, name: str):
        if name in self._plugins:
            self._plugins[name].enabled = False

    def trigger_hook_point(self, hook_point, hook_ctx):
        """触发某个事件点，所有已加载且启用的插件会自动响应"""
        from matbuilder.core.hooks import hooks
        return hooks.trigger(hook_point, hook_ctx)


# 全局单例
plugin_manager = PluginManager()
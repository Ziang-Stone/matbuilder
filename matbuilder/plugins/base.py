# -*- coding: utf-8 -*-
"""
插件基类定义
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from matbuilder.core.hooks import HookPoint, HookContext


class PluginBase(ABC):
    """所有插件必须继承的基类"""
    
    name: str = "abstract_plugin"
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    enabled: bool = True   # 是否启用，可由 CLI 切换

    def __init__(self):
        self._register_hooks()

    def _register_hooks(self):
        """自动注册插件中定义的所有钩子方法"""
        from matbuilder.core.hooks import hooks, HookPoint
        
        # 遍历所有 HookPoint，检查插件是否实现了对应的 on_<event> 方法
        for hp in HookPoint:
            method_name = f"on_{hp.value}"
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                if callable(method):
                    hooks.register(hp, method)

    # ---------- 插件生命周期方法（可选重写） ----------
    def on_install(self):
        """插件安装时调用"""
        pass

    def on_uninstall(self):
        """插件卸载时调用"""
        pass

    # ---------- 业务钩子方法（子类按需重写） ----------
    def on_before_load(self, ctx: HookContext) -> HookContext:
        return ctx

    def on_after_load(self, ctx: HookContext) -> HookContext:
        return ctx

    def on_before_strain(self, ctx: HookContext) -> HookContext:
        return ctx

    def on_after_strain(self, ctx: HookContext) -> HookContext:
        return ctx

    def on_before_convert(self, ctx: HookContext) -> HookContext:
        return ctx

    def on_after_convert(self, ctx: HookContext) -> HookContext:
        return ctx

    def on_before_write(self, ctx: HookContext) -> HookContext:
        return ctx

    def on_after_write(self, ctx: HookContext) -> HookContext:
        return ctx

    def __repr__(self):
        return f"<Plugin {self.name} v{self.version}>"
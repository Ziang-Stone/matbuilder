# -*- coding: utf-8 -*-
"""
事件钩子系统 — 插件与主流程的通信桥梁
"""

from typing import Dict, List, Callable, Any
from enum import Enum
from dataclasses import dataclass, field


class HookPoint(Enum):
    """定义所有可注入的事件点"""
    BEFORE_LOAD = "before_load"
    AFTER_LOAD = "after_load"
    BEFORE_STRAIN = "before_strain"
    AFTER_STRAIN = "after_strain"
    BEFORE_TRANSFORM = "before_transform"
    AFTER_TRANSFORM = "after_transform"
    BEFORE_CONVERT = "before_convert"
    AFTER_CONVERT = "after_convert"
    BEFORE_BEND = "before_bend"
    AFTER_BEND = "after_bend"
    BEFORE_WRITE = "before_write"
    AFTER_WRITE = "after_write"


@dataclass
class HookContext:
    """事件上下文，携带当前运行状态"""
    event: HookPoint
    context: Any = None          # 主 Context 对象
    structure: Any = None        # 当前结构对象
    params: Dict = field(default_factory=dict)  # 步骤参数
    result: Any = None           # 步骤返回值


class HookManager:
    """全局钩子管理器（单例）"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._listeners: Dict[HookPoint, List[Callable]] = {
                hp: [] for hp in HookPoint
            }
        return cls._instance

    def register(self, hook_point: HookPoint, callback: Callable):
        """注册一个回调函数到指定事件点"""
        if hook_point not in self._listeners:
            self._listeners[hook_point] = []
        self._listeners[hook_point].append(callback)

    def unregister(self, hook_point: HookPoint, callback: Callable):
        """移除回调"""
        if hook_point in self._listeners and callback in self._listeners[hook_point]:
            self._listeners[hook_point].remove(callback)

    def trigger(self, hook_point: HookPoint, hook_ctx: HookContext) -> HookContext:
        """触发事件，依次执行所有注册的回调"""
        if hook_point not in self._listeners:
            return hook_ctx
        for cb in self._listeners[hook_point]:
            try:
                hook_ctx = cb(hook_ctx)
            except Exception as e:
                print(f"  [Plugin Error] {cb.__name__}: {e}")
        return hook_ctx

    def clear(self):
        """清空所有监听（用于测试）"""
        for hp in HookPoint:
            self._listeners[hp] = []


# 全局单例实例
hooks = HookManager()
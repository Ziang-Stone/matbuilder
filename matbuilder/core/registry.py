# -*- coding: utf-8 -*-
"""
模块注册器 — 自动发现业务模块
"""

from typing import Dict, Type


class ModuleRegistry:
    """模块注册表 — 单例"""
    
    _modules: Dict[str, Type] = {}
    
    @classmethod
    def register(cls, module_class: Type):
        """注册模块"""
        cls._modules[module_class.name] = module_class
        # print(f"[Registry] Registered: {module_class.name}")
    
    @classmethod
    def get(cls, name: str) -> Type:
        """获取模块类"""
        return cls._modules.get(name)
    
    @classmethod
    def list_modules(cls) -> Dict[str, Type]:
        """列出所有已注册模块"""
        return cls._modules.copy()
    
    @classmethod
    def clear(cls):
        """清空（测试用）"""
        cls._modules.clear()

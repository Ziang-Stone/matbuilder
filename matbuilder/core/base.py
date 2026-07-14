# -*- coding: utf-8 -*-
"""
基类定义：Module 基类 + Backend 基类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BackendBase(ABC):
    """后端适配器基类"""
    
    name: str = "abstract"
    
    @abstractmethod
    def load_structure(self, filepath: str) -> Any:
        """加载结构文件，返回后端原生对象"""
        pass
    
    @abstractmethod
    def write_structure(self, structure: Any, filepath: str, **kwargs) -> None:
        """写入结构文件"""
        pass
    
    @abstractmethod
    def get_lattice_params(self, structure: Any) -> Dict[str, float]:
        """获取晶格参数 a, b, c, alpha, beta, gamma"""
        pass
    
    @abstractmethod
    def apply_strain(self, structure: Any, strain_matrix) -> Any:
        """应用应变矩阵，返回新结构"""
        pass


class ModuleBase(ABC):
    """业务模块基类 — 自动注册"""
    
    name: str = "abstract"
    description: str = ""
    
    def __init_subclass__(cls, **kwargs):
        """子类自动注册"""
        super().__init_subclass__(**kwargs)
        from .registry import ModuleRegistry
        if cls.name != "abstract":
            ModuleRegistry.register(cls)
    
    @abstractmethod
    def run(self, context) -> None:
        """模块主入口"""
        pass
    
    @abstractmethod
    def run_interactive(self, context) -> None:
        """交互式入口"""
        pass

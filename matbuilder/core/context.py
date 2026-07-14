# -*- coding: utf-8 -*-
"""
运行时上下文 — 跨模块共享数据
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Context:
    """全局运行时上下文"""
    
    settings: Any = None           # Settings 实例
    backend: Any = None            # BackendBase 实例
    
    # 当前加载的结构
    structure: Any = None          # 后端原生结构对象
    structure_path: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 运行时状态
    work_dir: str = "."
    
    def has_structure(self) -> bool:
        return self.structure is not None
    
    def set_structure(self, structure: Any, filepath: str, metadata: Dict = None):
        self.structure = structure
        self.structure_path = filepath
        if metadata:
            self.metadata.update(metadata)

# -*- coding: utf-8 -*-
"""
全局配置 — v0.4 增强版
"""

import os
from dataclasses import dataclass, asdict, field


@dataclass
class Settings:
    """运行时配置"""
    
    # 路径
    struct_dir: str = "structs"
    input_file: str = "PCM.vasp"
    
    # 物理参数
    default_poisson: float = 0.30
    max_batch_files: int = 200
    
    # 后端
    backend: str = "pymatgen"
    
    # 输出
    output_coord_type: str = "same"
    
    # Transform 默认参数
    default_supercell: tuple = (2, 2, 2)
    default_rotation_axis: str = "z"
    default_rotation_angle: float = 90.0
    
    # Pipeline 配置（v0.4 新增）
    pipeline_dir: str = "workflows"
    pipeline_continue_on_error: bool = False
    
    @property
    def input_path(self) -> str:
        return os.path.join(self.struct_dir, self.input_file)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise ValueError(f"Unknown setting: {key}")
    
    def reset_defaults(self):
        default = Settings()
        for key in self.to_dict().keys():
            setattr(self, key, getattr(default, key))
    
    def get(self, key, default=None):
        """字典风格访问（v0.4 新增）"""
        return getattr(self, key, default)
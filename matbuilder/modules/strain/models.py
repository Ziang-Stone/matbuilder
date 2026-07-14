# -*- coding: utf-8 -*-
"""
应变模块数据模型
"""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class StrainConfig:
    """应变配置"""
    
    strain_type: Literal[
        'uniaxial', 'biaxial', 'shear', 
        'pure_shear', 'hydrostatic'
    ]
    direction: str
    start: float
    end: float
    step: float
    mode: Literal['standard', 'poisson', 'vol_conserve'] = 'standard'
    poisson: Optional[float] = None
    
    @property
    def count(self) -> int:
        """计算文件数量"""
        return int((self.end - self.start) / self.step) + 1
    
    def validate(self) -> bool:
        if self.step <= 0:
            return False
        if self.start > self.end:
            return False
        if self.mode == 'poisson' and (self.poisson is None or self.poisson < 0 or self.poisson >= 0.5):
            return False
        return True
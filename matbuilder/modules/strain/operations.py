# -*- coding: utf-8 -*-
"""
应变核心算法 — 与后端无关的纯数学操作
"""

import numpy as np
from typing import Tuple


class StrainOperations:
    """应变矩阵生成器"""
    
    @staticmethod
    def uniaxial(direction: str, value: float, 
                 mode: str = 'standard', poisson: float = None) -> np.ndarray:
        """
        单轴应变矩阵
        value: 小数应变
        """
        F = np.eye(3)
        
        if direction == 'a':
            F[0, 0] = 1.0 + value
            if mode == 'poisson' and poisson is not None:
                F[1, 1] = 1.0 - poisson * value
                F[2, 2] = 1.0 - poisson * value
            elif mode == 'vol_conserve':
                s = 1.0 / np.sqrt(1.0 + value)
                F[1, 1] = s
                F[2, 2] = s
        elif direction == 'b':
            F[1, 1] = 1.0 + value
            if mode == 'poisson' and poisson is not None:
                F[0, 0] = 1.0 - poisson * value
                F[2, 2] = 1.0 - poisson * value
            elif mode == 'vol_conserve':
                s = 1.0 / np.sqrt(1.0 + value)
                F[0, 0] = s
                F[2, 2] = s
        elif direction == 'c':
            F[2, 2] = 1.0 + value
            if mode == 'poisson' and poisson is not None:
                F[0, 0] = 1.0 - poisson * value
                F[1, 1] = 1.0 - poisson * value
            elif mode == 'vol_conserve':
                s = 1.0 / np.sqrt(1.0 + value)
                F[0, 0] = s
                F[1, 1] = s
        
        return F
    
    @staticmethod
    def biaxial(direction: str, value: float,
                mode: str = 'standard', poisson: float = None) -> np.ndarray:
        """双轴应变矩阵"""
        F = np.eye(3)
        
        if direction == 'ab':
            F[0, 0] = 1.0 + value
            F[1, 1] = 1.0 + value
            if mode == 'poisson' and poisson is not None:
                F[2, 2] = 1.0 - poisson * value
            elif mode == 'vol_conserve':
                F[2, 2] = 1.0 / (1.0 + value) ** 2
        elif direction == 'bc':
            F[1, 1] = 1.0 + value
            F[2, 2] = 1.0 + value
            if mode == 'poisson' and poisson is not None:
                F[0, 0] = 1.0 - poisson * value
            elif mode == 'vol_conserve':
                F[0, 0] = 1.0 / (1.0 + value) ** 2
        elif direction == 'ac':
            F[0, 0] = 1.0 + value
            F[2, 2] = 1.0 + value
            if mode == 'poisson' and poisson is not None:
                F[1, 1] = 1.0 - poisson * value
            elif mode == 'vol_conserve':
                F[1, 1] = 1.0 / (1.0 + value) ** 2
        
        return F
    
    @staticmethod
    def shear(direction: str, value: float) -> np.ndarray:
        """简单剪切矩阵 — 天然体积守恒"""
        F = np.eye(3)
        
        if direction == 'ab':   F[0, 1] = value
        elif direction == 'bc': F[1, 2] = value
        elif direction == 'ac': F[0, 2] = value
        elif direction == 'ba': F[1, 0] = value
        elif direction == 'cb': F[2, 1] = value
        elif direction == 'ca': F[2, 0] = value
        
        return F
    
    @staticmethod
    def pure_shear(direction: str, value: float) -> np.ndarray:
        """纯剪切矩阵 — 严格体积守恒"""
        F = np.eye(3)
        
        if direction == 'ab':
            F[0, 0] = 1.0 + value
            F[1, 1] = 1.0 / (1.0 + value)
        elif direction == 'bc':
            F[1, 1] = 1.0 + value
            F[2, 2] = 1.0 / (1.0 + value)
        elif direction == 'ac':
            F[0, 0] = 1.0 + value
            F[2, 2] = 1.0 / (1.0 + value)
        
        return F
    
    @staticmethod
    def hydrostatic(value: float) -> np.ndarray:
        """三轴静水压 — 各向同性"""
        return np.eye(3) * (1.0 + value)
    
    @classmethod
    def get_strain_matrix(cls, strain_type: str, direction: str, value: float,
                          mode: str = 'standard', poisson: float = None) -> np.ndarray:
        """统一入口"""
        if strain_type == 'uniaxial':
            return cls.uniaxial(direction, value, mode, poisson)
        elif strain_type == 'biaxial':
            return cls.biaxial(direction, value, mode, poisson)
        elif strain_type == 'shear':
            return cls.shear(direction, value)
        elif strain_type == 'pure_shear':
            return cls.pure_shear(direction, value)
        elif strain_type == 'hydrostatic':
            return cls.hydrostatic(value)
        else:
            raise ValueError(f"Unknown strain type: {strain_type}")
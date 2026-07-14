# -*- coding: utf-8 -*-
"""
业务模块包 — 显式注册所有模块
"""

from matbuilder.core.registry import ModuleRegistry

from .strain.module import StrainModule
from .transform.module import TransformModule
from .convert.module import ConvertModule
from .bend.module import BendModule
from .symmetry.module import SymmetryModule
from .struct2d.module import Struct2DModule          # ← 改为从 module 导入

ModuleRegistry.register(StrainModule)
ModuleRegistry.register(TransformModule)
ModuleRegistry.register(ConvertModule)
ModuleRegistry.register(BendModule)
ModuleRegistry.register(SymmetryModule)
ModuleRegistry.register(Struct2DModule)

__all__ = [
    "StrainModule", "TransformModule", "ConvertModule",
    "BendModule", "SymmetryModule", "Struct2DModule"
]
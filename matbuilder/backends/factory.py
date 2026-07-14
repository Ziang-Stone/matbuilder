# -*- coding: utf-8 -*-
"""
后端工厂 — 动态创建后端实例
"""

from .pymatgen import PymatgenBackend


class BackendFactory:
    """后端工厂"""
    
    _backends = {
        'pymatgen': PymatgenBackend,
        # 'ase': ASEBackend,  # v0.2 引入
    }
    
    @classmethod
    def create(cls, name: str = 'pymatgen'):
        if name not in cls._backends:
            raise ValueError(f"Unknown backend: {name}. Available: {list(cls._backends.keys())}")
        return cls._backends[name]()
    
    @classmethod
    def list_backends(cls):
        return list(cls._backends.keys())
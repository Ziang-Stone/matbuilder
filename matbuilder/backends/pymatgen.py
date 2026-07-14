# -*- coding: utf-8 -*-
"""
pymatgen 后端适配器
"""

import os
from typing import Dict, Any

import numpy as np
from pymatgen.core import Structure, Lattice
from pymatgen.io.vasp import Poscar

from .base import BackendBase


class PymatgenBackend(BackendBase):
    """pymatgen 后端实现"""
    
    name = "pymatgen"
    
    def load_structure(self, filepath: str) -> Structure:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        structure = Structure.from_file(filepath)
        
        # 提取原始坐标类型元数据
        metadata = self._extract_metadata(filepath)
        
        return structure, metadata
    
    def _extract_metadata(self, filepath: str) -> Dict[str, Any]:
        """提取 POSCAR 元数据"""
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        idx = 2
        line5 = lines[5].strip().split()
        try:
            float(line5[0])
            idx = 6
        except ValueError:
            idx = 7
        
        coord_header = lines[idx].strip()
        if coord_header[0].lower() == 's':
            idx += 1
            coord_type = lines[idx].strip()[0].upper()
        else:
            coord_type = coord_header[0].upper()
        
        return {
            'original_coord_type': 'C' if coord_type == 'C' else 'D',
            'source_file': filepath,
        }
    
    def write_structure(self, structure: Structure, filepath: str, coord_type: str = 'D') -> None:
        p = Poscar(structure)
        p.write_file(filepath)
    
    def get_lattice_params(self, structure: Structure) -> Dict[str, float]:
        lat = structure.lattice
        return {
            'a': lat.a, 'b': lat.b, 'c': lat.c,
            'alpha': lat.alpha, 'beta': lat.beta, 'gamma': lat.gamma
        }
    
    def apply_strain(self, structure: Structure, strain_matrix: np.ndarray) -> Structure:
        """
        应用一般应变矩阵（3×3）
        strain_matrix: 变形梯度 F，新 lattice = F @ 原 lattice
        """
        new_lat_matrix = strain_matrix @ structure.lattice.matrix
        new_structure = structure.copy()
        new_structure.lattice = Lattice(new_lat_matrix)
        return new_structure
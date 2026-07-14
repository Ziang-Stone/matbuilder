# -*- coding: utf-8 -*-
"""
struct2d.py - 二维材料建模模块 (MatBuilder 集成版 v0.6.0)

提供以下建模功能：
1. 表面切割法 (Slab Model)
2. 单层剥离法 (Monolayer Extraction)
3. 转角堆叠法 (Twist Stacking / 魔角构建)
4. 异质结构建法 (Heterostructure Stacking)
5. 缺陷与掺杂建模 (Defects & Doping)
6. 超晶格构建 (Superlattice)
7. 边缘/边界结构建模 (Edge & Nanoribbon)
8. 衬底与界面建模 (Substrate & Interface)
9. 滑移铁电结构生成 (Sliding Ferroelectricity)
"""

from __future__ import annotations

import os
import sys
import math
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pymatgen.*")
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Callable, Union, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
from datetime import datetime


import numpy as np
from numpy.linalg import norm, det, inv

# 导入 MatBuilder 模块基类
from matbuilder.core.base import ModuleBase
from matbuilder.utils.logging import Logger
from matbuilder.utils.validators import (
    get_float_input, get_int_input, get_choice_input, get_yes_no_input
)

# =============================================================================
# 改进的 ASE 导入检测（逐项导入，捕获具体错误）
# =============================================================================
HAS_ASE = False
ASE_IMPORT_ERRORS = []

try:
    from ase import Atoms
    from ase.io import read, write
    from ase.geometry import get_layers, wrap_positions
    from ase.constraints import FixAtoms, FixCartesian
    from ase.spacegroup import get_spacegroup
    HAS_ASE = True
except ImportError as e:
    ASE_IMPORT_ERRORS.append(f"ase 主模块导入失败: {e}")

if HAS_ASE:
    # 尝试导入 ase.build 中的函数（可能因版本而异）
    try:
        from ase.build import surface, add_adsorbate, fcc111, bcc110, hcp0001, diamond100
    except ImportError as e:
        ASE_IMPORT_ERRORS.append(f"ase.build 部分导入失败: {e}")
        warnings.warn(f"ASE 部分功能受限: {e}")
    try:
        from ase.build import mx2, graphene, nanotube, cut
        try:
            from ase.build import graphene_nanoribbon
            HAS_GRAPHENE_NANORIBBON = True
        except ImportError:
            HAS_GRAPHENE_NANORIBBON = False
    except ImportError as e:
        ASE_IMPORT_ERRORS.append(f"ase.build 中 mx2/graphene/nanotube/cut 导入失败: {e}")
        warnings.warn(f"ASE 高级构建函数不可用: {e}")
        # 定义占位函数，避免后续 NameError
        def mx2(*args, **kwargs):
            raise ImportError("mx2 不可用，请安装完整 ASE")
        def graphene(*args, **kwargs):
            raise ImportError("graphene 不可用，请安装完整 ASE")
        def nanotube(*args, **kwargs):
            raise ImportError("nanotube 不可用，请安装完整 ASE")
        def cut(*args, **kwargs):
            raise ImportError("cut 不可用，请安装完整 ASE")
        HAS_GRAPHENE_NANORIBBON = False

if not HAS_ASE:
    warnings.warn("ASE 未安装，部分功能将受限。建议: pip install ase")

# =============================================================================
# pymatgen 导入
# =============================================================================
HAS_PMG = False
try:
    from pymatgen.core import Structure, Lattice, Element, Composition
    from pymatgen.io.vasp import Poscar
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    from pymatgen.analysis.structure_matcher import StructureMatcher
    from pymatgen.core.surface import SlabGenerator, ReconstructionGenerator
    from pymatgen.analysis.interfaces import CoherentInterfaceBuilder
    HAS_PMG = True
except ImportError as e:
    warnings.warn(f"pymatgen 未安装: {e}。建议: pip install pymatgen")

# spglib
try:
    import spglib
    HAS_SPGLIB = True
except ImportError:
    HAS_SPGLIB = False

# scipy
try:
    from scipy.spatial import cKDTree
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    warnings.warn("scipy未安装，边缘钝化功能将受限。建议: pip install scipy")


# =============================================================================
# 常量与配置
# =============================================================================

MODULE_NAME = "struct2d"
MODULE_VERSION = "0.1.0"
MODULE_DESC = "二维材料与表面结构建模模块"

DEFAULT_VACUUM = 20.0
DEFAULT_SLAB_LAYERS = 4
DEFAULT_FIX_LAYERS = 2
DEFAULT_LAYER_TOLERANCE = 0.1

VDW_LAYER_SPACING = {
    'graphene': 3.35,
    'MoS2': 6.50,
    'WS2': 6.55,
    'MoSe2': 6.55,
    'WSe2': 6.60,
    'MoTe2': 6.98,
    'WTe2': 7.00,
    'BN': 3.33,
    'black_phosphorus': 5.25,
    'GaS': 7.70,
    'GaSe': 7.95,
    'InSe': 8.32,
    'Bi2Se3': 9.55,
    'Bi2Te3': 10.15,
    'Sb2Te3': 10.15,
    'CrI3': 6.80,
    'CrGeTe3': 7.05,
    'Fe3GeTe2': 8.05,
    'MnBi2Te4': 13.50,
}

SUBSTRATE_DATABASE = {
    'SiO2_quartz': {'a': 4.914, 'b': 4.914, 'c': 5.405, 'gamma': 120},
    'Si_111': {'a': 3.840, 'b': 3.840, 'c': 6.651, 'gamma': 60},
    'SiC_4H': {'a': 3.073, 'b': 3.073, 'c': 10.053, 'gamma': 120},
    'hBN': {'a': 2.504, 'b': 2.504, 'c': 6.661, 'gamma': 120},
    'Al2O3_0001': {'a': 4.759, 'b': 4.759, 'c': 12.991, 'gamma': 120},
    'Au_111': {'a': 2.884, 'b': 2.884, 'c': 7.065, 'gamma': 60},
    'Cu_111': {'a': 2.556, 'b': 2.556, 'c': 6.263, 'gamma': 60},
    'Ag_111': {'a': 2.889, 'b': 2.889, 'c': 7.071, 'gamma': 60},
    'Pt_111': {'a': 2.775, 'b': 2.775, 'c': 6.791, 'gamma': 60},
    'TiO2_rutile_110': {'a': 4.594, 'b': 4.594, 'c': 2.959, 'gamma': 90},
}


# =============================================================================
# 异常类
# =============================================================================

class Struct2DError(Exception):
    pass

class InputError(Struct2DError):
    pass

class StructureError(Struct2DError):
    pass

class DependencyError(Struct2DError):
    pass


# =============================================================================
# 数据类
# =============================================================================

@dataclass
class SlabConfig:
    miller_indices: Tuple[int, int, int] = (1, 1, 1)
    layers: int = DEFAULT_SLAB_LAYERS
    vacuum: float = DEFAULT_VACUUM
    fix_bottom_layers: int = DEFAULT_FIX_LAYERS
    fix_bottom_height: Optional[float] = None
    symmetric: bool = False
    adsorbate: Optional[str] = None
    adsorbate_height: float = 2.0
    supercell: Tuple[int, int, int] = (1, 1, 1)
    title: str = "Slab_Model"

@dataclass
class MonolayerConfig:
    layer_tolerance: float = DEFAULT_LAYER_TOLERANCE
    target_layer_index: Optional[int] = None
    vacuum: float = DEFAULT_VACUUM
    fix_in_plane: bool = False
    title: str = "Monolayer"

@dataclass
class TwistConfig:
    twist_angle: float = 1.05
    layer1_atoms: Optional[Atoms] = None
    layer2_atoms: Optional[Atoms] = None
    interlayer_distance: float = 3.35
    supercell_method: str = "atom_number"
    max_atoms: int = 500
    tolerance: float = 0.1
    title: str = "Twisted_Bilayer"

@dataclass
class HeteroConfig:
    bottom_layer: Optional[Atoms] = None
    top_layer: Optional[Atoms] = None
    interlayer_distance: float = 3.5
    vacuum: float = DEFAULT_VACUUM
    alignment: str = "center"
    custom_shift: Tuple[float, float] = (0.0, 0.0)
    strain_on: str = "none"
    max_strain: float = 0.05
    title: str = "Heterostructure"

@dataclass
class DefectConfig:
    defect_type: str = "vacancy"
    target_species: Optional[str] = None
    defect_species: Optional[str] = None
    defect_positions: Optional[List[int]] = None
    defect_concentration: Optional[float] = None
    random_doping: bool = False
    title: str = "Defective_Structure"

@dataclass
class SuperlatticeConfig:
    supercell_matrix: Optional[np.ndarray] = None
    stacking_sequence: Optional[List[str]] = None
    repeat_times: int = 1
    interlayer_spacings: Optional[List[float]] = None
    vacuum: float = DEFAULT_VACUUM
    title: str = "Superlattice"

@dataclass
class NanoribbonConfig:
    direction: str = "zigzag"
    width: int = 5
    length: Optional[int] = None
    edge_passivation: Optional[str] = None
    passivation_bond_length: float = 1.1
    vacuum_xy: float = 15.0
    vacuum_z: float = 20.0
    title: str = "Nanoribbon"

@dataclass
class SubstrateConfig:
    substrate_type: str = "custom"
    substrate_atoms: Optional[Atoms] = None
    adsorbate_atoms: Optional[Atoms] = None
    interface_distance: float = 3.0
    vacuum: float = DEFAULT_VACUUM
    fix_substrate: bool = True
    fix_layers: int = 2
    match_method: str = "strain"
    max_strain: float = 0.05
    max_rotation: float = 30.0
    title: str = "Substrate_Interface"

@dataclass
class SlidingFerroelectricConfig:
    slide_vector: Tuple[float, float] = (0.0, 0.0)
    slide_direction: str = "auto"
    slide_magnitude: Optional[float] = None
    slide_path: Optional[List[Tuple[float, float]]] = None
    interlayer_distance: Optional[float] = None
    vacuum: float = DEFAULT_VACUUM
    n_slide_points: int = 11
    fix_bottom_layer: bool = True
    fix_slide_layer: bool = False
    calculate_polarization: bool = False
    magnetic_order: Optional[str] = None
    title: str = "Sliding_Ferroelectric"


# =============================================================================
# 工具函数 (独立于 MatBuilder 的 utils)
# =============================================================================

def _check_dependencies() -> None:
    if not HAS_ASE:
        raise DependencyError("ASE 未安装，请执行: pip install ase")
    if not HAS_PMG:
        raise DependencyError("pymatgen 未安装，请执行: pip install pymatgen")

def _read_structure(filepath: Union[str, Path]) -> Atoms:
    _check_dependencies()
    filepath = Path(filepath)
    if not filepath.exists():
        raise InputError(f"文件不存在: {filepath}")
    try:
        atoms = read(str(filepath))
        if atoms is None:
            raise StructureError(f"无法读取结构文件: {filepath}")
        return atoms
    except Exception as e:
        raise StructureError(f"读取结构失败: {e}")

def _write_structure(atoms: Atoms, filepath: Union[str, Path],
                     fmt: Optional[str] = None) -> None:
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    try:
        write(str(filepath), atoms, format=fmt)
    except Exception as e:
        raise StructureError(f"写入结构失败: {e}")

def _atoms_to_pymatgen(atoms: Atoms) -> Structure:
    return Structure(
        lattice=Lattice(atoms.get_cell()),
        species=atoms.get_chemical_symbols(),
        coords=atoms.get_scaled_positions(),
        coords_are_cartesian=False
    )

def _pymatgen_to_atoms(structure: Structure) -> Atoms:
    return Atoms(
        symbols=[str(s) for s in structure.species],
        positions=structure.cart_coords,
        cell=structure.lattice.matrix,
        pbc=True
    )

def _add_vacuum(atoms: Atoms, vacuum: float, axis: int = 2) -> Atoms:
    cell = atoms.get_cell().copy()
    positions = atoms.get_positions()
    coords = positions[:, axis]
    z_min, z_max = coords.min(), coords.max()
    thickness = z_max - z_min
    new_height = thickness + vacuum
    old_height = cell[axis, axis]
    center_shift = (new_height - thickness) / 2 - z_min
    positions[:, axis] += center_shift
    cell[axis, :] = cell[axis, :] * (new_height / old_height)
    new_atoms = atoms.copy()
    new_atoms.set_cell(cell, scale_atoms=False)
    new_atoms.set_positions(positions)
    new_atoms.set_pbc([True, True, True])
    return new_atoms

def _fix_bottom_layers(atoms: Atoms, n_layers: int = DEFAULT_FIX_LAYERS,
                       axis: int = 2) -> Atoms:
    positions = atoms.get_positions()
    z_coords = positions[:, axis]
    sorted_z = np.sort(np.unique(np.round(z_coords, 2)))
    if len(sorted_z) < n_layers:
        warnings.warn(f"结构只有{len(sorted_z)}层，无法固定{n_layers}层")
        n_layers = len(sorted_z)
    threshold = sorted_z[n_layers - 1] + 0.05
    mask = z_coords <= threshold
    constraints = FixAtoms(mask=mask)
    new_atoms = atoms.copy()
    new_atoms.set_constraint(constraints)
    return new_atoms

def _fix_bottom_by_height(atoms: Atoms, height: float, axis: int = 2) -> Atoms:
    positions = atoms.get_positions()
    z_coords = positions[:, axis]
    z_min = z_coords.min()
    mask = z_coords <= (z_min + height)
    constraints = FixAtoms(mask=mask)
    new_atoms = atoms.copy()
    new_atoms.set_constraint(constraints)
    return new_atoms

def _get_rotation_matrix(angle: float, axis: str = 'z') -> np.ndarray:
    rad = np.radians(angle)
    if axis == 'z':
        return np.array([
            [np.cos(rad), -np.sin(rad), 0],
            [np.sin(rad), np.cos(rad), 0],
            [0, 0, 1]
        ])
    elif axis == 'x':
        return np.array([
            [1, 0, 0],
            [0, np.cos(rad), -np.sin(rad)],
            [0, np.sin(rad), np.cos(rad)]
        ])
    elif axis == 'y':
        return np.array([
            [np.cos(rad), 0, np.sin(rad)],
            [0, 1, 0],
            [-np.sin(rad), 0, np.cos(rad)]
        ])
    else:
        raise ValueError(f"不支持的旋转轴: {axis}")

def _get_lattice_mismatch(lattice1: np.ndarray, lattice2: np.ndarray) -> Tuple[float, float]:
    a1, b1 = np.linalg.norm(lattice1[0]), np.linalg.norm(lattice1[1])
    a2, b2 = np.linalg.norm(lattice2[0]), np.linalg.norm(lattice2[1])
    mismatch_a = abs(a1 - a2) / max(a1, a2)
    mismatch_b = abs(b1 - b2) / max(b1, b2)
    return mismatch_a, mismatch_b

def _rational_approximation(x: float, max_denominator: int = 50) -> Tuple[int, int]:
    from fractions import Fraction
    frac = Fraction(x).limit_denominator(max_denominator)
    return frac.numerator, frac.denominator


# =============================================================================
# 核心建模类 (继承 MatBuilder ModuleBase)
# =============================================================================

class Struct2DModule(ModuleBase):
    """二维材料建模模块，集成到 MatBuilder"""

    name = "struct2d"
    description = "2D Materials Modeling (表面/单层/转角/异质结/缺陷/超晶格/纳米带/衬底/滑移铁电)"

    MENU_ITEMS = [
        ("表面切割法 (Slab Model)", "build_slab"),
        ("单层剥离法 (Monolayer Extraction)", "build_monolayer"),
        ("转角堆叠法 (Twist Stacking)", "build_twisted_bilayer"),
        ("异质结构建法 (Heterostructure)", "build_heterostructure"),
        ("缺陷与掺杂建模 (Defects & Doping)", "build_defect"),
        ("超晶格构建 (Superlattice)", "build_superlattice"),
        ("边缘/纳米带建模 (Nanoribbon)", "build_nanoribbon"),
        ("衬底与界面建模 (Substrate Interface)", "build_substrate_interface"),
        ("滑移铁电结构生成 (Sliding Ferroelectricity)", "build_sliding_ferroelectric"),
    ]

    def __init__(self):
        super().__init__()
        # ★ 统一使用 structs/ 作为输出根目录
        self.work_dir = Path.cwd() / "structs"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.current_atoms: Optional[Atoms] = None
        self.history: List[Atoms] = []
        self._context = None

    # ★ 实现抽象方法 run (编程入口)
    def run(self, context) -> None:
        """编程式入口（未实现，保留占位）"""
        self._context = context
        pass

    def run_interactive(self, context) -> None:
        """交互式主菜单 (MatBuilder 调用)"""
        self._context = context
        print(f"\n{'='*60}")
        print(f"  {MODULE_NAME} v{MODULE_VERSION} - {MODULE_DESC}")
        print(f"{'='*60}")

        while True:
            print("\n--- 主菜单 ---")
            for i, (name, _) in enumerate(self.MENU_ITEMS, 1):
                print(f"  {i}) {name}")
            print(f"  0) 返回主菜单")

            # 使用 get_int_input 避免重复打印菜单
            choice = get_int_input("请选择", 0, min_val=0, max_val=len(self.MENU_ITEMS))

            if choice == 0:
                print("  返回主菜单")
                break

            method_name = self.MENU_ITEMS[choice - 1][1]
            try:
                getattr(self, method_name)()
            except Exception as e:
                print(f"\n  [错误] {e}")
                import traceback
                traceback.print_exc()

    # ---------- 内部方法 ----------
    
    def _save_result(self, atoms: Atoms, filename: str,
                     subdir: Optional[str] = None) -> Path:
        """保存结果到 structs/ 目录下，可选子目录"""
        save_dir = self.work_dir
        if subdir:
            save_dir = save_dir / subdir
        save_dir.mkdir(parents=True, exist_ok=True)
        filepath = save_dir / filename
        _write_structure(atoms, filepath, fmt='vasp')
        # 同时保存 cif
        cif_path = filepath.with_suffix('.cif')
        _write_structure(atoms, cif_path, fmt='cif')
        print(f"  ✓ 结构已保存: {filepath}")
        print(f"  ✓ CIF格式: {cif_path}")
        self.current_atoms = atoms
        self.history.append(atoms.copy())
        return filepath    

    def _load_input_structure(self, prompt: str = "输入结构文件路径") -> Atoms:
        print(f"\n  {prompt}")
        print("  支持格式: POSCAR, CONTCAR, cif, xyz, etc.")
        # 优先使用已加载的结构
        if self._context and hasattr(self._context, 'has_structure') and self._context.has_structure():
            print(f"  检测到已加载的结构: {self._context.structure_path}")
            use_loaded = get_yes_no_input("  使用当前已加载的结构?", True)
            if use_loaded:
                try:
                    # 将 pymatgen Structure 转换为 ASE Atoms
                    from matbuilder.backends.pymatgen import PymatgenBackend
                    # 直接使用 _pymatgen_to_atoms
                    atoms = _pymatgen_to_atoms(self._context.structure)
                    print(f"  ✓ 使用已加载的结构: {self._context.structure_path}")
                    return atoms
                except Exception as e:
                    print(f"  ✗ 转换已加载结构失败: {e}")
                    # 继续手动输入

        while True:
            filepath = input("文件路径: ").strip()
            path = Path(filepath)
            if not path.is_absolute():
                path = self.work_dir / path
            try:
                atoms = _read_structure(path)
                print(f"  ✓ 成功加载: {path.name}")
                print(f"    化学式: {atoms.get_chemical_formula()}")
                print(f"    原子数: {len(atoms)}")
                print(f"    晶胞: {atoms.get_cell().diagonal().round(3)}")
                return atoms
            except Exception as e:
                print(f"  ✗ {e}")
                retry = get_yes_no_input("是否重新输入?", True)
                if not retry:
                    raise InputError("用户取消输入")

    # =========================================================================
    # 1. 表面切割法 (Slab Model)
    # =========================================================================

    def build_slab(self) -> Atoms:
        """
        表面切割法 - 从三维块体构建表面Slab模型
        """
        print(f"\n{'─'*50}")
        print("  [1] 表面切割法 (Slab Model)")
        print(f"{'─'*50}")

        # 读取输入结构
        bulk_atoms = self._load_input_structure("输入块体结构文件")

        # 交互式参数设置
        print("\n  --- 参数设置 ---")

        # Miller指数
        h = get_int_input("Miller指数 h", 1)
        k = get_int_input("Miller指数 k", 1)
        l = get_int_input("Miller指数 l", 1)
        miller = (h, k, l)

        # 层数
        layers = get_int_input("Slab层数", DEFAULT_SLAB_LAYERS, min_val=1, max_val=50)

        # 真空层
        vacuum = get_float_input("真空层厚度 (Å)", DEFAULT_VACUUM, min_val=5.0, max_val=100.0)

        # 对称性
        symmetric = get_yes_no_input("是否构建对称表面 (两侧相同)?", False)

        # 固定底层
        fix_bottom = get_yes_no_input("是否固定底部原子层?", True)
        fix_layers = 0
        fix_height = None
        if fix_bottom:
            fix_mode = get_choice_input("固定方式",
                                        ["固定指定层数", "固定指定高度范围"])
            if fix_mode == 1:
                fix_layers = get_int_input("固定层数", DEFAULT_FIX_LAYERS, min_val=1)
            else:
                fix_height = get_float_input("固定高度 (Å)", 2.0, min_val=0.5)

        # 超胞
        sc_x = get_int_input("超胞 x方向", 1, min_val=1)
        sc_y = get_int_input("超胞 y方向", 1, min_val=1)
        supercell = (sc_x, sc_y, 1)

        # 构建Slab
        print("\n  正在构建Slab模型...")

        try:
            # 使用pymatgen的SlabGenerator
            structure = _atoms_to_pymatgen(bulk_atoms)
            
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                sga = SpacegroupAnalyzer(structure)
                conventional = sga.get_conventional_standard_structure()

                slab_gen = SlabGenerator(
                    conventional,
                    miller_index=miller,
                    min_slab_size=layers * 2.0,
                    min_vacuum_size=vacuum,
                    lll_reduce=True,
                    center_slab=True,
                    primitive=True,
                    in_unit_planes=True
                )

                slabs = slab_gen.get_slabs()
            if not slabs:
                raise StructureError("无法生成Slab，请检查Miller指数和结构")

            # 选择终止面（如果存在多个）
            if len(slabs) > 1:
                print(f"\n  发现 {len(slabs)} 种可能的表面终止:")
                for i, slab in enumerate(slabs, 1):
                    print(f"    {i}) {slab.composition.reduced_formula} - "
                          f"表面能相关参数...")
                slab_idx = get_choice_input("选择终止面",
                                            [f"终止面 {i}" for i in range(1, len(slabs)+1)]) - 1
                slab_struct = slabs[slab_idx]
            else:
                slab_struct = slabs[0]

            slab_atoms = _pymatgen_to_atoms(slab_struct)

            # 调整真空层精确值
            slab_atoms = _add_vacuum(slab_atoms, vacuum, axis=2)

            # 应用超胞
            if supercell != (1, 1, 1):
                slab_atoms = slab_atoms * supercell

            # 应用约束
            if fix_bottom:
                if fix_height is not None:
                    slab_atoms = _fix_bottom_by_height(slab_atoms, fix_height)
                else:
                    slab_atoms = _fix_bottom_layers(slab_atoms, fix_layers)

            # 对称化处理
            if symmetric:
                slab_atoms = self._make_symmetric_slab(slab_atoms)

        except Exception as e:
            # 降级使用ASE的surface构建
            print(f"  pymatgen构建失败，尝试ASE方法: {e}")
            try:
                slab_atoms = surface(bulk_atoms, miller, layers)
                slab_atoms = _add_vacuum(slab_atoms, vacuum)
                if supercell != (1, 1, 1):
                    slab_atoms = slab_atoms * supercell
                if fix_bottom:
                    slab_atoms = _fix_bottom_layers(slab_atoms, fix_layers)
            except Exception as e2:
                raise StructureError(f"Slab构建失败: {e2}")

        # 保存结果
        formula = slab_atoms.get_chemical_formula()
        filename = f"slab_{formula}_{h}{k}{l}.vasp"
        self._save_result(slab_atoms, filename, "slab")

        # 输出信息
        print(f"\n  --- Slab模型信息 ---")
        print(f"  化学式: {formula}")
        print(f"  总原子数: {len(slab_atoms)}")
        print(f"  Miller指数: ({h}{k}{l})")
        print(f"  真空层: {vacuum} Å")
        print(f"  超胞: {supercell}")
        if slab_atoms.constraints:
            fixed = sum(1 for c in slab_atoms.constraints
                       if hasattr(c, 'index'))
            print(f"  固定原子数: {fixed}")

        return slab_atoms

    def _make_symmetric_slab(self, atoms: Atoms) -> Atoms:
        """构建对称Slab（两侧相同终止面）"""
        positions = atoms.get_positions()
        cell = atoms.get_cell()
        z_center = cell[2, 2] / 2

        mirrored = atoms.copy()
        new_positions = positions.copy()
        new_positions[:, 2] = 2 * z_center - new_positions[:, 2]

        combined = atoms + mirrored
        combined.set_cell(cell)
        return combined

    # =========================================================================
    # 2. 单层剥离法 (Monolayer Extraction)
    # =========================================================================

    def build_monolayer(self) -> Atoms:
        """
        单层剥离法 - 从范德华层状材料中提取单层
        """
        print(f"\n{'─'*50}")
        print("  [2] 单层剥离法 (Monolayer Extraction)")
        print(f"{'─'*50}")

        bulk_atoms = self._load_input_structure("输入层状块体结构")

        print("\n  --- 参数设置 ---")

        auto_detect = get_yes_no_input("自动识别原子层?", True)

        layer_tol = get_float_input("层识别容差 (Å)", DEFAULT_LAYER_TOLERANCE,
                                      min_val=0.01, max_val=1.0)

        # 识别层
        positions = bulk_atoms.get_positions()
        z_coords = positions[:, 2]

        sorted_z = np.sort(z_coords)
        layers_z = []
        current_layer = [sorted_z[0]]

        for z in sorted_z[1:]:
            if z - current_layer[-1] <= layer_tol:
                current_layer.append(z)
            else:
                layers_z.append((np.mean(current_layer), len(current_layer)))
                current_layer = [z]
        layers_z.append((np.mean(current_layer), len(current_layer)))

        print(f"\n  识别到 {len(layers_z)} 个原子层:")
        for i, (z, count) in enumerate(layers_z, 1):
            print(f"    层 {i}: z ≈ {z:.3f} Å, {count} 个原子")

        if auto_detect:
            target_idx = len(layers_z) // 2
            print(f"\n  自动选择中间层 (层 {target_idx + 1})")
        else:
            target_idx = get_int_input("选择要提取的层索引", 1,
                                         min_val=1, max_val=len(layers_z)) - 1

        target_z, _ = layers_z[target_idx]

        mask = np.abs(z_coords - target_z) < layer_tol * 2
        monolayer = bulk_atoms[mask].copy()

        ml_positions = monolayer.get_positions()
        z_shift = -ml_positions[:, 2].min()
        ml_positions[:, 2] += z_shift
        monolayer.set_positions(ml_positions)

        vacuum = get_float_input("真空层厚度 (Å)", DEFAULT_VACUUM, min_val=5.0)
        monolayer = _add_vacuum(monolayer, vacuum, axis=2)

        optimize_cell = get_yes_no_input("是否优化面内晶格参数 (基于范德华间距)?", False)
        if optimize_cell:
            formula = monolayer.get_chemical_formula()
            matched_spacing = None
            for key, spacing in VDW_LAYER_SPACING.items():
                if key.lower() in formula.lower() or any(
                    elem in formula for elem in key.split('_')):
                    matched_spacing = spacing
                    break

            if matched_spacing:
                print(f"  匹配到范德华间距: {matched_spacing} Å ({key})")
                cell = monolayer.get_cell()
            else:
                print("  未匹配到已知范德华材料，保持原晶格")

        formula = monolayer.get_chemical_formula()
        filename = f"monolayer_{formula}.vasp"
        self._save_result(monolayer, filename, "monolayer")

        print(f"\n  --- 单层结构信息 ---")
        print(f"  化学式: {formula}")
        print(f"  原子数: {len(monolayer)}")
        print(f"  提取层: 第 {target_idx + 1} 层")
        print(f"  真空层: {vacuum} Å")

        return monolayer

    # =========================================================================
    # 3. 转角堆叠法 (Twist Stacking)
    # =========================================================================

    def build_twisted_bilayer(self) -> Atoms:
        """
        转角堆叠法 - 构建转角双层/魔角结构
        """
        print(f"\n{'─'*50}")
        print("  [3] 转角堆叠法 (Twist Stacking)")
        print(f"{'─'*50}")

        print("\n  提示: 需要输入两层相同的二维材料结构")

        use_preset = get_yes_no_input("使用预设结构 (如graphene, MoS2)?", True)

        if use_preset:
            presets = ['graphene', 'MoS2', 'WS2', 'BN', 'black_phosphorus']
            preset_idx = get_choice_input("选择预设结构", presets)
            preset_name = presets[preset_idx - 1]

            if preset_name == 'graphene':
                layer1 = graphene()
            elif preset_name in ['MoS2', 'WS2']:
                layer1 = mx2(formula=preset_name, kind='2H', a=3.18 if 'Mo' in preset_name else 3.15)
            elif preset_name == 'BN':
                layer1 = mx2(formula='BN', kind='2H', a=2.50)
            elif preset_name == 'black_phosphorus':
                a, b, c = 3.31, 4.38, 10.0
                layer1 = Atoms('P4',
                              positions=[[0.0, 0.0, 0.0],
                                        [0.5*a, 0.0, 0.0],
                                        [0.0, 0.5*b, 0.0],
                                        [0.5*a, 0.5*b, 0.0]],
                              cell=[a, b, c],
                              pbc=[True, True, False])
            else:
                layer1 = graphene()

            print(f"  ✓ 生成预设结构: {preset_name}")
        else:
            layer1 = self._load_input_structure("输入第一层结构")

        print("\n  --- 参数设置 ---")
        angle = get_float_input("转角 θ (度)", 1.05, min_val=0.01, max_val=60.0)

        magic_angles = [1.05, 1.16, 1.20, 1.47, 2.00, 2.65, 3.15, 3.89, 5.09, 7.34, 9.43, 13.17, 21.79]
        print(f"\n  常见魔角参考: {magic_angles}")

        interlayer = get_float_input("层间距 (Å)", 3.35, min_val=2.0, max_val=10.0)

        max_atoms = get_int_input("最大原子数限制", 500, min_val=50, max_val=10000)

        print(f"\n  正在构建转角 {angle}° 双层结构...")

        layer2 = layer1.copy()
        layer2.rotate(angle, 'z', center=(0, 0, 0))

        twisted_atoms = self._build_twist_supercell(layer1, layer2, angle,
                                                     interlayer, max_atoms)

        vacuum = get_float_input("垂直真空层 (Å)", DEFAULT_VACUUM)
        twisted_atoms = _add_vacuum(twisted_atoms, vacuum, axis=2)

        formula = twisted_atoms.get_chemical_formula()
        filename = f"twisted_{formula}_{angle:.2f}deg.vasp"
        self._save_result(twisted_atoms, filename, "twisted")

        print(f"\n  --- 转角结构信息 ---")
        print(f"  化学式: {formula}")
        print(f"  总原子数: {len(twisted_atoms)}")
        print(f"  转角: {angle}°")
        print(f"  层间距: {interlayer} Å")
        print(f"  超胞尺寸: {twisted_atoms.get_cell().diagonal()[:2].round(3)}")

        return twisted_atoms

    def _build_twist_supercell(self, layer1: Atoms, layer2: Atoms,
                                angle: float, interlayer: float,
                                max_atoms: int) -> Atoms:
        cell1 = layer1.get_cell()[:2, :2]
        cell2 = layer2.get_cell()[:2, :2]

        theta_rad = np.radians(angle)
        R = np.array([[np.cos(theta_rad), -np.sin(theta_rad)],
                      [np.sin(theta_rad), np.cos(theta_rad)]])

        best_n = 1
        best_misfit = float('inf')
        best_sc1 = (1, 0)
        best_sc2 = (0, 1)

        max_search = min(20, int(np.sqrt(max_atoms / len(layer1))))

        for n in range(1, max_search + 1):
            for m in range(n + 1):
                sc1 = np.array([n, m])
                sc2 = np.array([-m, n + m]) if m != 0 else np.array([0, n])

                super_cell1 = sc1[0] * cell1[0] + sc1[1] * cell1[1]
                super_cell2 = sc2[0] * cell1[0] + sc2[1] * cell1[1]

                super_cell1_rot = R @ super_cell1
                super_cell2_rot = R @ super_cell2

                len1 = np.linalg.norm(super_cell1)
                len1_rot = np.linalg.norm(super_cell1_rot)
                len2 = np.linalg.norm(cell2[0])

                misfit = abs(len1_rot - len2 * n) / len2

                total_atoms = len(layer1) * (n**2 + n*m + m**2)

                if misfit < best_misfit and total_atoms <= max_atoms:
                    best_misfit = misfit
                    best_n = n
                    best_sc1 = sc1
                    best_sc2 = sc2

        print(f"  最佳超胞: n={best_n}, misfit={best_misfit:.4f}")
        print(f"  预估原子数: ~{len(layer1) * (best_n**2 + best_n*best_sc2[1] + best_sc2[1]**2)}")

        sc_matrix = np.array([[best_sc1[0], best_sc1[1], 0],
                              [best_sc2[0], best_sc2[1], 0],
                              [0, 0, 1]])

        layer1_sc = layer1 * (best_n, best_n, 1)

        target_cell = np.zeros((3, 3))
        target_cell[:2, 0] = best_sc1[0] * cell1[0] + best_sc1[1] * cell1[1]
        target_cell[:2, 1] = best_sc2[0] * cell1[0] + best_sc2[1] * cell1[1]
        target_cell[2, 2] = 20.0

        layer2_sc = layer2 * (best_n, best_n, 1)

        layer2_positions = layer2_sc.get_positions()
        layer2_positions[:, 2] += interlayer

        combined = layer1_sc.copy()
        combined.extend(Atoms(positions=layer2_positions,
                             symbols=layer2_sc.get_chemical_symbols(),
                             cell=layer2_sc.get_cell()))

        combined.set_cell(target_cell, scale_atoms=False)
        return combined

    # =========================================================================
    # 4. 异质结构建法 (Heterostructure)
    # =========================================================================

    def build_heterostructure(self) -> Atoms:
        """
        异质结构建法 - 垂直堆叠不同二维材料
        """
        print(f"\n{'─'*50}")
        print("  [4] 异质结构建法 (Heterostructure Stacking)")
        print(f"{'─'*50}")

        print("\n  需要输入两种二维材料结构")

        bottom = self._load_input_structure("输入底层材料结构")
        top = self._load_input_structure("输入顶层材料结构")

        print("\n  --- 参数设置 ---")

        cell_b = bottom.get_cell()[:2, :2]
        cell_t = top.get_cell()[:2, :2]

        mismatch_a, mismatch_b = _get_lattice_mismatch(cell_b, cell_t)
        print(f"\n  晶格失配分析:")
        print(f"    底层晶格: a={np.linalg.norm(cell_b[0]):.4f}, b={np.linalg.norm(cell_b[1]):.4f}")
        print(f"    顶层晶格: a={np.linalg.norm(cell_t[0]):.4f}, b={np.linalg.norm(cell_t[1]):.4f}")
        print(f"    失配度: {mismatch_a*100:.2f}%, {mismatch_b*100:.2f}%")

        if max(mismatch_a, mismatch_b) > 0.05:
            print("  ⚠ 晶格失配较大 (>5%)")
            strain_choice = get_choice_input("应变处理方式", [
                "不施加应变 (直接堆叠，可能产生应力)",
                "应变底层以匹配顶层",
                "应变顶层以匹配底层",
                "双方各应变一半",
                "构建近似超胞 (最小公倍数)"
            ])
        else:
            strain_choice = 1

        if strain_choice == 2:
            bottom = self._strain_2d(bottom, cell_t)
        elif strain_choice == 3:
            top = self._strain_2d(top, cell_b)
        elif strain_choice == 4:
            avg_cell = (cell_b + cell_t) / 2
            bottom = self._strain_2d(bottom, avg_cell)
            top = self._strain_2d(top, avg_cell)
        elif strain_choice == 5:
            bottom, top = self._build_commensurate_supercell(bottom, top)

        interlayer = get_float_input("层间距 (Å)", 3.5, min_val=2.0, max_val=10.0)

        alignment = get_choice_input("对齐方式", [
            "中心对齐 (默认)",
            "原点对齐",
            "自定义平移"
        ])

        shift = (0.0, 0.0)
        if alignment == 3:
            shift_x = get_float_input("x方向平移 (Å)", 0.0)
            shift_y = get_float_input("y方向平移 (Å)", 0.0)
            shift = (shift_x, shift_y)

        vacuum = get_float_input("真空层厚度 (Å)", DEFAULT_VACUUM)

        hetero = self._stack_layers(bottom, top, interlayer, alignment, shift)
        hetero = _add_vacuum(hetero, vacuum, axis=2)

        formula = hetero.get_chemical_formula()
        filename = f"hetero_{formula}.vasp"
        self._save_result(hetero, filename, "heterostructure")

        print(f"\n  --- 异质结信息 ---")
        print(f"  化学式: {formula}")
        print(f"  总原子数: {len(hetero)}")
        print(f"  层间距: {interlayer} Å")
        print(f"  对齐方式: {['中心', '原点', '自定义'][alignment-1]}")

        return hetero

    def _strain_2d(self, atoms: Atoms, target_cell_2d: np.ndarray) -> Atoms:
        new_atoms = atoms.copy()
        cell = new_atoms.get_cell().copy()
        cell[:2, :2] = target_cell_2d
        new_atoms.set_cell(cell, scale_atoms=True)
        return new_atoms

    def _build_commensurate_supercell(self, atoms1: Atoms, atoms2: Atoms) -> Tuple[Atoms, Atoms]:
        cell1 = atoms1.get_cell()[:2, :2]
        cell2 = atoms2.get_cell()[:2, :2]

        a1, a2 = np.linalg.norm(cell1[0]), np.linalg.norm(cell2[0])

        best_n, best_m = 1, 1
        best_error = float('inf')

        for n in range(1, 10):
            for m in range(1, 10):
                error = abs(n * a1 - m * a2) / max(n * a1, m * a2)
                if error < best_error:
                    best_error = error
                    best_n, best_m = n, m

        sc1 = atoms1 * (best_n, best_n, 1)
        sc2 = atoms2 * (best_m, best_m, 1)

        avg_cell = (sc1.get_cell() + sc2.get_cell()) / 2
        sc1.set_cell(avg_cell, scale_atoms=True)
        sc2.set_cell(avg_cell, scale_atoms=True)

        print(f"  公度超胞: {best_n}x{best_n} 和 {best_m}x{best_m}, 误差: {best_error*100:.2f}%")

        return sc1, sc2

    def _stack_layers(self, bottom: Atoms, top: Atoms,
                      interlayer: float, alignment: int,
                      shift: Tuple[float, float]) -> Atoms:
        cell = bottom.get_cell().copy()
        top_strained = top.copy()
        top_strained.set_cell(cell, scale_atoms=True)

        bottom_pos = bottom.get_positions()
        top_pos = top_strained.get_positions()

        z_bottom = bottom_pos[:, 2].max()
        top_pos[:, 2] += z_bottom + interlayer

        if alignment == 1:
            center_b = bottom_pos[:, :2].mean(axis=0)
            center_t = top_pos[:, :2].mean(axis=0)
            top_pos[:, :2] += center_b - center_t
        elif alignment == 3:
            top_pos[:, 0] += shift[0]
            top_pos[:, 1] += shift[1]

        top_strained.set_positions(top_pos)

        combined = bottom.copy()
        combined.extend(top_strained)

        return combined

    # =========================================================================
    # 5. 缺陷与掺杂建模 (Defects & Doping)
    # =========================================================================

    def build_defect(self) -> Atoms:
        """
        缺陷与掺杂建模
        """
        print(f"\n{'─'*50}")
        print("  [5] 缺陷与掺杂建模 (Defects & Doping)")
        print(f"{'─'*50}")

        base_atoms = self._load_input_structure("输入完美结构")

        print("\n  --- 缺陷类型选择 ---")
        defect_type = get_choice_input("缺陷类型", [
            "空位 (Vacancy)",
            "替位掺杂 (Substitution)",
            "间隙掺杂 (Interstitial)",
            "吸附原子 (Adatom)",
            "复杂缺陷组合"
        ])

        defect_names = ["vacancy", "substitution", "interstitial", "adatom", "complex"]
        defect_name = defect_names[defect_type - 1]

        modified_atoms = base_atoms.copy()

        if defect_name == "vacancy":
            modified_atoms = self._create_vacancy(modified_atoms)
        elif defect_name == "substitution":
            modified_atoms = self._create_substitution(modified_atoms)
        elif defect_name == "interstitial":
            modified_atoms = self._create_interstitial(modified_atoms)
        elif defect_name == "adatom":
            modified_atoms = self._create_adatom(modified_atoms)
        elif defect_name == "complex":
            modified_atoms = self._create_complex_defect(modified_atoms)

        formula = modified_atoms.get_chemical_formula()
        filename = f"defect_{formula}_{defect_name}.vasp"
        self._save_result(modified_atoms, filename, "defect")

        print(f"\n  --- 缺陷结构信息 ---")
        print(f"  化学式: {formula}")
        print(f"  总原子数: {len(modified_atoms)}")
        print(f"  缺陷类型: {defect_name}")

        return modified_atoms

    def _create_vacancy(self, atoms: Atoms) -> Atoms:
        print("\n  --- 空位设置 ---")

        species = list(set(atoms.get_chemical_symbols()))
        print(f"  可用元素: {species}")

        target = input("目标元素 (或 'any' 任意): ").strip()
        if not target:
            target = species[0]

        if target.lower() == 'any':
            print("\n  原子列表:")
            for i, (sym, pos) in enumerate(zip(atoms.get_chemical_symbols(),
                                                  atoms.get_positions())):
                print(f"    {i:3d}: {sym} @ ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")

            idx = get_int_input("要移除的原子索引", 0, min_val=0, max_val=len(atoms)-1)
        else:
            indices = [i for i, s in enumerate(atoms.get_chemical_symbols()) if s == target]
            print(f"  {target} 原子索引: {indices}")

            if len(indices) == 1:
                idx = indices[0]
                print(f"  自动选择唯一原子: {idx}")
            else:
                idx = get_int_input("选择要移除的原子索引", indices[0],
                                      min_val=min(indices), max_val=max(indices))

        modified_atoms = atoms.copy()
        del modified_atoms[idx]
        print(f"  ✓ 已移除原子 {idx}")

        return modified_atoms

    def _create_substitution(self, atoms: Atoms) -> Atoms:
        print("\n  --- 替位掺杂设置 ---")

        species = list(set(atoms.get_chemical_symbols()))
        print(f"  宿主元素: {species}")

        target = input("要被替换的元素: ").strip()
        if not target:
            target = species[0]
        dopant = input("掺杂元素 (如 Al, N, etc.): ").strip()
        if not dopant:
            dopant = "Al"

        indices = [i for i, s in enumerate(atoms.get_chemical_symbols()) if s == target]

        if len(indices) > 1:
            use_concentration = get_yes_no_input("按浓度随机掺杂?", False)
            if use_concentration:
                conc = get_float_input("掺杂浓度 (0-1)", 0.1, min_val=0.0, max_val=1.0)
                n_dope = max(1, int(len(indices) * conc))
                import random
                dope_indices = random.sample(indices, n_dope)
            else:
                print(f"  可替换位置: {indices}")
                dope_input = input("输入要替换的索引 (逗号分隔): ").strip()
                if not dope_input:
                    dope_input = ",".join(map(str, indices[:1]))
                dope_indices = [int(x.strip()) for x in dope_input.split(',')]
        else:
            dope_indices = indices

        symbols = list(atoms.get_chemical_symbols())
        for idx in dope_indices:
            symbols[idx] = dopant
            print(f"  ✓ 位置 {idx}: {target} → {dopant}")

        modified_atoms = atoms.copy()
        modified_atoms.set_chemical_symbols(symbols)

        return modified_atoms

    def _create_interstitial(self, atoms: Atoms) -> Atoms:
        print("\n  --- 间隙掺杂设置 ---")

        element = input("间隙原子元素: ").strip()
        if not element:
            element = "H"

        print("\n  插入位置选择:")
        print("    1) 晶胞中心")
        print("    2) 四面体间隙 (FCC-like)")
        print("    3) 八面体间隙 (FCC-like)")
        print("    4) 自定义坐标")

        pos_choice = get_choice_input("选择插入位置", [
            "晶胞中心", "四面体间隙", "八面体间隙", "自定义坐标"
        ])

        cell = atoms.get_cell()

        if pos_choice == 1:
            position = cell.sum(axis=0) / 2
        elif pos_choice == 2:
            position = cell[0] * 0.25 + cell[1] * 0.25 + cell[2] * 0.25
        elif pos_choice == 3:
            position = cell[0] * 0.5 + cell[1] * 0.5 + cell[2] * 0.5
        else:
            x = get_float_input("x坐标 (fractional)", 0.5)
            y = get_float_input("y坐标 (fractional)", 0.5)
            z = get_float_input("z坐标 (fractional)", 0.5)
            position = x * cell[0] + y * cell[1] + z * cell[2]

        modified_atoms = atoms.copy()
        modified_atoms.append(element)
        positions = modified_atoms.get_positions()
        positions[-1] = position
        modified_atoms.set_positions(positions)

        print(f"  ✓ 已插入 {element} @ ({position[0]:.3f}, {position[1]:.3f}, {position[2]:.3f})")

        return modified_atoms

    def _create_adatom(self, atoms: Atoms) -> Atoms:
        print("\n  --- 吸附原子设置 ---")

        element = input("吸附原子元素: ").strip()
        if not element:
            element = "H"
        height = get_float_input("吸附高度 (Å, 距表面)", 2.0, min_val=0.5)

        print("\n  吸附位置:")
        pos_choice = get_choice_input("选择吸附位置", [
            "表面上方中心",
            "顶位 (Top site)",
            "桥位 (Bridge site)",
            "hollow位 (FCC/HCP)",
            "自定义坐标"
        ])

        positions = atoms.get_positions()
        z_max = positions[:, 2].max()
        cell = atoms.get_cell()

        if pos_choice == 1:
            xy_pos = (cell[0, :2] + cell[1, :2]) / 2
        elif pos_choice == 2:
            surface_atoms = [i for i, z in enumerate(positions[:, 2])
                           if z > z_max - 0.5]
            print(f"  表面原子: {surface_atoms}")
            top_idx = get_int_input("选择顶位原子索引", surface_atoms[0])
            xy_pos = positions[top_idx, :2]
        elif pos_choice == 3:
            print("  选择两个表面原子...")
            idx1 = get_int_input("原子1", 0)
            idx2 = get_int_input("原子2", 1)
            xy_pos = (positions[idx1, :2] + positions[idx2, :2]) / 2
        elif pos_choice == 4:
            print("  选择三个表面原子...")
            idxs = []
            for i in range(3):
                idxs.append(get_int_input(f"原子{i+1}", i))
            xy_pos = np.mean([positions[i, :2] for i in idxs], axis=0)
        else:
            x = get_float_input("x坐标 (Å)", 0.0)
            y = get_float_input("y坐标 (Å)", 0.0)
            xy_pos = np.array([x, y])

        position = np.array([xy_pos[0], xy_pos[1], z_max + height])

        modified_atoms = atoms.copy()
        modified_atoms.append(element)
        new_positions = modified_atoms.get_positions()
        new_positions[-1] = position
        modified_atoms.set_positions(new_positions)

        print(f"  ✓ 已吸附 {element} @ ({position[0]:.3f}, {position[1]:.3f}, {position[2]:.3f})")

        return modified_atoms

    def _create_complex_defect(self, atoms: Atoms) -> Atoms:
        print("\n  --- 复杂缺陷设置 ---")
        print("  依次添加多种缺陷，输入 'done' 完成")

        modified = atoms.copy()

        while True:
            print("\n  当前原子数:", len(modified))
            cont = input("添加缺陷类型 (vacancy/sub/interstitial/adatom/done): ").strip().lower()
            if cont == 'done':
                break

            if cont in ['v', 'vacancy']:
                modified = self._create_vacancy(modified)
            elif cont in ['sub', 'substitution']:
                modified = self._create_substitution(modified)
            elif cont in ['i', 'interstitial']:
                modified = self._create_interstitial(modified)
            elif cont in ['a', 'adatom']:
                modified = self._create_adatom(modified)
            else:
                print("  ! 未知缺陷类型")

        return modified

    # =========================================================================
    # 6. 超晶格构建 (Superlattice)
    # =========================================================================

    def build_superlattice(self) -> Atoms:
        """
        超晶格构建 - 周期性堆叠或扩展结构
        """
        print(f"\n{'─'*50}")
        print("  [6] 超晶格构建 (Superlattice)")
        print(f"{'─'*50}")

        print("\n  --- 超晶格类型 ---")
        lattice_type = get_choice_input("选择超晶格类型", [
            "简单超胞扩展 (Supercell)",
            "多层堆叠超晶格 (Multilayer Stack)",
            "摩尔超晶格 (Moiré Superlattice by Strain)",
            "条纹/孔洞超晶格 (Patterned Superlattice)"
        ])

        if lattice_type == 1:
            return self._build_simple_supercell()
        elif lattice_type == 2:
            return self._build_multilayer_stack()
        elif lattice_type == 3:
            return self._build_moire_superlattice()
        else:
            return self._build_patterned_superlattice()

    def _build_simple_supercell(self) -> Atoms:
        atoms = self._load_input_structure("输入原胞结构")

        print("\n  --- 超胞矩阵设置 ---")
        nx = get_int_input("x方向扩展倍数", 2, min_val=1)
        ny = get_int_input("y方向扩展倍数", 2, min_val=1)
        nz = get_int_input("z方向扩展倍数", 1, min_val=1)

        supercell = atoms * (nx, ny, nz)

        add_vac = get_yes_no_input("添加真空层?", False)
        if add_vac:
            vacuum = get_float_input("真空层厚度 (Å)", DEFAULT_VACUUM)
            supercell = _add_vacuum(supercell, vacuum)

        filename = f"supercell_{supercell.get_chemical_formula()}_{nx}x{ny}x{nz}.vasp"
        self._save_result(supercell, filename, "superlattice")

        return supercell

    def _build_multilayer_stack(self) -> Atoms:
        print("\n  构建多层堆叠超晶格")
        print("  依次输入各层结构，输入 'done' 完成")

        layers = []
        spacings = []

        while True:
            print(f"\n  --- 第 {len(layers)+1} 层 ---")
            cont = get_yes_no_input("是否继续添加层?", True)
            if not cont:
                break

            layer = self._load_input_structure(f"输入第 {len(layers)+1} 层结构")
            layers.append(layer)

            if len(layers) > 1:
                spacing = get_float_input(f"与前一层间距 (Å)", 3.5)
                spacings.append(spacing)

        if len(layers) < 2:
            raise InputError("至少需要两层构建超晶格")

        ref_cell = layers[0].get_cell()

        combined = layers[0].copy()
        current_z = combined.get_positions()[:, 2].max()

        for i, layer in enumerate(layers[1:], 1):
            layer_copy = layer.copy()
            layer_copy.set_cell(ref_cell, scale_atoms=True)

            positions = layer_copy.get_positions()
            z_min = positions[:, 2].min()
            z_shift = current_z + spacings[i-1] - z_min
            positions[:, 2] += z_shift
            layer_copy.set_positions(positions)

            combined.extend(layer_copy)
            current_z = positions[:, 2].max()

        vacuum = get_float_input("真空层厚度 (Å)", DEFAULT_VACUUM)
        combined = _add_vacuum(combined, vacuum)

        repeat = get_int_input("超晶格重复次数", 1, min_val=1)
        if repeat > 1:
            combined = combined * (1, 1, repeat)

        filename = f"multilayer_{combined.get_chemical_formula()}.vasp"
        self._save_result(combined, filename, "superlattice")

        return combined

    def _build_moire_superlattice(self) -> Atoms:
        print("\n  构建摩尔超晶格")
        print("  需要两种晶格常数略有差异的材料")

        layer1 = self._load_input_structure("输入第一层")
        layer2 = self._load_input_structure("输入第二层 (晶格常数略有不同)")

        cell1 = layer1.get_cell()[:2, :2]
        cell2 = layer2.get_cell()[:2, :2]

        a1, b1 = np.linalg.norm(cell1[0]), np.linalg.norm(cell1[1])
        a2, b2 = np.linalg.norm(cell2[0]), np.linalg.norm(cell2[1])

        print(f"\n  晶格常数: 层1=({a1:.3f}, {b1:.3f}), 层2=({a2:.3f}, {b2:.3f})")

        mismatch = abs(a1 - a2) / min(a1, a2)
        moire_period = max(a1, a2) / mismatch if mismatch > 0 else float('inf')
        print(f"  失配度: {mismatch*100:.3f}%")
        print(f"  理论摩尔周期: ~{moire_period:.1f} Å")

        max_atoms = get_int_input("最大原子数限制", 500)

        best_n, best_m = 1, 1
        best_error = float('inf')

        for n in range(1, 20):
            for m in range(1, 20):
                error = abs(n * a1 - m * a2) / max(n * a1, m * a2)
                total_atoms = len(layer1) * n * n + len(layer2) * m * m
                if error < best_error and total_atoms <= max_atoms:
                    best_error = error
                    best_n, best_m = n, m

        print(f"\n  最佳匹配: {best_n}x 层1 ≈ {best_m}x 层2")
        print(f"  误差: {best_error*100:.3f}%")
        print(f"  预估原子数: {len(layer1)*best_n**2 + len(layer2)*best_m**2}")

        sc1 = layer1 * (best_n, best_n, 1)
        sc2 = layer2 * (best_m, best_m, 1)

        avg_cell = (sc1.get_cell() + sc2.get_cell()) / 2
        sc1.set_cell(avg_cell, scale_atoms=True)
        sc2.set_cell(avg_cell, scale_atoms=True)

        interlayer = get_float_input("层间距 (Å)", 3.5)
        sc2_positions = sc2.get_positions()
        sc2_positions[:, 2] += sc1.get_positions()[:, 2].max() + interlayer
        sc2.set_positions(sc2_positions)

        combined = sc1.copy()
        combined.extend(sc2)

        vacuum = get_float_input("真空层 (Å)", DEFAULT_VACUUM)
        combined = _add_vacuum(combined, vacuum)

        filename = f"moire_{combined.get_chemical_formula()}.vasp"
        self._save_result(combined, filename, "superlattice")

        return combined

    def _build_patterned_superlattice(self) -> Atoms:
        print("\n  构建图案化超晶格")
        print("  此功能通过超胞+选择性移除原子实现")

        atoms = self._load_input_structure("输入基础结构")

        pattern = get_choice_input("图案类型", [
            "条纹超晶格 (纳米带阵列)",
            "孔洞超晶格 (反点阵)",
            "棋盘格超晶格"
        ])

        nx = get_int_input("x方向周期 (原胞倍数)", 4, min_val=2)
        ny = get_int_input("y方向周期 (原胞倍数)", 4, min_val=2)

        supercell = atoms * (nx, ny, 1)
        positions = supercell.get_positions()
        cell = supercell.get_cell()

        n_atoms = len(supercell)
        indices_to_remove = []

        if pattern == 1:
            stripe_width = get_int_input("条纹宽度 (原子数)", nx // 2, min_val=1, max_val=nx-1)
            stripe_dir = get_choice_input("条纹方向", ["x方向", "y方向"])

            frac_pos = supercell.get_scaled_positions()
            if stripe_dir == 1:
                for i, pos in enumerate(frac_pos):
                    stripe_idx = int(pos[1] * ny) % ny
                    if stripe_idx >= stripe_width:
                        indices_to_remove.append(i)
            else:
                for i, pos in enumerate(frac_pos):
                    stripe_idx = int(pos[0] * nx) % nx
                    if stripe_idx >= stripe_width:
                        indices_to_remove.append(i)

        elif pattern == 2:
            hole_shape = get_choice_input("孔洞形状", ["圆形", "方形", "菱形"])
            hole_size = get_float_input("孔洞尺寸 (fractional)", 0.3, min_val=0.1, max_val=0.5)
            center = np.array([0.5, 0.5])

            frac_pos = supercell.get_scaled_positions()

            if hole_shape == 1:
                for i, pos in enumerate(frac_pos):
                    dx = pos[0] - center[0]
                    dy = pos[1] - center[1]
                    dx = dx - round(dx)
                    dy = dy - round(dy)
                    if np.sqrt(dx**2 + dy**2) < hole_size:
                        indices_to_remove.append(i)

            elif hole_shape == 2:
                for i, pos in enumerate(frac_pos):
                    dx = abs(pos[0] - center[0])
                    dy = abs(pos[1] - center[1])
                    dx = min(dx, 1.0 - dx)
                    dy = min(dy, 1.0 - dy)
                    if dx < hole_size and dy < hole_size:
                        indices_to_remove.append(i)

            else:
                for i, pos in enumerate(frac_pos):
                    dx = abs(pos[0] - center[0])
                    dy = abs(pos[1] - center[1])
                    dx = min(dx, 1.0 - dx)
                    dy = min(dy, 1.0 - dy)
                    if dx + dy < hole_size:
                        indices_to_remove.append(i)

        else:
            frac_pos = supercell.get_scaled_positions()
            for i, pos in enumerate(frac_pos):
                ix = int(pos[0] * nx) % 2
                iy = int(pos[1] * ny) % 2
                if (ix + iy) % 2 == 0:
                    indices_to_remove.append(i)

        indices_to_remove = sorted(set(indices_to_remove), reverse=True)

        for idx in indices_to_remove:
            del supercell[idx]

        print(f"  移除 {len(indices_to_remove)} 个原子")
        print(f"  剩余 {len(supercell)} 个原子")

        vacuum = get_float_input("真空层厚度 (Å)", DEFAULT_VACUUM)
        supercell = _add_vacuum(supercell, vacuum)

        pattern_names = ["stripe", "hole", "checkerboard"]
        filename = f"patterned_{supercell.get_chemical_formula()}_{pattern_names[pattern-1]}.vasp"
        self._save_result(supercell, filename, "superlattice")

        return supercell

    # =========================================================================
    # 7. 边缘/边界结构建模 (Edge & Nanoribbon)
    # =========================================================================

    def build_nanoribbon(self) -> Atoms:
        """
        边缘/纳米带建模 - 沿特定方向切割二维材料形成一维纳米带
        使用 ASE cut() 函数实现（替代不存在的 nanoribbon）
        """
        print(f"\n{'─'*50}")
        print("  [7] 边缘/纳米带建模 (Nanoribbon)")
        print(f"{'─'*50}")

        base_atoms = self._load_input_structure("输入二维材料结构")

        print("\n  --- 参数设置 ---")

        edge_type = get_choice_input("边缘类型", [
            "扶手椅型边缘 (Armchair)",
            "锯齿型边缘 (Zigzag)",
            "手性边缘 (Chiral) - 自定义方向"
        ])

        width = get_int_input("纳米带宽度 (单胞倍数)", 5, min_val=1, max_val=50)

        use_periodic = get_yes_no_input("长度方向保持周期性?", True)
        length = None
        if not use_periodic:
            length = get_int_input("纳米带长度 (单胞倍数)", 10, min_val=1)

        passivate = get_yes_no_input("是否钝化边缘悬挂键?", True)
        passivant = None
        passivation_bond_length = 1.1
        if passivate:
            passivants = ["H", "F", "O", "Cl", "OH"]
            passivant_idx = get_choice_input("选择钝化原子/基团", passivants)
            passivant = passivants[passivant_idx - 1]
            passivation_bond_length = get_float_input("钝化键长 (Å)", 1.1, min_val=0.5, max_val=3.0)

        vacuum_xy = get_float_input("面内真空层 (Å)", 15.0, min_val=5.0)
        vacuum_z = get_float_input("垂直真空层 (Å)", DEFAULT_VACUUM, min_val=5.0)

        print("\n  正在构建纳米带...")

        # 使用 ASE cut() 构建纳米带
        cell = base_atoms.get_cell()

        # 确定切割方向和周期性方向
        if edge_type == 1:  # armchair
            # armchair 边缘: 切割方向为 y (b轴)，周期性沿 x (a轴)
            # 需要先将结构旋转使 armchair 方向对齐
            base_rotated = base_atoms.copy()
            # 对于六方晶格如石墨烯，armchair 方向需要旋转 30 度
            # 但对于通用材料，我们直接使用 cut
            n_cut = width
            n_periodic = length if length else 1
            ribbon = cut(base_rotated, a=(n_periodic, 0, 0), b=(0, n_cut, 0), c=(0, 0, 1))
            
        elif edge_type == 2:  # zigzag
            # zigzag 边缘: 切割方向为 x (a轴)，周期性沿 y (b轴)
            n_cut = width
            n_periodic = length if length else 1
            ribbon = cut(base_atoms, a=(n_cut, 0, 0), b=(0, n_periodic, 0), c=(0, 0, 1))
            
        else:  # chiral
            chiral_angle = get_float_input("手性角度 (度, 相对于x轴)", 30.0, min_val=0.0, max_val=90.0)
            base_rotated = base_atoms.copy()
            if chiral_angle != 0:
                base_rotated.rotate(chiral_angle, 'z', center=(0, 0, 0))
            n_cut = width
            n_periodic = length if length else 1
            ribbon = cut(base_rotated, a=(n_periodic, 0, 0), b=(0, n_cut, 0), c=(0, 0, 1))

        # 调整晶胞: 添加真空层
        positions = ribbon.get_positions()
        x_span = positions[:, 0].max() - positions[:, 0].min()
        y_span = positions[:, 1].max() - positions[:, 1].min()
        z_span = positions[:, 2].max() - positions[:, 2].min()

        new_cell = np.eye(3)
        if use_periodic:
            # 周期性方向保持实际长度，非周期性方向加真空
            if edge_type == 1:  # armchair: 周期性沿 x
                new_cell[0, 0] = ribbon.get_cell()[0, 0]
                new_cell[1, 1] = y_span + vacuum_xy
            else:  # zigzag: 周期性沿 y
                new_cell[0, 0] = x_span + vacuum_xy
                new_cell[1, 1] = ribbon.get_cell()[1, 1]
        else:
            new_cell[0, 0] = x_span + vacuum_xy
            new_cell[1, 1] = y_span + vacuum_xy
        
        new_cell[2, 2] = z_span + vacuum_z

        ribbon.set_cell(new_cell, scale_atoms=False)
        ribbon.center()

        # 设置周期性
        if use_periodic:
            if edge_type == 1:  # armchair: 周期性沿 x
                ribbon.set_pbc([True, False, False])
            else:  # zigzag: 周期性沿 y
                ribbon.set_pbc([False, True, False])
        else:
            ribbon.set_pbc([False, False, False])

        # 边缘钝化
        if passivate and passivant:
            ribbon = self._passivate_edges(ribbon, passivant, passivation_bond_length,
                                           ["armchair", "zigzag", "chiral"][edge_type-1])

        edge_names = ["armchair", "zigzag", "chiral"]
        formula = ribbon.get_chemical_formula()
        filename = f"nanoribbon_{formula}_{edge_names[edge_type-1]}_w{width}.vasp"
        self._save_result(ribbon, filename, "nanoribbon")

        print(f"\n  --- 纳米带信息 ---")
        print(f"  化学式: {formula}")
        print(f"  总原子数: {len(ribbon)}")
        print(f"  边缘类型: {edge_names[edge_type-1]}")
        print(f"  宽度: {width} 单胞")
        print(f"  周期性: {'是' if use_periodic else '否'}")
        if passivate:
            print(f"  钝化: {passivant}")

        return ribbon

    def _passivate_edges(self, atoms: Atoms, passivant: str,
                         bond_length: float, edge_type_name: str) -> Atoms:
        """
        钝化纳米带边缘悬挂键
        使用配位数判断边缘原子，并添加钝化原子
        """
        print(f"\n  正在钝化 {edge_type_name} 边缘...")

        positions = atoms.get_positions()
        symbols = atoms.get_chemical_symbols()
        cell = atoms.get_cell()
        pbc = atoms.get_pbc()

        new_atoms = atoms.copy()

        # 计算每个原子的配位数（考虑周期性）
        if HAS_SCIPY:
            # 使用 cKDTree 计算邻居
            # 对于周期性边界，需要扩展镜像
            cutoff = 2.5  # 典型的化学键截止距离
            
            # 构建扩展位置列表（考虑周期性镜像）
            all_positions = [positions]
            if pbc[0]:
                all_positions.extend([positions + np.array([cell[0,0], 0, 0]), 
                                      positions - np.array([cell[0,0], 0, 0])])
            if pbc[1]:
                all_positions.extend([positions + np.array([0, cell[1,1], 0]), 
                                      positions - np.array([0, cell[1,1], 0])])
            
            extended_positions = np.vstack(all_positions)
            tree = cKDTree(extended_positions)
            
            neighbor_counts = []
            for i, pos in enumerate(positions):
                neighbors = tree.query_ball_point(pos, cutoff)
                # 排除自身
                count = len([n for n in neighbors if n != i and n < len(positions)])
                neighbor_counts.append(count)
        else:
            # 降级：基于z坐标简单判断（适用于平面二维材料）
            z_coords = positions[:, 2]
            z_mean = z_coords.mean()
            z_span = z_coords.max() - z_coords.min()
            
            neighbor_counts = []
            for pos in positions:
                # 边缘原子通常在z方向偏离平均值
                z_dev = abs(pos[2] - z_mean)
                if z_dev > z_span * 0.15:
                    neighbor_counts.append(2)  # 边缘原子配位数低
                else:
                    neighbor_counts.append(6)  # 体原子配位数高

        # 确定配位数阈值
        avg_coord = np.mean(neighbor_counts)
        std_coord = np.std(neighbor_counts)
        edge_threshold = avg_coord - 0.5 * std_coord
        
        # 更保守的边缘判断：配位数显著低于平均值
        edge_indices = [i for i, count in enumerate(neighbor_counts) if count < edge_threshold]

        print(f"  平均配位数: {avg_coord:.1f}")
        print(f"  边缘阈值: {edge_threshold:.1f}")
        print(f"  识别到 {len(edge_indices)} 个边缘原子")

        added_count = 0
        for idx in edge_indices:
            pos = positions[idx]
            symbol = symbols[idx]

            # 计算缺失键的方向（指向真空）
            if HAS_SCIPY:
                # 找到邻居方向
                tree = cKDTree(positions)
                neighbors = tree.query_ball_point(pos, cutoff)
                neighbor_vecs = []
                for n_idx in neighbors:
                    if n_idx != idx:
                        vec = positions[n_idx] - pos
                        # 应用周期性边界条件
                        for dim in range(3):
                            if pbc[dim]:
                                vec[dim] = vec[dim] - cell[dim, dim] * round(vec[dim] / cell[dim, dim])
                        dist = np.linalg.norm(vec)
                        if dist > 0.5:  # 排除自身
                            neighbor_vecs.append(vec / dist)
            else:
                # 简单估计：边缘原子的缺失方向指向外侧
                # 对于纳米带，边缘在x或y方向
                center_xy = positions[:, :2].mean(axis=0)
                vec_to_center = center_xy - pos[:2]
                dist_to_center = np.linalg.norm(vec_to_center)
                if dist_to_center > 0.1:
                    missing_dir_xy = -vec_to_center / dist_to_center
                else:
                    missing_dir_xy = np.array([1.0, 0.0])
                missing_dir = np.array([missing_dir_xy[0], missing_dir_xy[1], 0.0])
                neighbor_vecs = [missing_dir]

            if len(neighbor_vecs) == 0:
                continue

            # 缺失方向 = 邻居方向的反方向平均
            missing_dir = -np.mean(neighbor_vecs, axis=0)
            missing_norm = np.linalg.norm(missing_dir)
            if missing_norm < 0.1:
                continue
            missing_dir = missing_dir / missing_norm

            # 添加钝化原子
            passivant_pos = pos + missing_dir * bond_length

            new_atoms.append(passivant)
            new_positions = new_atoms.get_positions()
            new_positions[-1] = passivant_pos
            new_atoms.set_positions(new_positions)
            added_count += 1

        print(f"  添加 {added_count} 个 {passivant} 钝化原子")

        return new_atoms

    # =========================================================================
    # 8. 衬底与界面建模 (Substrate & Interface)
    # =========================================================================

    def build_substrate_interface(self) -> Atoms:
        """
        衬底与界面建模 - 二维材料与衬底的界面结构
        """
        print(f"\n{'─'*50}")
        print("  [8] 衬底与界面建模 (Substrate Interface)")
        print(f"{'─'*50}")

        print("\n  --- 衬底选择 ---")

        substrate_source = get_choice_input("衬底来源", [
            "从数据库选择常见衬底",
            "从文件导入自定义衬底",
            "从表面切割构建衬底"
        ])

        substrate_atoms = None

        if substrate_source == 1:
            substrate_names = list(SUBSTRATE_DATABASE.keys())
            sub_idx = get_choice_input("选择衬底", substrate_names)
            sub_name = substrate_names[sub_idx - 1]
            sub_data = SUBSTRATE_DATABASE[sub_name]

            print(f"\n  构建 {sub_name} 衬底...")

            if 'SiO2' in sub_name:
                substrate_atoms = self._build_sio2_substrate(sub_data)
            elif 'Si_' in sub_name:
                substrate_atoms = self._build_si_substrate(sub_data)
            elif 'SiC' in sub_name:
                substrate_atoms = self._build_sic_substrate(sub_data)
            elif 'hBN' in sub_name:
                substrate_atoms = self._build_hbn_substrate(sub_data)
            elif 'Al2O3' in sub_name:
                substrate_atoms = self._build_al2o3_substrate(sub_data)
            elif 'Au_' in sub_name or 'Cu_' in sub_name or 'Ag_' in sub_name or 'Pt_' in sub_name:
                substrate_atoms = self._build_metal_substrate(sub_name, sub_data)
            elif 'TiO2' in sub_name:
                substrate_atoms = self._build_tio2_substrate(sub_data)
            else:
                substrate_atoms = self._build_generic_substrate(sub_data, sub_name)

        elif substrate_source == 2:
            substrate_atoms = self._load_input_structure("输入衬底结构文件")

        else:
            bulk_substrate = self._load_input_structure("输入衬底块体结构")
            h = get_int_input("衬底表面 Miller h", 1)
            k = get_int_input("衬底表面 Miller k", 1)
            l = get_int_input("衬底表面 Miller l", 1)
            sub_layers = get_int_input("衬底层数", 6, min_val=2, max_val=20)
            sub_vacuum = get_float_input("衬底真空层 (Å)", 15.0)

            structure = _atoms_to_pymatgen(bulk_substrate)
            
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                sga = SpacegroupAnalyzer(structure)
                conventional = sga.get_conventional_standard_structure()

                slab_gen = SlabGenerator(
                    conventional,
                    miller_index=(h, k, l),
                    min_slab_size=sub_layers * 2.0,
                    min_vacuum_size=sub_vacuum,
                    lll_reduce=True,
                    center_slab=True,
                    primitive=True
                )
                slabs = slab_gen.get_slabs()
            if slabs:
                substrate_atoms = _pymatgen_to_atoms(slabs[0])
            else:
                raise StructureError("无法生成衬底表面")

        print("\n  --- 吸附材料 ---")
        adsorbate_atoms = self._load_input_structure("输入二维材料结构")

        print("\n  --- 界面参数 ---")

        sub_cell = substrate_atoms.get_cell()[:2, :2]
        ads_cell = adsorbate_atoms.get_cell()[:2, :2]

        mismatch_a, mismatch_b = _get_lattice_mismatch(sub_cell, ads_cell)
        print(f"\n  晶格匹配分析:")
        print(f"    衬底: a={np.linalg.norm(sub_cell[0]):.4f}, b={np.linalg.norm(sub_cell[1]):.4f}")
        print(f"    吸附层: a={np.linalg.norm(ads_cell[0]):.4f}, b={np.linalg.norm(ads_cell[1]):.4f}")
        print(f"    失配: {mismatch_a*100:.2f}%, {mismatch_b*100:.2f}%")

        if max(mismatch_a, mismatch_b) > 0.05:
            print("  ⚠ 晶格失配较大")
            strain_choice = get_choice_input("应变处理方式", [
                "应变二维材料以匹配衬底",
                "应变衬底以匹配二维材料",
                "构建公度超胞",
                "不施加应变 (直接堆叠)"
            ])

            if strain_choice == 1:
                adsorbate_atoms = self._strain_2d(adsorbate_atoms, sub_cell)
            elif strain_choice == 2:
                substrate_atoms = self._strain_2d(substrate_atoms, ads_cell)
            elif strain_choice == 3:
                substrate_atoms, adsorbate_atoms = self._build_commensurate_supercell(
                    substrate_atoms, adsorbate_atoms)

        interface_distance = get_float_input("界面距离 (Å)", 3.0, min_val=1.5, max_val=10.0)

        alignment = get_choice_input("对齐方式", [
            "中心对齐",
            "原点对齐",
            "自定义平移"
        ])

        shift = (0.0, 0.0)
        if alignment == 3:
            shift_x = get_float_input("x方向平移 (fractional)", 0.0)
            shift_y = get_float_input("y方向平移 (fractional)", 0.0)
            shift = (shift_x, shift_y)

        fix_substrate = get_yes_no_input("是否固定衬底原子?", True)
        fix_layers = 2
        if fix_substrate:
            fix_layers = get_int_input("固定衬底层数 (从底部)", 2, min_val=1)

        vacuum = get_float_input("顶部真空层 (Å)", DEFAULT_VACUUM)

        print("\n  正在构建界面结构...")
        interface = self._build_interface(substrate_atoms, adsorbate_atoms,
                                          interface_distance, alignment, shift,
                                          fix_substrate, fix_layers, vacuum)

        formula = interface.get_chemical_formula()
        filename = f"interface_{formula}.vasp"
        self._save_result(interface, filename, "interface")

        print(f"\n  --- 界面结构信息 ---")
        print(f"  化学式: {formula}")
        print(f"  总原子数: {len(interface)}")
        print(f"  界面距离: {interface_distance} Å")
        print(f"  衬底固定: {'是' if fix_substrate else '否'}")

        return interface

    def _build_interface(self, substrate: Atoms, adsorbate: Atoms,
                         distance: float, alignment: int,
                         shift: Tuple[float, float],
                         fix_substrate: bool, fix_layers: int,
                         vacuum: float) -> Atoms:

        sub_cell = substrate.get_cell()
        ads_cell = adsorbate.get_cell()

        adsorbate = adsorbate.copy()
        new_cell = ads_cell.copy()
        new_cell[:2, :2] = sub_cell[:2, :2]
        adsorbate.set_cell(new_cell, scale_atoms=True)

        sub_positions = substrate.get_positions()
        ads_positions = adsorbate.get_positions()

        sub_z_max = sub_positions[:, 2].max()
        sub_z_min = sub_positions[:, 2].min()

        ads_z_min = ads_positions[:, 2].min()
        ads_thickness = ads_positions[:, 2].max() - ads_z_min

        z_shift = sub_z_max + distance - ads_z_min
        ads_positions[:, 2] += z_shift

        if alignment == 1:
            sub_center_xy = sub_positions[:, :2].mean(axis=0)
            ads_center_xy = ads_positions[:, :2].mean(axis=0)
            ads_positions[:, :2] += sub_center_xy - ads_center_xy
        elif alignment == 3:
            ads_positions[:, 0] += shift[0] * sub_cell[0, 0]
            ads_positions[:, 1] += shift[1] * sub_cell[1, 1]

        adsorbate.set_positions(ads_positions)

        interface = substrate.copy()
        interface.extend(adsorbate)

        all_positions = interface.get_positions()
        z_max = all_positions[:, 2].max()
        z_min = all_positions[:, 2].min()

        new_cell = sub_cell.copy()
        new_cell[2, 2] = z_max - z_min + vacuum
        interface.set_cell(new_cell, scale_atoms=False)

        all_positions = interface.get_positions()
        all_positions[:, 2] -= z_min - vacuum / 2
        interface.set_positions(all_positions)

        if fix_substrate:
            interface = _fix_bottom_layers(interface, fix_layers, axis=2)

        return interface

    def _build_sio2_substrate(self, params: Dict) -> Atoms:
        a, b, c = params['a'], params['b'], params['c']
        gamma = np.radians(params['gamma'])

        cell = np.array([
            [a, 0, 0],
            [b * np.cos(gamma), b * np.sin(gamma), 0],
            [0, 0, c]
        ])

        positions = []
        symbols = []

        n_layers = 3
        for i in range(n_layers):
            z = i * 2.2
            positions.extend([
                [0.0, 0.0, z],
                [a/2, b/2*np.sin(gamma), z]
            ])
            symbols.extend(['Si', 'Si'])

            positions.extend([
                [a/4, b/4*np.sin(gamma), z + 0.8],
                [3*a/4, 3*b/4*np.sin(gamma), z + 0.8]
            ])
            symbols.extend(['O', 'O'])

        atoms = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)
        atoms = _add_vacuum(atoms, 15.0)
        return atoms

    def _build_si_substrate(self, params: Dict) -> Atoms:
        a = params['a']
        si = Atoms('Si2',
                   positions=[[0, 0, 0], [0.25*a, 0.25*a, 0.25*a]],
                   cell=[a, a, a],
                   pbc=True)
        si = si * (3, 3, 4)
        si = _add_vacuum(si, 15.0)
        return si

    def _build_sic_substrate(self, params: Dict) -> Atoms:
        a = params['a']
        c = params['c']

        cell = np.array([[a, 0, 0],
                         [a/2, a*np.sqrt(3)/2, 0],
                         [0, 0, c]])

        positions = [
            [0, 0, 0],
            [2*a/3, a/3/np.sqrt(3), c/8],
            [0, 0, c/2],
            [2*a/3, a/3/np.sqrt(3), 5*c/8]
        ]
        symbols = ['Si', 'C', 'Si', 'C']

        atoms = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)
        atoms = atoms * (3, 3, 2)
        atoms = _add_vacuum(atoms, 15.0)
        return atoms

    def _build_hbn_substrate(self, params: Dict) -> Atoms:
        a = params['a']

        cell = np.array([[a, 0, 0],
                         [a/2, a*np.sqrt(3)/2, 0],
                         [0, 0, 20.0]])

        positions = [
            [0, 0, 10.0],
            [a/2, a*np.sqrt(3)/6, 10.0]
        ]
        symbols = ['B', 'N']

        atoms = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)
        atoms = atoms * (4, 4, 1)
        return atoms

    def _build_al2o3_substrate(self, params: Dict) -> Atoms:
        a = params['a']
        c = params['c']

        cell = np.array([[a, 0, 0],
                         [a/2, a*np.sqrt(3)/2, 0],
                         [0, 0, c/3]])

        positions = [
            [0, 0, 0],
            [a/3, a/3/np.sqrt(3), 0.8],
            [2*a/3, 2*a/3/np.sqrt(3), 0.8],
            [0, 0, 1.6]
        ]
        symbols = ['Al', 'O', 'O', 'Al']

        atoms = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)
        atoms = atoms * (3, 3, 3)
        atoms = _add_vacuum(atoms, 15.0)
        return atoms

    def _build_metal_substrate(self, name: str, params: Dict) -> Atoms:
        a = params['a']
        c = params['c']
        element = name.split('_')[0]

        cell = np.array([[a, 0, 0],
                         [a/2, a*np.sqrt(3)/2, 0],
                         [0, 0, c]])

        positions = []
        n_layers = 4
        for i in range(n_layers):
            z = i * c / n_layers
            if i % 3 == 0:
                positions.extend([[0, 0, z], [a/2, a*np.sqrt(3)/6, z]])
            elif i % 3 == 1:
                positions.extend([[a/2, a*np.sqrt(3)/2, z], [0, a*np.sqrt(3)/3, z]])
            else:
                positions.extend([[a/2, a*np.sqrt(3)/6, z], [a, a*np.sqrt(3)/3, z]])

        symbols = [element] * len(positions)
        atoms = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)
        atoms = _add_vacuum(atoms, 15.0)
        return atoms

    def _build_tio2_substrate(self, params: Dict) -> Atoms:
        a = params['a']
        c = params['c']

        cell = np.array([[a, 0, 0],
                         [0, c, 0],
                         [0, 0, 20.0]])

        positions = [
            [0, 0, 10.0],
            [a/2, c/2, 10.0],
            [0.25*a, 0.25*c, 11.0],
            [0.75*a, 0.25*c, 11.0],
            [0.25*a, 0.75*c, 11.0],
            [0.75*a, 0.75*c, 11.0],
            [0, 0, 12.0],
            [a/2, c/2, 12.0],
        ]
        symbols = ['Ti', 'Ti', 'O', 'O', 'O', 'O', 'Ti', 'Ti']

        atoms = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)
        atoms = atoms * (3, 3, 1)
        return atoms

    def _build_generic_substrate(self, params: Dict, name: str) -> Atoms:
        a = params.get('a', 4.0)
        b = params.get('b', a)
        c = params.get('c', 20.0)
        gamma = np.radians(params.get('gamma', 90))

        cell = np.array([
            [a, 0, 0],
            [b * np.cos(gamma), b * np.sin(gamma), 0],
            [0, 0, c]
        ])

        positions = [[0, 0, c/2]]
        symbols = ['X']

        atoms = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)
        atoms = atoms * (3, 3, 1)
        atoms = _add_vacuum(atoms, 15.0)
        return atoms

    # =========================================================================
    # 9. 滑移铁电结构生成 (Sliding Ferroelectricity)
    # =========================================================================

    def build_sliding_ferroelectric(self) -> Atoms:
        """
        滑移铁电结构生成 - 通过层间相对面内滑移构建铁电双稳态结构
        """
        print(f"\n{'─'*50}")
        print("  [9] 滑移铁电结构生成 (Sliding Ferroelectricity)")
        print(f"{'─'*50}")

        print("\n  提示: 需要输入双层(或多层)层状结构")
        print("  典型体系: 双层3R-MoS₂, 双层BN, 双层WTe₂, In₂Se₃等")

        bilayer = self._load_input_structure("输入双层/多层结构文件")

        n_layers, layer_indices = self._identify_layers(bilayer)
        print(f"\n  识别到 {n_layers} 个原子层")

        if n_layers < 2:
            raise StructureError("滑移铁电需要至少两层结构")

        if n_layers == 2:
            bottom_layer_idx = 0
            top_layer_idx = 1
            print("  自动选择: 层0(底) ↔ 层1(顶)")
        else:
            print("\n  选择要相对滑移的相邻两层:")
            bottom_layer_idx = get_int_input("底层索引", 0, min_val=0, max_val=n_layers-2)
            top_layer_idx = get_int_input("顶层索引", bottom_layer_idx+1,
                                            min_val=bottom_layer_idx+1, max_val=n_layers-1)

        bottom_layer, top_layer = self._split_bilayer(
            bilayer, layer_indices, bottom_layer_idx, top_layer_idx
        )

        config = self._configure_sliding_ferroelectric(bottom_layer, top_layer)

        print("\n  --- 生成滑移结构 ---")

        mode = get_choice_input("生成模式", [
            "单点滑移 (生成特定滑移量的结构)",
            "滑移路径扫描 (生成势能面采样系列结构)",
            "铁电双稳态对 (生成 ±δ 两个结构)",
            "高对称路径自动扫描"
        ])

        if mode == 1:
            result = self._generate_single_slide(bottom_layer, top_layer, config)
        elif mode == 2:
            result = self._generate_slide_path(bottom_layer, top_layer, config)
        elif mode == 3:
            result = self._generate_bistable_pair(bottom_layer, top_layer, config)
        else:
            result = self._generate_high_symmetry_path(bottom_layer, top_layer, config)

        return result

    def _identify_layers(self, atoms: Atoms,
                         tolerance: float = DEFAULT_LAYER_TOLERANCE) -> Tuple[int, List[np.ndarray]]:
        positions = atoms.get_positions()
        z_coords = positions[:, 2]

        sorted_indices = np.argsort(z_coords)
        sorted_z = z_coords[sorted_indices]

        layers = []
        current_layer = [sorted_indices[0]]
        current_z = sorted_z[0]

        for idx, z in zip(sorted_indices[1:], sorted_z[1:]):
            if abs(z - current_z) <= tolerance:
                current_layer.append(idx)
            else:
                layers.append(np.array(current_layer))
                current_layer = [idx]
                current_z = z

        layers.append(np.array(current_layer))

        return len(layers), layers

    def _split_bilayer(self, atoms: Atoms,
                       layer_indices: List[np.ndarray],
                       bottom_idx: int,
                       top_idx: int) -> Tuple[Atoms, Atoms]:
        bottom_atoms = atoms[layer_indices[bottom_idx]].copy()
        top_atoms = atoms[layer_indices[top_idx]].copy()

        bottom_z = bottom_atoms.get_positions()[:, 2].min()
        bottom_pos = bottom_atoms.get_positions()
        bottom_pos[:, 2] -= bottom_z
        bottom_atoms.set_positions(bottom_pos)

        top_z = top_atoms.get_positions()[:, 2].min()
        top_pos = top_atoms.get_positions()
        top_pos[:, 2] -= top_z
        top_atoms.set_positions(top_pos)

        return bottom_atoms, top_atoms

    def _configure_sliding_ferroelectric(self,
                                         bottom: Atoms,
                                         top: Atoms) -> SlidingFerroelectricConfig:
        print("\n  --- 滑移参数配置 ---")

        cell = bottom.get_cell()
        a_len = np.linalg.norm(cell[0])
        b_len = np.linalg.norm(cell[1])

        print(f"\n  底层晶格参数: a={a_len:.4f}Å, b={b_len:.4f}Å")
        print(f"  建议滑移幅度: ~0.1-0.5Å (通常为晶格常数的1/6到1/3)")

        direction_choice = get_choice_input("滑移方向", [
            "自动检测高对称方向",
            "沿a方向 (x)",
            "沿b方向 (y)",
            "沿a+b方向",
            "沿a-b方向",
            "自定义矢量"
        ])

        if direction_choice == 1:
            slide_direction = self._detect_high_symmetry_slide_direction(bottom)
            print(f"  检测到高对称滑移方向: {slide_direction}")
        elif direction_choice == 2:
            slide_direction = "x"
        elif direction_choice == 3:
            slide_direction = "y"
        elif direction_choice == 4:
            slide_direction = "x+y"
        elif direction_choice == 5:
            slide_direction = "x-y"
        else:
            slide_direction = "custom"

        default_slide = min(a_len, b_len) / 6
        slide_mag = get_float_input("滑移幅度 (Å)", default_slide, min_val=0.0, max_val=max(a_len, b_len))

        if slide_direction == "x":
            slide_vector = (slide_mag / a_len, 0.0)
        elif slide_direction == "y":
            slide_vector = (0.0, slide_mag / b_len)
        elif slide_direction == "x+y":
            slide_vector = (slide_mag / (a_len * np.sqrt(2)), slide_mag / (b_len * np.sqrt(2)))
        elif slide_direction == "x-y":
            slide_vector = (slide_mag / (a_len * np.sqrt(2)), -slide_mag / (b_len * np.sqrt(2)))
        elif slide_direction == "custom":
            sx = get_float_input("滑移矢量 x分量 (fractional)", 0.0)
            sy = get_float_input("滑移矢量 y分量 (fractional)", 0.0)
            slide_vector = (sx, sy)
        else:
            slide_vector = slide_direction

        current_gap = 3.5
        print(f"\n  当前估算层间距: {current_gap:.3f}Å")
        adjust_gap = get_yes_no_input("是否调整层间距?", False)
        interlayer_dist = None
        if adjust_gap:
            interlayer_dist = get_float_input("目标层间距 (Å)", current_gap, min_val=1.5, max_val=10.0)

        vacuum = get_float_input("真空层厚度 (Å)", DEFAULT_VACUUM, min_val=5.0)

        fix_bottom = get_yes_no_input("固定底层原子?", True)
        fix_slide = get_yes_no_input("固定滑移层原子位置 (用于势能面扫描)?", False)

        calc_pol = get_yes_no_input("标记此结构用于极化计算?", False)

        mag_order = None
        has_magnetic = get_yes_no_input("是否设置磁性序 (多铁性研究)?", False)
        if has_magnetic:
            mag_choice = get_choice_input("磁性序类型", [
                "铁磁 (FM)",
                "层间反铁磁 (AFM)",
                "自定义MAGMOM"
            ])
            mag_order = ["FM", "AFM", "custom"][mag_choice - 1]

        return SlidingFerroelectricConfig(
            slide_vector=slide_vector,
            slide_direction=slide_direction,
            slide_magnitude=slide_mag,
            interlayer_distance=interlayer_dist,
            vacuum=vacuum,
            fix_bottom_layer=fix_bottom,
            fix_slide_layer=fix_slide,
            calculate_polarization=calc_pol,
            magnetic_order=mag_order
        )

    def _detect_high_symmetry_slide_direction(self, atoms: Atoms) -> Tuple[float, float]:
        cell = atoms.get_cell()[:2, :2]
        a, b = np.linalg.norm(cell[0]), np.linalg.norm(cell[1])
        angle = np.arccos(np.dot(cell[0], cell[1]) / (a * b))

        is_hexagonal = abs(a - b) < 0.1 and abs(angle - np.pi/3) < 0.1

        if is_hexagonal:
            return (0.5, 0.0)
        else:
            if a <= b:
                return (0.5, 0.0)
            else:
                return (0.0, 0.5)

    def _estimate_interlayer_distance(self, bottom: Atoms, top: Atoms) -> float:
        return 3.5

    def _apply_slide(self, layer: Atoms,
                     slide_vector: Tuple[float, float],
                     cell: np.ndarray) -> Atoms:
        new_layer = layer.copy()
        positions = new_layer.get_positions()

        slide_cart = slide_vector[0] * cell[0] + slide_vector[1] * cell[1]

        positions[:, 0] += slide_cart[0]
        positions[:, 1] += slide_cart[1]

        new_layer.set_positions(positions)
        return new_layer

    def _combine_sliding_layers(self, bottom: Atoms,
                                 top: Atoms,
                                 config: SlidingFerroelectricConfig) -> Atoms:
        if config.interlayer_distance is not None:
            top_pos = top.get_positions()
            current_gap = top_pos[:, 2].min() - bottom.get_positions()[:, 2].max()
            if current_gap > 0:
                z_shift = config.interlayer_distance - current_gap
                top_pos[:, 2] += z_shift
                top.set_positions(top_pos)

        combined = bottom.copy()
        combined.extend(top)

        combined = _add_vacuum(combined, config.vacuum, axis=2)

        constraints = []
        if config.fix_bottom_layer:
            bottom_indices = list(range(len(bottom)))
            constraints.append(FixAtoms(indices=bottom_indices))

        if config.fix_slide_layer:
            top_indices = list(range(len(bottom), len(combined)))
            constraints.append(FixAtoms(indices=top_indices))

        if constraints:
            combined.set_constraint(constraints)

        return combined

    def _generate_single_slide(self, bottom: Atoms, top: Atoms,
                                config: SlidingFerroelectricConfig) -> Atoms:
        print(f"\n  生成单点滑移结构...")
        print(f"  滑移矢量 (fractional): ({config.slide_vector[0]:.4f}, {config.slide_vector[1]:.4f})")

        cell = bottom.get_cell()
        slid_top = self._apply_slide(top, config.slide_vector, cell)

        result = self._combine_sliding_layers(bottom, slid_top, config)

        formula = result.get_chemical_formula()
        sx, sy = config.slide_vector
        filename = f"sliding_{formula}_sx{sx:.3f}_sy{sy:.3f}.vasp"
        filepath = self._save_result(result, filename, "sliding_ferroelectric")

        if config.calculate_polarization:
            self._generate_polarization_input(filepath, config)

        if config.magnetic_order:
            self._generate_magnetic_incar(filepath, config.magnetic_order, result)

        print(f"\n  --- 滑移铁电结构信息 ---")
        print(f"  化学式: {formula}")
        print(f"  总原子数: {len(result)}")
        print(f"  滑移矢量: ({sx:.4f}, {sy:.4f}) [fractional]")
        print(f"  层间距: {config.interlayer_distance or '保持原值'} Å")
        if config.calculate_polarization:
            print(f"  已生成极化计算辅助文件")

        return result

    def _generate_bistable_pair(self, bottom: Atoms, top: Atoms,
                                 config: SlidingFerroelectricConfig) -> Atoms:
        print("\n  生成铁电双稳态对 (+δ / -δ)...")

        cell = bottom.get_cell()
        sx, sy = config.slide_vector

        print("\n  --- 生成 +δ (正向滑移) 结构 ---")
        config_pos = SlidingFerroelectricConfig(**config.__dict__)
        config_pos.slide_vector = (sx, sy)
        config_pos.title = f"{config.title}_plus"

        slid_top_pos = self._apply_slide(top.copy(), (sx, sy), cell)
        result_pos = self._combine_sliding_layers(bottom, slid_top_pos, config_pos)

        formula = result_pos.get_chemical_formula()
        filename_pos = f"sliding_{formula}_plus.vasp"
        self._save_result(result_pos, filename_pos, "sliding_ferroelectric/bistable")

        print("\n  --- 生成 -δ (反向滑移) 结构 ---")
        config_neg = SlidingFerroelectricConfig(**config.__dict__)
        config_neg.slide_vector = (-sx, -sy)
        config_neg.title = f"{config.title}_minus"

        slid_top_neg = self._apply_slide(top.copy(), (-sx, -sy), cell)
        result_neg = self._combine_sliding_layers(bottom, slid_top_neg, config_neg)

        filename_neg = f"sliding_{formula}_minus.vasp"
        self._save_result(result_neg, filename_neg, "sliding_ferroelectric/bistable")

        print("\n  --- 生成参考结构 (未滑移) ---")
        config_ref = SlidingFerroelectricConfig(**config.__dict__)
        config_ref.slide_vector = (0.0, 0.0)
        config_ref.title = f"{config.title}_reference"

        result_ref = self._combine_sliding_layers(bottom, top.copy(), config_ref)
        filename_ref = f"sliding_{formula}_reference.vasp"
        self._save_result(result_ref, filename_ref, "sliding_ferroelectric/bistable")

        print(f"\n  --- 铁电双稳态生成完毕 ---")
        print(f"  共生成3个结构:")
        print(f"    1) {filename_ref} (参考态, 中心对称)")
        print(f"    2) {filename_pos} (+δ 极化态)")
        print(f"    3) {filename_neg} (-δ 极化态)")
        print(f"\n  后续计算建议:")
        print(f"    - 分别优化三个结构，比较能量")
        print(f"    - 用NEB计算 +δ ↔ -δ 翻转势垒")
        print(f"    - Berry phase计算各态极化强度")

        return result_pos

    def _generate_slide_path(self, bottom: Atoms, top: Atoms,
                              config: SlidingFerroelectricConfig) -> Atoms:
        print(f"\n  生成滑移路径扫描结构...")

        n_points = get_int_input("采样点数", config.n_slide_points, min_val=3, max_val=50)
        sx_max, sy_max = config.slide_vector

        cell = bottom.get_cell()
        formula = bottom.get_chemical_formula()

        path_structures = []

        for i in range(n_points):
            frac = i / (n_points - 1)
            sx = sx_max * frac
            sy = sy_max * frac

            slid_top = self._apply_slide(top.copy(), (sx, sy), cell)
            result = self._combine_sliding_layers(bottom, slid_top, config)

            filename = f"sliding_path_{formula}_p{i:02d}_sx{sx:.4f}_sy{sy:.4f}.vasp"
            filepath = self._save_result(result, filename, "sliding_ferroelectric/path")
            path_structures.append(filepath)

            print(f"    点 {i+1}/{n_points}: ({sx:.4f}, {sy:.4f}) -> {filename}")

        self._generate_batch_script(path_structures, "slide_path")

        print(f"\n  --- 滑移路径扫描生成完毕 ---")
        print(f"  共生成 {n_points} 个结构")
        print(f"  建议: 用这些结构计算总能，拟合滑移势能面")

        return result

    def _generate_high_symmetry_path(self, bottom: Atoms, top: Atoms,
                                      config: SlidingFerroelectricConfig) -> Atoms:
        print("\n  生成高对称滑移路径...")

        cell = bottom.get_cell()[:2, :2]
        a, b = np.linalg.norm(cell[0]), np.linalg.norm(cell[1])
        angle = np.arccos(np.dot(cell[0], cell[1]) / (a * b))
        is_hexagonal = abs(a - b) < 0.1 and abs(angle - np.pi/3) < 0.1

        if is_hexagonal:
            print("  检测到六方晶格，使用 Γ→M→K→Γ 路径")
            gamma = (0.0, 0.0)
            m_point = (0.5, 0.0)
            k_point = (1.0/3.0, 1.0/3.0)

            path_points = [gamma, m_point, k_point, gamma]
            path_labels = ["Gamma", "M", "K", "Gamma"]
        else:
            print("  非六方晶格，使用 Γ→X→S→Y→Γ 路径")
            gamma = (0.0, 0.0)
            x_point = (0.5, 0.0)
            s_point = (0.5, 0.5)
            y_point = (0.0, 0.5)

            path_points = [gamma, x_point, s_point, y_point, gamma]
            path_labels = ["Gamma", "X", "S", "Y", "Gamma"]

        n_per_segment = get_int_input("每段路径采样点数", 5, min_val=2, max_val=20)

        cell = bottom.get_cell()
        formula = bottom.get_chemical_formula()
        all_structures = []

        for seg_idx in range(len(path_points) - 1):
            p1, p2 = path_points[seg_idx], path_points[seg_idx + 1]
            label1, label2 = path_labels[seg_idx], path_labels[seg_idx + 1]

            print(f"\n  路径段 {seg_idx+1}: {label1} → {label2}")

            for i in range(n_per_segment):
                frac = i / (n_per_segment - 1) if n_per_segment > 1 else 0
                sx = p1[0] + frac * (p2[0] - p1[0])
                sy = p1[1] + frac * (p2[1] - p1[1])

                slid_top = self._apply_slide(top.copy(), (sx, sy), cell)
                result = self._combine_sliding_layers(bottom, slid_top, config)

                filename = f"sliding_hsp_{formula}_{label1}to{label2}_p{i:02d}.vasp"
                filepath = self._save_result(result, filename, "sliding_ferroelectric/high_sym")
                all_structures.append(filepath)

                print(f"    点 {i+1}/{n_per_segment}: ({sx:.4f}, {sy:.4f})")

        self._generate_batch_script(all_structures, "high_sym_path")

        print(f"\n  --- 高对称路径扫描生成完毕 ---")
        print(f"  共生成 {len(all_structures)} 个结构")

        return result

    def _generate_polarization_input(self, structure_path: Path,
                                      config: SlidingFerroelectricConfig) -> None:
        print("  生成极化计算辅助文件...")

        incar_suggestions = """
# 滑移铁电极化计算 INCAR 建议
# ================================
# 1. 自洽计算 (LCALCPOL = .TRUE.)
LCALCPOL = .TRUE.
# 或
# 2. Berry phase 极化计算
LBERRY = .TRUE.
IGPAR = 3
NPPSTR = 8

# 3. k点网格建议使用 Gamma-centered, 如 12x12x1

# 4. ΔP = P(+δ) - P(-δ) 或 P(δ) - P(0)
"""

        pol_file = structure_path.parent / f"{structure_path.stem}_POLARIZATION.txt"
        with open(pol_file, 'w') as f:
            f.write(incar_suggestions)

        print(f"    已保存: {pol_file}")

    def _generate_magnetic_incar(self, structure_path: Path,
                                  mag_order: str,
                                  atoms: Atoms) -> None:
        print(f"  生成磁性序 ({mag_order}) INCAR 建议...")

        n_atoms = len(atoms)
        symbols = atoms.get_chemical_symbols()

        magnetic_elements = {'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'V', 'Ti',
                              'Ru', 'Rh', 'Pd', 'Os', 'Ir', 'Pt', 'Gd', 'Tb',
                              'Dy', 'Ho', 'Er'}

        mag_atoms = [(i, s) for i, s in enumerate(symbols) if s in magnetic_elements]

        if not mag_atoms:
            print("  警告: 未检测到常见磁性元素")
            return

        if mag_order == "FM":
            magmom = " ".join(["5.0" if s in magnetic_elements else "0.0"
                              for s in symbols])
            incar_text = f"""
# 铁磁序 (FM) INCAR 设置
ISPIN = 2
MAGMOM = {magmom}
"""
        elif mag_order == "AFM":
            magmom_list = []
            for i, s in enumerate(symbols):
                if s in magnetic_elements:
                    magmom_list.append("5.0" if i % 2 == 0 else "-5.0")
                else:
                    magmom_list.append("0.0")
            magmom = " ".join(magmom_list)
            incar_text = f"""
# 反铁磁序 (AFM) INCAR 设置
ISPIN = 2
MAGMOM = {magmom}
# 注意: 需根据实际磁结构调整MAGMOM符号
"""
        else:
            incar_text = """
# 自定义磁性序
ISPIN = 2
# 请手动设置 MAGMOM
"""

        mag_file = structure_path.parent / f"{structure_path.stem}_MAGNETIC.txt"
        with open(mag_file, 'w') as f:
            f.write(incar_text)

        print(f"    已保存: {mag_file}")

    def _generate_batch_script(self, structure_paths: List[Path],
                                job_name: str) -> None:
        script_content = f"""#!/bin/bash
# 滑移铁电批量计算脚本
# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 任务名称: {job_name}

for poscar in {" ".join([f"'{p.name}'" for p in structure_paths])}; do
    dir_name="${{poscar%.vasp}}"
    mkdir -p "$dir_name"
    cp "$poscar" "$dir_name/POSCAR"
    # cp INCAR_template "$dir_name/INCAR"
    # cp POTCAR "$dir_name/POTCAR"
    # cp KPOINTS "$dir_name/KPOINTS"
    # cd "$dir_name" && sbatch run_vasp.sh
    echo "准备完成: $dir_name"
done

echo "所有任务准备完毕，共 {len(structure_paths)} 个结构"
"""

        script_path = self.work_dir / "sliding_ferroelectric" / f"batch_{job_name}.sh"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        with open(script_path, 'w') as f:
            f.write(script_content)

        import os
        os.chmod(script_path, 0o755)

        print(f"    已生成批量脚本: {script_path}")


# =============================================================================
# 命令行入口 (保留)
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='MatBuilder 2D材料建模模块')
    parser.add_argument('-w', '--work-dir', type=str, default='.',
                        help='工作目录')
    parser.add_argument('--non-interactive', action='store_true',
                        help='非交互模式（用于脚本调用）')

    args = parser.parse_args()

    module = Struct2DModule()
    module.work_dir = Path(args.work_dir)

    if args.non_interactive:
        print("非交互模式：请通过Python API调用具体方法")
        print("可用方法:", [item[1] for item in module.MENU_ITEMS])
    else:
        module.run_interactive(None)


if __name__ == '__main__':
    main()
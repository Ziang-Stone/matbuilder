# -*- coding: utf-8 -*-
"""
Transform Module v0.2
功能：超胞构建、旋转、镜像、平移
"""

import os
import numpy as np

from matbuilder.core.base import ModuleBase
from matbuilder.core.pipeline import PipelineExecutor
from matbuilder.core.registry import ModuleRegistry
from matbuilder.utils.logging import Logger
from matbuilder.utils.validators import (
    get_float_input, get_int_input, get_choice_input, 
    get_yes_no_input, get_tuple_input
)


class TransformModule(ModuleBase):
    """结构变换模块：超胞、旋转、镜像、平移"""
    
    name = "transform"
    description = "Supercell, rotation, mirror, translation"
    
    def run(self, context) -> None:
        """编程式入口"""
        pass
    
    def run_interactive(self, context) -> None:
        """交互式入口"""
        self._interactive_menu(context)
    
    def _interactive_menu(self, ctx):
        while True:
            Logger.banner("Transform")
            Logger.info(f"Source: {ctx.structure_path or 'Not loaded'}")
            print("\n  ------------------- Transform Options ---------------------")
            Logger.menu_item("1", "Supercell            (超胞构建)")
            Logger.menu_item("2", "Rotation             (旋转)")
            Logger.menu_item("3", "Mirror               (镜像)")
            Logger.menu_item("4", "Translation          (平移)")
            Logger.menu_item("5", "Vacuum Slab          (添加真空层 — 二维材料)")
            Logger.menu_item("0", "Back to Main Menu")
            print("-" * 72)
            
            choice = input("\n  Select: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self._supercell_menu(ctx)
            elif choice == '2':
                self._rotation_menu(ctx)
            elif choice == '3':
                self._mirror_menu(ctx)
            elif choice == '4':
                self._translation_menu(ctx)
            elif choice == '5':
                self._vacuum_menu(ctx)
            else:
                Logger.error("Invalid option.")
                input("  Press Enter...")
    
    # ==================== 超胞构建 ====================
    
    def _supercell_menu(self, ctx):
        print("\n  --- Supercell ---")
        print("  Enter expansion factors (e.g., 2 2 2 for 2x2x2)")
        
        default = ctx.settings.default_supercell
        use_default = get_yes_no_input(f"  Use default {default}?", default=True)
        
        if use_default:
            nx, ny, nz = default
        else:
            nx, ny, nz = get_tuple_input("  Enter (nx ny nz): ", length=3)
        
        # 构建超胞
        new_structure = ctx.structure.copy()
        new_structure.make_supercell([nx, ny, nz])
        
        fname = self._generate_filename(ctx, "supercell", f"{nx}{ny}{nz}")
        self._write_and_report(ctx, new_structure, fname)
        input("\n  Press Enter...")
    
    # ==================== 旋转 ====================
    
    def _rotation_menu(self, ctx):
        print("\n  --- Rotation ---")
        print("  Available axes: x, y, z")
        
        axis = get_choice_input("  Rotation axis: ", ['x', 'y', 'z'])
        angle = get_float_input("  Rotation angle (degrees): ")
        
        # pymatgen 旋转
        from pymatgen.transformations.standard_transformations import RotationTransformation
        
        rot = RotationTransformation([1 if a == axis else 0 for a in ['x', 'y', 'z']], angle)
        new_structure = rot.apply_transformation(ctx.structure)
        
        fname = self._generate_filename(ctx, "rot", f"{axis}{int(angle)}")
        self._write_and_report(ctx, new_structure, fname)
        input("\n  Press Enter...")
    
    # ==================== 镜像 ====================
    
    def _mirror_menu(self, ctx):
        print("\n  --- Mirror ---")
        print("  Mirror plane: xy (z→-z), yz (x→-x), xz (y→-y)")
        
        plane = get_choice_input("  Mirror plane: ", ['xy', 'yz', 'xz'])
        
        new_structure = ctx.structure.copy()
        
        # 根据平面选择镜像轴
        axis_map = {'xy': 2, 'yz': 0, 'xz': 1}  # z, x, y
        flip_axis = axis_map[plane]
        
        # 翻转坐标
        for site in new_structure:
            coords = list(site.coords)
            coords[flip_axis] *= -1
            site.coords = coords
        
        fname = self._generate_filename(ctx, "mirror", plane)
        self._write_and_report(ctx, new_structure, fname)
        input("\n  Press Enter...")
    
    # ==================== 平移 ====================
    
    def _translation_menu(self, ctx):
        print("\n  --- Translation ---")
        print("  Enter translation vector in fractional coordinates")
        
        tx, ty, tz = get_tuple_input("  Enter (tx ty tz): ", length=3, dtype=float)
        
        new_structure = ctx.structure.copy()
        new_structure.translate_sites(
            indices=range(len(new_structure)),
            vector=[tx, ty, tz],
            frac_coords=True
        )
        
        fname = self._generate_filename(ctx, "trans", f"{tx:.2f}{ty:.2f}{tz:.2f}".replace('.', ''))
        self._write_and_report(ctx, new_structure, fname)
        input("\n  Press Enter...")
    
    # ==================== 真空层（二维材料） ====================
    
    def _vacuum_menu(self, ctx):
        print("\n  --- Vacuum Slab ---")
        print("  Add vacuum layer along c-axis for 2D materials")
        
        vacuum = get_float_input("  Vacuum thickness (Å): ")
        
        new_structure = ctx.structure.copy()
        lat = new_structure.lattice.matrix.copy()
        
        # 在 c 方向添加真空层
        old_c = lat[2, 2]
        new_c = old_c + vacuum
        lat[2, 2] = new_c
        
        # 更新晶格
        from pymatgen.core import Lattice
        new_structure.lattice = Lattice(lat)
        
        # 分数坐标不变，原子在 slab 中心
        fname = self._generate_filename(ctx, "vac", f"{int(vacuum)}A")
        self._write_and_report(ctx, new_structure, fname)
        input("\n  Press Enter...")
    
    # ==================== 通用辅助方法 ====================
    
    def _generate_filename(self, ctx, operation, suffix):
        """生成输出文件名"""
        base = os.path.splitext(os.path.basename(ctx.settings.input_file))[0]
        return f"{base}_{operation}_{suffix}.vasp"
    
    def _write_and_report(self, ctx, structure, fname):
        """写入文件并报告"""
        outpath = os.path.join(ctx.settings.struct_dir, fname)
        coord_type = ctx.metadata.get('original_coord_type', 'D')
        ctx.backend.write_structure(structure, outpath, coord_type=coord_type)
        
        Logger.success(f"Saved: {fname}")
        Logger.info(f"  Atoms: {len(structure)}")
        params = ctx.backend.get_lattice_params(structure)
        Logger.info(f"  Lattice: a={params['a']:.4f} b={params['b']:.4f} c={params['c']:.4f}")
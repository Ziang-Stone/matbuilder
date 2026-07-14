# -*- coding: utf-8 -*-
"""
Strain Module — 交互式实现
"""

import os

import numpy as np

from matbuilder.core.base import ModuleBase
from matbuilder.core.pipeline import PipelineExecutor
from matbuilder.utils.logging import Logger
from matbuilder.utils.validators import get_float_input

from .models import StrainConfig
from .operations import StrainOperations


class StrainModule(ModuleBase):
    """应变建模模块"""
    
    name = "strain"
    description = "Strain modeling: uniaxial, biaxial, shear, pure shear, hydrostatic"
    
    def run(self, context) -> None:
        """编程式入口"""
        pass  # v0.2 实现
    
    def run_interactive(self, context) -> None:
        """交互式入口"""
        self._interactive_menu(context)
    
    # ==================== 交互式菜单 ====================
    
    def _interactive_menu(self, ctx):
        while True:
            Logger.banner("Strain Modeling")
            Logger.info(f"Source: {ctx.structure_path or 'Not loaded'}")
            print("\n  ------------------- Strain Type ---------------------")
            Logger.menu_item("1", "Uniaxial Strain      (单轴: a / b / c)")
            Logger.menu_item("2", "Biaxial Strain       (双轴: ab / bc / ac)")
            Logger.menu_item("3", "Simple Shear         (简单剪切)")
            Logger.menu_item("4", "Pure Shear           (纯剪切)")
            Logger.menu_item("5", "Hydrostatic          (三轴静水压)")
            Logger.menu_item("0", "Back to Main Menu")
            print("-" * 72)
            
            choice = input("\n  Select: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self._uniaxial_menu(ctx)
            elif choice == '2':
                self._biaxial_menu(ctx)
            elif choice == '3':
                self._shear_menu(ctx, 'shear')
            elif choice == '4':
                self._shear_menu(ctx, 'pure_shear')
            elif choice == '5':
                self._hydrostatic_menu(ctx)
            else:
                Logger.error("Invalid option.")
                input("  Press Enter...")
    
    def _select_mode(self, allow_poisson=True):
        print("\n  --- Mode ---")
        Logger.menu_item("1", "Standard (标准，无修正)")
        if allow_poisson:
            Logger.menu_item("2", "Poisson Ratio Correction (泊松比修正)")
        Logger.menu_item("3", "Volume Conservation (体积守恒)")
        m = input("  Select: ").strip()
        
        mode = 'standard'
        poisson = None
        if m == '2' and allow_poisson:
            mode = 'poisson'
            poisson = get_float_input("  Enter Poisson ratio ν (default 0.3): ")
            if poisson < 0 or poisson >= 0.5:
                Logger.warn(f"ν={poisson} out of typical range [0, 0.5)")
        elif m == '3':
            mode = 'vol_conserve'
        return mode, poisson
    
    def _get_range(self):
        start = get_float_input("  Start strain (%): ")
        end = get_float_input("  End strain   (%): ")
        step = get_float_input("  Step size    (%): ")
        if step <= 0 or start > end:
            Logger.error("Invalid range!")
            return None, None, None
        return start, end, step
    
    def _generate_filename(self, ctx, strain_type, direction, percent, 
                           mode='standard', poisson=None):
        sign = '+' if percent >= 0 else '-'
        abs_val = abs(percent)
        val_str = f"{int(abs_val)}" if abs_val == int(abs_val) else f"{abs_val:.1f}"
        base = os.path.splitext(os.path.basename(ctx.settings.input_file))[0]
        
        prefix = {
            'uniaxial': '', 'biaxial': '',
            'shear': 'sh', 'pure_shear': 'pure',
            'hydrostatic': 'hydro'
        }.get(strain_type, '')
        
        mode_suffix = ''
        if mode == 'poisson' and poisson is not None:
            nu_str = f"{poisson:.2f}".replace('.', '')
            mode_suffix = f"_p{nu_str}"
        elif mode == 'vol_conserve':
            mode_suffix = '_vc'
        
        if strain_type == 'hydrostatic':
            return f"{base}_hydro_{sign}{val_str}{mode_suffix}.vasp"
        else:
            if prefix:
                return f"{base}_{prefix}{direction}_{sign}{val_str}{mode_suffix}.vasp"
            return f"{base}_{direction}_{sign}{val_str}{mode_suffix}.vasp"
    
    def _run_batch(self, ctx, strain_type, direction, start, end, step,
                   mode='standard', poisson=None):
        count = int((end - start) / step) + 1
        if count > ctx.settings.max_batch_files:
            cfm = input(f"  [Warn] 将生成 {count} 个文件，确认继续? (y/n): ").strip().lower()
            if cfm != 'y':
                return 0
        
        print(f"\n  Generating {count} files (Mode: {mode})...")
        n_gen = 0
        coord_type = ctx.metadata.get('original_coord_type', 'D')
        
        for i in range(count):
            p = start + i * step
            val = p / 100.0
            
            # 生成应变矩阵
            F = StrainOperations.get_strain_matrix(
                strain_type, direction, val, mode=mode, poisson=poisson
            )
            
            # 应用应变
            new_structure = ctx.backend.apply_strain(ctx.structure, F)
            
            # 生成文件名并写入
            fname = self._generate_filename(
                ctx, strain_type, direction, p, mode=mode, poisson=poisson
            )
            outpath = os.path.join(ctx.settings.struct_dir, fname)
            ctx.backend.write_structure(new_structure, outpath, coord_type=coord_type)
            
            n_gen += 1
            print(f"    {fname}")
        
        print(f"\n  Done! Generated {n_gen} files.")
        return n_gen
    
    # ==================== 各应变类型子菜单 ====================
    
    def _uniaxial_menu(self, ctx):
        d = input("  Direction (a/b/c): ").strip().lower()
        if d not in ['a', 'b', 'c']:
            Logger.error("Invalid direction.")
            input()
            return
        mode, poisson = self._select_mode()
        s, e, st = self._get_range()
        if s is None:
            return
        self._run_batch(ctx, 'uniaxial', d, s, e, st, mode=mode, poisson=poisson)
        input("\n  Press Enter...")
    
    def _biaxial_menu(self, ctx):
        d = input("  Plane (ab/bc/ac): ").strip().lower()
        if d not in ['ab', 'bc', 'ac']:
            Logger.error("Invalid plane.")
            input()
            return
        mode, poisson = self._select_mode()
        s, e, st = self._get_range()
        if s is None:
            return
        self._run_batch(ctx, 'biaxial', d, s, e, st, mode=mode, poisson=poisson)
        input("\n  Press Enter...")
    
    def _shear_menu(self, ctx, stype):
        names = {'shear': 'Simple Shear', 'pure_shear': 'Pure Shear'}
        print(f"\n  --- {names[stype]} ---")
        
        if stype == 'shear':
            print("  Directions: ab / bc / ac / ba / cb / ca")
            d = input("  Direction: ").strip().lower()
            if d not in ['ab', 'bc', 'ac', 'ba', 'cb', 'ca']:
                Logger.error("Invalid.")
                input()
                return
        else:
            print("  Planes: ab / bc / ac")
            d = input("  Plane: ").strip().lower()
            if d not in ['ab', 'bc', 'ac']:
                Logger.error("Invalid.")
                input()
                return
        
        print("  Note: Shear is naturally volume-conserving.")
        s, e, st = self._get_range()
        if s is None:
            return
        self._run_batch(ctx, stype, d, s, e, st, mode='standard')
        input("\n  Press Enter...")
    
    def _hydrostatic_menu(self, ctx):
        print("\n  --- Hydrostatic (Isotropic) ---")
        s, e, st = self._get_range()
        if s is None:
            return
        self._run_batch(ctx, 'hydrostatic', 'iso', s, e, st, mode='standard')
        input("\n  Press Enter...")
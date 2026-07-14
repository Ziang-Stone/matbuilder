# -*- coding: utf-8 -*-
"""
Symmetry Module v0.5
基于 pymatgen 的 SpacegroupAnalyzer 实现
"""
import os
import numpy as np

from matbuilder.core.base import ModuleBase
from matbuilder.utils.logging import Logger
from matbuilder.utils.validators import get_float_input, get_choice_input, get_yes_no_input

# 尝试导入 tabulate，若不存在则提供备用输出
try:
    from tabulate import tabulate
except ImportError:
    tabulate = None


class SymmetryModule(ModuleBase):
    name = "symmetry"
    description = "Crystal symmetry analysis via pymatgen & spglib"

    def run(self, context) -> None:
        pass

    def run_interactive(self, context) -> None:
        self._interactive_menu(context)

    def _interactive_menu(self, ctx):
        while True:
            Logger.banner("Symmetry Analysis")
            Logger.info(f"Source: {ctx.structure_path or 'Not loaded'}")
            print("\n  ------------------- Analysis Options ---------------------")
            Logger.menu_item("1", "Full Symmetry Report   (完整对称性报告)")
            Logger.menu_item("2", "Space Group Info       (空间群信息)")
            Logger.menu_item("3", "Find Primitive Cell    (找原胞)")
            Logger.menu_item("4", "Standardize Cell       (标准化晶胞)")
            Logger.menu_item("5", "Point Group & Symmetry Ops (点群与对称操作)")
            Logger.menu_item("6", "Wyckoff Positions      (Wyckoff 位置)")
            Logger.menu_item("7", "Strain Symmetry Track  (应变对称性追踪)")
            Logger.menu_item("0", "Back to Main Menu")
            print("-" * 72)
            
            choice = input("\n  Select: ").strip()
            if choice == '0':
                break
            elif choice == '1':
                self._full_report(ctx)
            elif choice == '2':
                self._space_group(ctx)
            elif choice == '3':
                self._primitive_cell(ctx)
            elif choice == '4':
                self._standardize_cell(ctx)
            elif choice == '5':
                self._point_group(ctx)
            elif choice == '6':
                self._wyckoff_positions(ctx)
            elif choice == '7':
                self._strain_tracking(ctx)
            else:
                Logger.error("Invalid option.")
                input("  Press Enter...")

    # ---------- 核心分析方法 ----------
    
    def _get_analyzer(self, ctx):
        """获取 SpacegroupAnalyzer 实例"""
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
        return SpacegroupAnalyzer(ctx.structure, symprec=0.01, angle_tolerance=5.0)

    def _full_report(self, ctx):
        """完整对称性报告"""
        if not ctx.has_structure():
            Logger.error("No structure loaded.")
            input(); return
        
        analyzer = self._get_analyzer(ctx)
        dataset = analyzer.get_symmetry_dataset()
        
        print("\n  ========== Full Symmetry Report ==========")
        # 使用属性接口（避免 DeprecationWarning）
        print(f"  Space Group Number    : {dataset.number}")
        print(f"  International Symbol  : {dataset.international}")
        print(f"  Hall Symbol           : {dataset.hall}")
        print(f"  Point Group           : {dataset.pointgroup}")
        print(f"  Crystal System        : {analyzer.get_crystal_system()}")
        print(f"  Laue Class            : {analyzer.get_lattice_type()}")
        
        # 对称操作数
        ops = analyzer.get_symmetry_operations()
        print(f"  Symmetry Operations   : {len(ops)}")
        
        # Wyckoff 符号（每个原子一个符号）
        wyckoffs = getattr(dataset, 'wyckoffs', [])
        if len(wyckoffs) > 0:
            unique_wyck = sorted(set(wyckoffs))
            print(f"  Wyckoff sites present : {', '.join(unique_wyck)}")
            # 显示原子到 Wyckoff 的映射（前10个）
            print("  Wyckoff mapping (atom index -> symbol):")
            for i, w in enumerate(wyckoffs[:10]):
                print(f"    [{i}] {w}")
            if len(wyckoffs) > 10:
                print(f"    ... and {len(wyckoffs)-10} more atoms")
        else:
            print("  Wyckoff symbols not available in dataset.")
        
        # 变换矩阵
        trans_mat = getattr(dataset, 'transformation_matrix', None)
        if trans_mat is not None:
            print(f"  Transformation matrix :\n{trans_mat}")
        
        Logger.info("Report complete.")
        input("\n  Press Enter...")

    def _space_group(self, ctx):
        """空间群信息"""
        if not ctx.has_structure():
            Logger.error("No structure loaded.")
            input(); return
        
        analyzer = self._get_analyzer(ctx)
        dataset = analyzer.get_symmetry_dataset()
        
        print("\n  ========== Space Group ==========")
        print(f"  Number   : {dataset.number}")
        print(f"  Symbol   : {dataset.international}")
        print(f"  Hall     : {dataset.hall}")
        print(f"  System   : {analyzer.get_crystal_system()}")
        
        # 等效位置
        print("\n  Equivalent positions (fractional):")
        for i, op in enumerate(analyzer.get_symmetry_operations()[:10]):
            print(f"    {i+1}. rotation:\n{op.rotation_matrix}")
            print(f"       translation: {op.translation_vector}")
        if len(analyzer.get_symmetry_operations()) > 10:
            print(f"    ... and {len(analyzer.get_symmetry_operations())-10} more")
        
        input("\n  Press Enter...")

    def _primitive_cell(self, ctx):
        """找原胞"""
        if not ctx.has_structure():
            Logger.error("No structure loaded.")
            input(); return
        
        analyzer = self._get_analyzer(ctx)
        primitive = analyzer.get_primitive_standard_structure()
        
        fname = f"primitive_{ctx.settings.input_file}"
        outpath = os.path.join(ctx.settings.struct_dir, fname)
        coord_type = ctx.metadata.get('original_coord_type', 'D')
        ctx.backend.write_structure(primitive, outpath, coord_type=coord_type)
        
        Logger.success(f"Primitive cell saved as: {fname}")
        Logger.info(f"  Original atoms: {len(ctx.structure)} → Primitive: {len(primitive)}")
        input("\n  Press Enter...")

    def _standardize_cell(self, ctx):
        """标准化晶胞"""
        if not ctx.has_structure():
            Logger.error("No structure loaded.")
            input(); return
        
        analyzer = self._get_analyzer(ctx)
        standard = analyzer.get_conventional_standard_structure()
        
        fname = f"standard_{ctx.settings.input_file}"
        outpath = os.path.join(ctx.settings.struct_dir, fname)
        coord_type = ctx.metadata.get('original_coord_type', 'D')
        ctx.backend.write_structure(standard, outpath, coord_type=coord_type)
        
        Logger.success(f"Standardized cell saved as: {fname}")
        Logger.info(f"  Original atoms: {len(ctx.structure)} → Standard: {len(standard)}")
        input("\n  Press Enter...")

    def _point_group(self, ctx):
        """点群与对称操作"""
        if not ctx.has_structure():
            Logger.error("No structure loaded.")
            input(); return
        
        analyzer = self._get_analyzer(ctx)
        ops = analyzer.get_symmetry_operations()
        
        print("\n  ========== Point Group ==========")
        print(f"  Point Group: {analyzer.get_point_group_symbol()}")
        print(f"  Operations : {len(ops)}")
        
        # 按旋转部分分类
        rot_mats = {}
        for op in ops:
            key = str(op.rotation_matrix)
            if key not in rot_mats:
                rot_mats[key] = []
            rot_mats[key].append(op.translation_vector)
        
        print(f"\n  Rotation types: {len(rot_mats)}")
        for i, (mat, trans) in enumerate(rot_mats.items()):
            print(f"    [{i+1}] Rotation matrix:\n{mat}")
            print(f"        Translation vectors: {trans[:3]}{'...' if len(trans)>3 else ''}")
        
        input("\n  Press Enter...")

    def _wyckoff_positions(self, ctx):
        """Wyckoff 位置输出（基于等价原子分类）"""
        if not ctx.has_structure():
            Logger.error("No structure loaded.")
            input(); return
        
        analyzer = self._get_analyzer(ctx)
        dataset = analyzer.get_symmetry_dataset()
        
        wyckoffs = getattr(dataset, 'wyckoffs', None)
        equiv_atoms = getattr(dataset, 'equivalent_atoms', None)
        
        # 检查数据有效性（注意：可能是 numpy 数组，用 len() 判断）
        if wyckoffs is None or equiv_atoms is None or len(wyckoffs) == 0 or len(equiv_atoms) == 0:
            Logger.warn("Wyckoff data not available in symmetry dataset.")
            input(); return
        
        # 按等价原子分组
        groups = {}
        for idx, (w, eq) in enumerate(zip(wyckoffs, equiv_atoms)):
            if eq not in groups:
                groups[eq] = {'wyckoff': w, 'indices': []}
            groups[eq]['indices'].append(idx)
        
        # 提取代表性坐标（第一个原子）
        structure = ctx.structure
        data = []
        for eq, info in groups.items():
            idx0 = info['indices'][0]
            site = structure[idx0]
            data.append([
                info['wyckoff'],
                len(info['indices']),  # 多重度（等效原子数）
                f"({site.frac_coords[0]:.4f}, {site.frac_coords[1]:.4f}, {site.frac_coords[2]:.4f})"
            ])
        
        print("\n  ========== Wyckoff Positions ==========")
        print(f"  Total independent Wyckoff sites: {len(data)}")
        
        if tabulate is not None:
            print(tabulate(data, headers=["Wyckoff", "Multiplicity", "Representative Fractional Coord"], tablefmt="grid"))
        else:
            # 备用输出
            print("  Wyckoff | Multiplicity | Representative Coord")
            for row in data:
                print(f"  {row[0]:8s} | {row[1]:5d}       | {row[2]}")
        
        input("\n  Press Enter...")

    def _strain_tracking(self, ctx):
        """应变对称性追踪：扫描应变范围，记录空间群变化"""
        if not ctx.has_structure():
            Logger.error("No structure loaded.")
            input(); return
        
        print("\n  ========== Strain Symmetry Tracking ==========")
        print("  Apply uniaxial strain and track space group changes")
        
        direction = get_choice_input("  Direction (a/b/c): ", ['a', 'b', 'c'])
        start = get_float_input("  Start strain (%): ")
        end = get_float_input("  End strain (%): ")
        step = get_float_input("  Step size (%): ")
        
        if step <= 0 or start > end:
            Logger.error("Invalid range.")
            input(); return
        
        from matbuilder.modules.strain.operations import StrainOperations
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
        
        print("\n  Strain (%) | Space Group | System | Atoms")
        print("  ----------------------------------------------")
        
        results = []
        p = start
        while p <= end + 1e-9:
            val = p / 100.0
            F = StrainOperations.get_strain_matrix('uniaxial', direction, val, 'standard')
            strained = ctx.backend.apply_strain(ctx.structure, F)
            
            try:
                analyzer = SpacegroupAnalyzer(strained, symprec=0.01)
                sg = analyzer.get_space_group_symbol()
                sys = analyzer.get_crystal_system()
                print(f"  {p:+6.1f}     | {sg:15s} | {sys:10s} | {len(strained)}")
                results.append((p, sg, sys))
            except Exception:
                print(f"  {p:+6.1f}     | {'Failed':15s} | {'--':10s} | {len(strained)}")
            
            p += step
        
        # 保存结果摘要
        fname = f"symmetry_track_{direction}.txt"
        outpath = os.path.join(ctx.settings.struct_dir, fname)
        with open(outpath, 'w') as f:
            f.write(f"Strain symmetry tracking: {direction}-axis\n")
            f.write("Strain(%)\tSpace Group\tSystem\n")
            for r in results:
                f.write(f"{r[0]:.2f}\t{r[1]}\t{r[2]}\n")
        Logger.info(f"Results saved to: {fname}")
        
        input("\n  Press Enter...")
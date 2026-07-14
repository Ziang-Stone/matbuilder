# -*- coding: utf-8 -*-
"""
Convert Module v0.3
功能：POSCAR ↔ CIF ↔ XYZ ↔ LAMMPS Data ↔ ABACUS STRU ↔ QE PWscf 格式互转
"""

import os
import numpy as np  # ★ 移到文件顶部

from matbuilder.core.base import ModuleBase
from matbuilder.core.pipeline import PipelineExecutor
from matbuilder.utils.logging import Logger
from matbuilder.utils.validators import get_choice_input, get_yes_no_input


class ConvertModule(ModuleBase):
    """格式转换模块"""
    
    name = "convert"
    description = "Format conversion: POSCAR ↔ CIF ↔ XYZ ↔ LAMMPS ↔ ABACUS ↔ QE"
    
    # 支持的格式映射
    FORMATS = {
        'poscar': {'ext': '.vasp', 'desc': 'VASP POSCAR'},
        'cif': {'ext': '.cif', 'desc': 'Crystallographic Information File'},
        'xyz': {'ext': '.xyz', 'desc': 'XYZ Cartesian coordinates'},
        'lammps': {'ext': '.data', 'desc': 'LAMMPS Data file'},
        'abacus': {'ext': '.stru', 'desc': 'ABACUS STRU file'},
        'qe': {'ext': '.pw.in', 'desc': 'Quantum ESPRESSO PWscf input'},
    }
    
    def run(self, context) -> None:
        """编程式入口"""
        pass
    
    def run_interactive(self, context) -> None:
        """交互式入口"""
        self._interactive_menu(context)
    
    def _interactive_menu(self, ctx):
        while True:
            Logger.banner("Format Conversion")
            Logger.info(f"Source: {ctx.structure_path or 'Not loaded'}")
            print("\n  ------------------- Conversion Options ---------------------")
            Logger.menu_item("1", "POSCAR → CIF")
            Logger.menu_item("2", "POSCAR → XYZ")
            Logger.menu_item("3", "POSCAR → LAMMPS Data")
            Logger.menu_item("4", "POSCAR → ABACUS STRU")
            Logger.menu_item("5", "POSCAR → QE PWscf")
            Logger.menu_item("6", "CIF → POSCAR")
            Logger.menu_item("7", "XYZ → POSCAR")
            Logger.menu_item("8", "Batch Convert      (批量转换目录)")
            Logger.menu_item("0", "Back to Main Menu")
            print("-" * 72)
            
            choice = input("\n  Select: ").strip()
            
            if choice == '0':
                break
            elif choice in ['1', '2', '3', '4', '5']:
                fmt_map = {'1': 'cif', '2': 'xyz', '3': 'lammps', '4': 'abacus', '5': 'qe'}
                self._convert(ctx, 'poscar', fmt_map[choice])
            elif choice == '6':
                self._convert_file(ctx, 'cif', 'poscar')
            elif choice == '7':
                self._convert_file(ctx, 'xyz', 'poscar')
            elif choice == '8':
                self._batch_convert(ctx)
            else:
                Logger.error("Invalid option.")
                input("  Press Enter...")
    
    # ==================== 核心转换方法 ====================
    
    def _convert(self, ctx, src_fmt: str, dst_fmt: str):
        """从当前加载的结构转换"""
        if not ctx.has_structure():
            Logger.error("No structure loaded. Please load a structure first.")
            input("  Press Enter...")
            return
        
        base = os.path.splitext(os.path.basename(ctx.structure_path))[0]
        ext = self.FORMATS[dst_fmt]['ext']
        default_name = f"{base}{ext}"
        
        fname = input(f"  Output filename [{default_name}]: ").strip()
        if not fname:
            fname = default_name
        
        outpath = os.path.join(ctx.settings.struct_dir, fname)
        
        try:
            self._write_structure(ctx, ctx.structure, dst_fmt, outpath)
            Logger.success(f"Converted: {ctx.structure_path} → {outpath}")
        except Exception as e:
            Logger.error(f"Conversion failed: {e}")
            import traceback
            traceback.print_exc()
        
        input("\n  Press Enter...")
    
    def _convert_file(self, ctx, src_fmt: str, dst_fmt: str):
        """从文件转换（外部格式导入）"""
        print(f"\n  --- {src_fmt.upper()} → {dst_fmt.upper()} ---")
        
        src_ext = self.FORMATS[src_fmt]['ext']
        import glob
        files = sorted(glob.glob(os.path.join(ctx.settings.struct_dir, f"*{src_ext}")))
        
        if not files:
            Logger.error(f"No {src_ext} files found in '{ctx.settings.struct_dir}/'")
            input("  Press Enter...")
            return
        
        print(f"  Available {src_ext} files:")
        for i, f in enumerate(files, 1):
            print(f"    [{i}]  {os.path.basename(f)}")
        
        choice = input("  Select file (number): ").strip()
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(files):
                raise ValueError
            src_path = files[idx]
        except (ValueError, IndexError):
            Logger.error("Invalid selection.")
            input("  Press Enter...")
            return
        
        try:
            structure = self._read_structure(src_path, src_fmt)
        except Exception as e:
            Logger.error(f"Failed to load {src_path}: {e}")
            input("  Press Enter...")
            return
        
        base = os.path.splitext(os.path.basename(src_path))[0]
        dst_ext = self.FORMATS[dst_fmt]['ext']
        default_name = f"{base}{dst_ext}"
        
        fname = input(f"  Output filename [{default_name}]: ").strip()
        if not fname:
            fname = default_name
        
        outpath = os.path.join(ctx.settings.struct_dir, fname)
        
        try:
            self._write_structure(ctx, structure, dst_fmt, outpath)
            Logger.success(f"Converted: {src_path} → {outpath}")
        except Exception as e:
            Logger.error(f"Conversion failed: {e}")
            import traceback
            traceback.print_exc()
        
        input("\n  Press Enter...")
    
    def _batch_convert(self, ctx):
        """批量转换目录中的所有文件"""
        print("\n  --- Batch Convert ---")
        
        src_fmt = get_choice_input(
            "  Source format (poscar/cif/xyz): ",
            ['poscar', 'cif', 'xyz']
        )
        dst_fmt = get_choice_input(
            "  Target format (cif/xyz/lammps/abacus/qe/poscar): ",
            ['cif', 'xyz', 'lammps', 'abacus', 'qe', 'poscar']
        )
        
        src_ext = self.FORMATS[src_fmt]['ext']
        dst_ext = self.FORMATS[dst_fmt]['ext']
        
        import glob
        files = sorted(glob.glob(os.path.join(ctx.settings.struct_dir, f"*{src_ext}")))
        
        if not files:
            Logger.error(f"No {src_ext} files found.")
            input("  Press Enter...")
            return
        
        Logger.info(f"Found {len(files)} {src_ext} file(s)")
        confirm = get_yes_no_input("  Proceed?", default=True)
        if not confirm:
            return
        
        success = 0
        failed = 0
        
        for src_path in files:
            base = os.path.splitext(os.path.basename(src_path))[0]
            dst_name = f"{base}{dst_ext}"
            dst_path = os.path.join(ctx.settings.struct_dir, dst_name)
            
            try:
                structure = self._read_structure(src_path, src_fmt)
                self._write_structure(ctx, structure, dst_fmt, dst_path)
                print(f"  ✓ {os.path.basename(src_path)} → {dst_name}")
                success += 1
            except Exception as e:
                print(f"  ✗ {os.path.basename(src_path)}: {e}")
                failed += 1
        
        Logger.success(f"Done! {success} succeeded, {failed} failed.")
        input("\n  Press Enter...")
    
    # ==================== 底层读写方法 ====================
    
    def _read_structure(self, filepath: str, fmt: str):
        """读取各种格式的结构文件"""
        if fmt == 'poscar':
            from pymatgen.io.vasp import Poscar
            return Poscar.from_file(filepath).structure
        
        elif fmt == 'cif':
            from pymatgen.io.cif import CifParser
            parser = CifParser(filepath)
            structures = parser.get_structures()
            if not structures:
                raise ValueError("No structures found in CIF file")
            return structures[0]
        
        elif fmt == 'xyz':
            try:
                from ase.io import read as ase_read
                from pymatgen.io.ase import AseAtomsAdaptor
                atoms = ase_read(filepath)
                return AseAtomsAdaptor.get_structure(atoms)
            except ImportError:
                from pymatgen.io.xyz import XYZ
                xyz = XYZ.from_file(filepath)
                if xyz.all_molecules:
                    from pymatgen.core import Structure, Lattice
                    mol = xyz.all_molecules[0]
                    coords = mol.cart_coords
                    max_range = coords.max(axis=0) - coords.min(axis=0)
                    lattice = Lattice.from_parameters(
                        a=max(max_range[0], 10),
                        b=max(max_range[1], 10),
                        c=max(max_range[2], 10),
                        alpha=90, beta=90, gamma=90
                    )
                    return Structure(
                        lattice=lattice,
                        species=[str(s.specie) for s in mol],
                        coords=mol.cart_coords,
                        coords_are_cartesian=True
                    )
                else:
                    raise ValueError("No molecules found in XYZ file")
        
        else:
            raise ValueError(f"Unsupported source format: {fmt}")
    
    def _write_structure(self, ctx, structure, fmt: str, filepath: str):
        """写入各种格式的结构文件"""
        if fmt == 'poscar':
            from pymatgen.io.vasp import Poscar
            p = Poscar(structure)
            p.write_file(filepath)
        
        elif fmt == 'cif':
            from pymatgen.io.cif import CifWriter
            writer = CifWriter(structure, symprec=0.01)
            writer.write_file(filepath)
        
        elif fmt == 'xyz':
            try:
                from ase.io import write as ase_write
                from pymatgen.io.ase import AseAtomsAdaptor
                atoms = AseAtomsAdaptor.get_atoms(structure)
                ase_write(filepath, atoms, format='xyz')
            except ImportError:
                self._write_simple_xyz(structure, filepath)
        
        elif fmt == 'lammps':
            self._write_lammps_data(structure, filepath)
        
        elif fmt == 'abacus':
            self._write_abacus_stru(structure, filepath)
        
        elif fmt == 'qe':
            self._write_qe_pwscf(structure, filepath)
        
        else:
            raise ValueError(f"Unsupported target format: {fmt}")
    
    def _write_simple_xyz(self, structure, filepath: str):
        """备用：简单 XYZ 格式"""
        with open(filepath, 'w') as f:
            f.write(f"{len(structure)}\n")
            f.write(f"Generated by MatBuilder\n")
            for site in structure:
                f.write(f"{str(site.specie):3s}  {site.x:12.6f}  {site.y:12.6f}  {site.z:12.6f}\n")
    
    # ==================== LAMMPS Data ====================
    
    def _write_lammps_data(self, structure, filepath: str):
        """写入 LAMMPS Data 文件（atomic 风格）"""
        lat = structure.lattice
        
        # 三斜盒子参数
        xlo, ylo, zlo = 0.0, 0.0, 0.0
        xhi = lat.a
        yhi = lat.b
        zhi = lat.c
        
        xy = lat.b * np.cos(np.radians(lat.gamma))
        xz = lat.c * np.cos(np.radians(lat.beta))
        yz = lat.c * (np.cos(np.radians(lat.alpha)) - 
                       np.cos(np.radians(lat.beta)) * np.cos(np.radians(lat.gamma))) / \
             max(np.sin(np.radians(lat.gamma)), 1e-10)
        
        # 元素类型映射
        species_list = sorted(set([str(site.specie) for site in structure]))
        type_map = {s: i+1 for i, s in enumerate(species_list)}
        
        with open(filepath, 'w') as f:
            f.write(f"LAMMPS data file generated by MatBuilder\n\n")
            f.write(f"{len(structure)} atoms\n")
            f.write(f"{len(species_list)} atom types\n\n")
            
            # 盒子边界
            if abs(xy) < 1e-10 and abs(xz) < 1e-10 and abs(yz) < 1e-10:
                f.write(f"{xlo:.6f} {xhi:.6f} xlo xhi\n")
                f.write(f"{ylo:.6f} {yhi:.6f} ylo yhi\n")
                f.write(f"{zlo:.6f} {zhi:.6f} zlo zhi\n")
            else:
                f.write(f"{xlo:.6f} {xhi:.6f} xlo xhi\n")
                f.write(f"{ylo:.6f} {yhi:.6f} ylo yhi\n")
                f.write(f"{zlo:.6f} {zhi:.6f} zlo zhi\n")
                f.write(f"{xy:.6f} {xz:.6f} {yz:.6f} xy xz yz\n")
            
            f.write(f"\nMasses\n\n")
            
            for species, type_id in type_map.items():
                from pymatgen.core import Element
                elem = Element(species)
                mass = float(elem.atomic_mass)
                f.write(f"{type_id} {mass:.4f}  # {species}\n")
            
            f.write(f"\nAtoms\n\n")
            
            for i, site in enumerate(structure, 1):
                type_id = type_map[str(site.specie)]
                f.write(f"{i} {type_id} {site.x:.6f} {site.y:.6f} {site.z:.6f}\n")
    
    # ==================== ABACUS STRU ====================
    
    def _write_abacus_stru(self, structure, filepath: str):
        """
        写入 ABACUS STRU 文件
        ABACUS 使用原子轨道基组，STRU 文件包含晶格、元素、坐标等信息
        """
        lat = structure.lattice
        
        # 按元素分组
        from collections import defaultdict
        elem_sites = defaultdict(list)
        for i, site in enumerate(structure):
            elem_sites[str(site.specie)].append((i, site))
        
        with open(filepath, 'w') as f:
            f.write("ATOMIC_SPECIES\n")
            for elem in sorted(elem_sites.keys()):
                from pymatgen.core import Element
                mass = float(Element(elem).atomic_mass)
                # 使用通用赝势文件名（用户需自行替换）
                f.write(f"{elem} {mass:.4f} {elem}_ONCV_PBE-1.0.upf\n")
            
            f.write("\nLATTICE_CONSTANT\n")
            f.write(f"{1.889726133}  # 1 Bohr = 1.889726133 Angstrom, ABACUS 内部用 Bohr\n")
            
            f.write("\nLATTICE_VECTORS\n")
            for i in range(3):
                f.write(f"  {lat.matrix[i, 0]:.10f}  {lat.matrix[i, 1]:.10f}  {lat.matrix[i, 2]:.10f}\n")
            
            f.write("\nATOMIC_POSITIONS\n")
            f.write("Direct  # 或 Cartesian，这里用分数坐标\n\n")
            
            for elem in sorted(elem_sites.keys()):
                sites = elem_sites[elem]
                f.write(f"{elem}  # 元素名\n")
                f.write(f"{len(sites)}  # 原子数\n")
                f.write("0.0  # 磁矩（可修改）\n")
                for idx, site in sites:
                    f.write(f"  {site.frac_coords[0]:.10f}  {site.frac_coords[1]:.10f}  {site.frac_coords[2]:.10f}  1  1  1  # 分数坐标 + 三个方向的可动标志\n")
                f.write("\n")
    
    # ==================== Quantum ESPRESSO PWscf ====================
    
    def _write_qe_pwscf(self, structure, filepath: str):
        """
        写入 Quantum ESPRESSO PWscf 输入文件（仅结构部分）
        用户需自行补充 &CONTROL, &SYSTEM, &ELECTRONS 等 namelist
        """
        lat = structure.lattice
        
        # 计算 celldm(1-6) —— QE 使用 alat 和 cosines
        a_angstrom = lat.a
        alat = a_angstrom / 0.529177  # 转换为 Bohr
        
        # 传统晶体学单元格参数
        a, b, c = lat.a, lat.b, lat.c
        cosa = np.cos(np.radians(lat.alpha))
        cosb = np.cos(np.radians(lat.beta))
        cosg = np.cos(np.radians(lat.gamma))
        
        # 判断是否为立方/四方/正交等简单晶系
        is_simple = (abs(lat.alpha - 90) < 1e-3 and 
                     abs(lat.beta - 90) < 1e-3 and 
                     abs(lat.gamma - 90) < 1e-3)
        
        with open(filepath, 'w') as f:
            f.write("&SYSTEM\n")
            f.write(f"  ibrav = 0,  # 一般晶胞（用户可根据实际对称性修改）\n")
            f.write(f"  nat = {len(structure)},\n")
            f.write(f"  ntyp = {len(set([str(s.specie) for s in structure]))},\n")
            f.write(f"  ecutwfc = 50.0,  # 请根据实际体系修改\n")
            f.write(f"  ecutrho = 400.0,\n")
            f.write(f"/\n\n")
            
            f.write("CELL_PARAMETERS angstrom\n")
            for i in range(3):
                f.write(f"  {lat.matrix[i, 0]:.10f}  {lat.matrix[i, 1]:.10f}  {lat.matrix[i, 2]:.10f}\n")
            
            f.write("\nATOMIC_SPECIES\n")
            species_seen = set()
            for site in structure:
                elem = str(site.specie)
                if elem not in species_seen:
                    species_seen.add(elem)
                    from pymatgen.core import Element
                    mass = float(Element(elem).atomic_mass)
                    f.write(f"  {elem}  {mass:.4f}  {elem}.pbe-n-kjpaw_psl.1.0.0.UPF  # 请替换为实际赝势文件\n")
            
            f.write("\nATOMIC_POSITIONS crystal\n")
            for site in structure:
                f.write(f"  {str(site.specie):4s}  {site.frac_coords[0]:.10f}  {site.frac_coords[1]:.10f}  {site.frac_coords[2]:.10f}\n")
            
            f.write("\nK_POINTS automatic\n")
            f.write("  6 6 6 0 0 0  # 请根据实际体系修改 K 点网格\n")
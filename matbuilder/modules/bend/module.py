# -*- coding: utf-8 -*-
"""
Bend Module v0.4
功能：二维材料弯曲、纳米管卷曲、喇叭结构（MoS₂ 等）
"""

import os
import numpy as np

from matbuilder.core.base import ModuleBase
from matbuilder.utils.logging import Logger
from matbuilder.utils.validators import (
    get_float_input, get_int_input, get_choice_input, get_yes_no_input
)


class BendModule(ModuleBase):
    """二维材料弯曲建模模块"""
    
    name = "bend"
    description = "2D bending, nanotube rolling, horn structure"
    
    def run(self, context) -> None:
        """编程式入口"""
        pass
    
    def run_interactive(self, context) -> None:
        """交互式入口"""
        self._interactive_menu(context)
    
    def _interactive_menu(self, ctx):
        while True:
            Logger.banner("Bend / Roll / Horn")
            Logger.info(f"Source: {ctx.structure_path or 'Not loaded'}")
            print("\n  ------------------- Bend Options ---------------------")
            Logger.menu_item("1", "Cylindrical Bending    (圆柱弯曲 — 沿轴卷曲)")
            Logger.menu_item("2", "Spherical Bending      (球面弯曲 — 穹顶结构)")
            Logger.menu_item("3", "Nanotube Rolling       (纳米管卷曲)")
            Logger.menu_item("4", "Horn Structure         (喇叭结构 — 锥形管)")
            Logger.menu_item("5", "Ripple / Corrugation   (波纹/褶皱结构)")
            Logger.menu_item("0", "Back to Main Menu")
            print("-" * 72)
            
            choice = input("\n  Select: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self._cylindrical_bending(ctx)
            elif choice == '2':
                self._spherical_bending(ctx)
            elif choice == '3':
                self._nanotube_rolling(ctx)
            elif choice == '4':
                self._horn_structure(ctx)
            elif choice == '5':
                self._ripple_structure(ctx)
            else:
                Logger.error("Invalid option.")
                input("  Press Enter...")
    
    # ==================== 圆柱弯曲 ====================
    
    def _cylindrical_bending(self, ctx):
        """
        圆柱弯曲：将二维材料沿某一轴卷曲成圆柱面
        理论：沿卷曲方向坐标不变，垂直方向映射到圆弧
        """
        print("\n  --- Cylindrical Bending ---")
        print("  Bend a 2D sheet into a cylindrical surface")
        
        # 选择卷曲轴
        axis = get_choice_input("  Axis to bend around (x/y/z): ", ['x', 'y', 'z'])
        
        # 卷曲半径
        radius = get_float_input("  Bend radius (Å): ")
        if radius <= 0:
            Logger.error("Radius must be positive.")
            input()
            return
        
        # 选择沿卷曲轴的晶轴
        axis_map = {'x': 0, 'y': 1, 'z': 2}
        axis_idx = axis_map[axis]
        
        # 垂直方向的两个晶轴
        perp_axes = [i for i in range(3) if i != axis_idx]
        
        structure = ctx.structure.copy()
        lat = structure.lattice.matrix.copy()
        
        # 获取垂直于卷曲轴的晶格长度
        L_perp = np.linalg.norm(lat[perp_axes[0]])
        
        # 计算卷曲角度
        circumference = 2 * np.pi * radius
        theta_max = L_perp / radius  # 弧度
        
        print(f"  Lattice length along bend direction: {L_perp:.4f} Å")
        print(f"  Circumference for r={radius}Å: {circumference:.4f} Å")
        print(f"  Bend angle: {np.degrees(theta_max):.2f}°")
        
        # 执行弯曲变换
        new_structure = self._apply_cylindrical_bend(structure, axis_idx, radius, theta_max)
        
        fname = self._generate_filename(ctx, "cylbend", f"{axis}{int(radius)}")
        self._write_and_report(ctx, new_structure, fname)
        input("\n  Press Enter...")
    
    def _apply_cylindrical_bend(self, structure, axis_idx, radius, theta_max):
        """
        应用圆柱弯曲变换
        axis_idx: 卷曲轴 (0=x, 1=y, 2=z)
        垂直方向坐标映射到圆柱面
        """
        new_structure = structure.copy()
        axis_idx = int(axis_idx)
        
        # 垂直方向的两个坐标索引
        perp_indices = [i for i in range(3) if i != axis_idx]
        
        for site in new_structure:
            frac = site.frac_coords.copy()
            cart = site.coords.copy()
            
            # 沿卷曲轴坐标不变
            # 垂直方向第一个坐标映射到角度
            u = frac[perp_indices[0]]  # 0 到 1
            
            # 映射到角度
            theta = u * theta_max
            
            # 新的笛卡尔坐标
            new_cart = cart.copy()
            
            # 垂直方向第一个坐标变为圆弧的切向位置
            new_cart[perp_indices[0]] = radius * np.sin(theta)
            # 垂直方向第二个坐标变为径向位置（相对于圆柱中心）
            new_cart[perp_indices[1]] = radius * (1 - np.cos(theta))
            
            site.coords = new_cart
        
        # 更新晶格：卷曲后晶格变为圆柱坐标系
        # 实际计算中保持原晶格，但原子位置已弯曲
        return new_structure
    
    # ==================== 球面弯曲 ====================
    
    def _spherical_bending(self, ctx):
        """
        球面弯曲：将二维材料映射到球冠（穹顶结构）
        理论：平面极坐标映射到球面坐标
        """
        print("\n  --- Spherical Bending (Dome) ---")
        print("  Bend a 2D sheet into a spherical cap")
        
        radius = get_float_input("  Sphere radius (Å): ")
        if radius <= 0:
            Logger.error("Radius must be positive.")
            input()
            return
        
        # 最大极角
        theta_max_deg = get_float_input("  Max polar angle (degrees, <180): ")
        theta_max = np.radians(theta_max_deg)
        
        structure = ctx.structure.copy()
        
        # 应用球面弯曲
        new_structure = self._apply_spherical_bend(structure, radius, theta_max)
        
        fname = self._generate_filename(ctx, "dome", f"R{int(radius)}A{int(theta_max_deg)}")
        self._write_and_report(ctx, new_structure, fname)
        input("\n  Press Enter...")
    
    def _apply_spherical_bend(self, structure, radius, theta_max):
        """应用球面弯曲变换"""
        new_structure = structure.copy()
        
        # 找到二维平面（假设 c 方向最薄）
        # 将 a-b 平面映射到球面
        for site in new_structure:
            frac = site.frac_coords.copy()
            
            # 平面极坐标
            r_frac = np.sqrt(frac[0]**2 + frac[1]**2)
            phi = np.arctan2(frac[1], frac[0])  # 方位角
            
            # 映射到球面坐标
            theta = r_frac * theta_max  # 极角
            
            # 球面笛卡尔坐标
            x = radius * np.sin(theta) * np.cos(phi)
            y = radius * np.sin(theta) * np.sin(phi)
            z = radius * (1 - np.cos(theta))  # 穹顶向上凸起
            
            site.coords = np.array([x, y, z])
        
        return new_structure
    
    # ==================== 纳米管卷曲 ====================
    
    def _nanotube_rolling(self, ctx):
        """
        纳米管卷曲：将二维材料沿特定手性矢量卷曲成纳米管
        理论：基于石墨烯/过渡金属硫化物的 (n,m) 手性矢量
        """
        print("\n  --- Nanotube Rolling ---")
        print("  Roll a 2D sheet into a nanotube")
        print("  Chirality vector: C_h = n*a1 + m*a2")
        
        # 手性指数
        n = get_int_input("  Chirality index n: ")
        m = get_int_input("  Chirality index m: ")
        
        if n < 0 or m < 0:
            Logger.error("Chirality indices must be non-negative.")
            input()
            return
        
        structure = ctx.structure.copy()
        lat = structure.lattice.matrix.copy()
        
        # 计算手性矢量
        # 对于六角晶格（如石墨烯），a1 和 a2 是基矢
        # 这里简化为正交晶格处理
        a1 = lat[0]  # 第一基矢
        a2 = lat[1]  # 第二基矢
        
        Ch = n * a1 + m * a2  # 手性矢量
        Ch_length = np.linalg.norm(Ch)
        
        # 纳米管周长 = |Ch|
        radius = Ch_length / (2 * np.pi)
        
        print(f"  Chiral vector: ({n}, {m})")
        print(f"  Ch vector length: {Ch_length:.4f} Å")
        print(f"  Nanotube radius: {radius:.4f} Å")
        print(f"  Diameter: {2*radius:.4f} Å")
        
        # 应用纳米管卷曲
        new_structure = self._apply_nanotube_roll(structure, a1, a2, n, m, radius)
        
        fname = self._generate_filename(ctx, "nanotube", f"{n}{m}R{int(radius)}")
        self._write_and_report(ctx, new_structure, fname)
        input("\n  Press Enter...")
    
    def _apply_nanotube_roll(self, structure, a1, a2, n, m, radius):
        """应用纳米管卷曲变换"""
        new_structure = structure.copy()
        
        # 手性矢量方向
        Ch = n * a1 + m * a2
        Ch_norm = Ch / np.linalg.norm(Ch)
        
        # 垂直于 Ch 的方向（管轴方向）
        T = np.cross(Ch, a1 + a2)
        if np.linalg.norm(T) < 1e-10:
            T = np.cross(Ch, a1)
        T_norm = T / np.linalg.norm(T)
        
        for site in new_structure:
            cart = site.coords.copy()
            
            # 投影到手性矢量方向
            u = np.dot(cart, Ch_norm)
            # 投影到管轴方向
            v = np.dot(cart, T_norm)
            
            # 映射到圆柱坐标
            theta = u / radius  # 角度
            
            # 新坐标
            new_cart = v * T_norm  # 沿管轴
            new_cart += radius * np.cos(theta) * Ch_norm  # 径向
            new_cart += radius * np.sin(theta) * np.cross(T_norm, Ch_norm)  # 切向
            
            site.coords = new_cart
        
        return new_structure
    
    # ==================== 喇叭结构 ====================
    
    def _horn_structure(self, ctx):
        """
        喇叭结构：锥形纳米管，半径沿轴向变化
        理论：半径随轴向位置线性或指数变化
        """
        print("\n  --- Horn Structure (Conical Tube) ---")
        print("  Create a conical nanotube with varying radius")
        
        r1 = get_float_input("  Radius at bottom (Å): ")
        r2 = get_float_input("  Radius at top (Å): ")
        length = get_float_input("  Tube length (Å): ")
        
        if r1 <= 0 or r2 <= 0 or length <= 0:
            Logger.error("All dimensions must be positive.")
            input()
            return
        
        # 锥度类型
        taper = get_choice_input("  Taper type (linear/exponential): ", ['linear', 'exponential'])
        
        structure = ctx.structure.copy()
        
        # 应用喇叭变换
        new_structure = self._apply_horn(structure, r1, r2, length, taper)
        
        taper_str = "lin" if taper == 'linear' else "exp"
        fname = self._generate_filename(ctx, "horn", f"{taper_str}R{int(r1)}-{int(r2)}L{int(length)}")
        self._write_and_report(ctx, new_structure, fname)
        input("\n  Press Enter...")
    
    def _apply_horn(self, structure, r1, r2, length, taper):
        """应用喇叭结构变换"""
        new_structure = structure.copy()
        
        # 找到轴向（假设为 c 方向）
        # 将 z 坐标映射到半径变化
        
        for site in new_structure:
            cart = site.coords.copy()
            
            # 归一化轴向位置
            z_norm = cart[2] / length  # 0 到 1
            
            # 当前半径
            if taper == 'linear':
                r = r1 + (r2 - r1) * z_norm
            else:  # exponential
                r = r1 * (r2 / r1) ** z_norm
            
            # 将 x, y 映射到当前半径的圆
            xy_length = np.sqrt(cart[0]**2 + cart[1]**2)
            if xy_length > 1e-10:
                scale = r / xy_length
                cart[0] *= scale
                cart[1] *= scale
            
            site.coords = cart
        
        # 更新晶格 c 方向
        lat = new_structure.lattice.matrix.copy()
        lat[2, 2] = length
        from pymatgen.core import Lattice
        new_structure.lattice = Lattice(lat)
        
        return new_structure
    
    # ==================== 波纹/褶皱结构 ====================
    
    def _ripple_structure(self, ctx):
        """
        波纹/褶皱结构：在二维材料中引入周期性起伏
        理论：正弦/余弦函数调制 z 方向坐标
        """
        print("\n  --- Ripple / Corrugation Structure ---")
        print("  Create periodic ripples in a 2D sheet")
        
        # 波纹方向
        ripple_dir = get_choice_input("  Ripple direction (x/y): ", ['x', 'y'])
        dir_idx = 0 if ripple_dir == 'x' else 1
        
        # 波纹参数
        amplitude = get_float_input("  Ripple amplitude (Å): ")
        wavelength = get_float_input("  Wavelength (Å): ")
        n_ripples = get_int_input("  Number of ripples: ")
        
        if amplitude <= 0 or wavelength <= 0 or n_ripples <= 0:
            Logger.error("Parameters must be positive.")
            input()
            return
        
        structure = ctx.structure.copy()
        
        # 应用波纹
        new_structure = self._apply_ripple(structure, dir_idx, amplitude, wavelength, n_ripples)
        
        fname = self._generate_filename(ctx, "ripple", f"{ripple_dir}A{int(amplitude)}W{int(wavelength)}")
        self._write_and_report(ctx, new_structure, fname)
        input("\n  Press Enter...")
    
    def _apply_ripple(self, structure, dir_idx, amplitude, wavelength, n_ripples):
        """应用波纹变换"""
        new_structure = structure.copy()
        
        k = 2 * np.pi / wavelength  # 波数
        
        for site in new_structure:
            cart = site.coords.copy()
            frac = site.frac_coords.copy()
            
            # 沿波纹方向的位置
            pos = cart[dir_idx]
            
            # 正弦调制 z 坐标
            cart[2] += amplitude * np.sin(k * pos * n_ripples)
            
            site.coords = cart
        
        # 扩展晶格 z 方向以容纳波纹
        lat = new_structure.lattice.matrix.copy()
        z_range = max(site.z for site in new_structure) - min(site.z for site in new_structure)
        lat[2, 2] = max(lat[2, 2], z_range + 5.0)  # 加 5Å 缓冲
        from pymatgen.core import Lattice
        new_structure.lattice = Lattice(lat)
        
        return new_structure
    
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
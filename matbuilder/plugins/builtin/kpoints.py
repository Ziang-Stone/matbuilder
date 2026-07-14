# -*- coding: utf-8 -*-
"""
内置插件：自动生成 VASP KPOINTS
"""
import os

from matbuilder.plugins.base import PluginBase
from matbuilder.core.hooks import HookPoint, HookContext
from matbuilder.utils.logging import Logger


class KPointsPlugin(PluginBase):
    name = "kpoints_generator"
    version = "0.1.0"
    description = "Auto-generate KPOINTS file based on structure"
    author = "MatBuilder Team"

    def on_after_convert(self, ctx: HookContext) -> HookContext:
        """在格式转换后自动生成 KPOINTS（如果目标是 VASP）"""
        # 判断是否为 POSCAR 输出
        params = ctx.params or {}
        fmt = params.get("format", "")
        if fmt != "poscar" and fmt != "vasp":
            return ctx
        
        # 检查是否生成了 vasp 文件
        output_path = params.get("output")
        if not output_path or not output_path.endswith(".vasp"):
            return ctx
        
        # 生成 KPOINTS
        kpoints_path = output_path.replace(".vasp", ".kpoints")
        if os.path.exists(kpoints_path):
            return ctx
        
        try:
            from pymatgen.io.vasp import Kpoints
            # 根据结构自动生成 Monkhorst-Pack 网格
            structure = ctx.structure
            if structure is None:
                return ctx
            
            # 基于晶格参数确定网格密度（简易：每轴约 0.04 Å⁻¹ 倒空间分辨率）
            lat = structure.lattice
            kpts = Kpoints.automatic_density(structure, 0.04)
            kpts.write_file(kpoints_path)
            Logger.info(f"  [Plugin] Generated KPOINTS: {kpoints_path}")
        except Exception as e:
            Logger.warn(f"  [Plugin] Failed to generate KPOINTS: {e}")
        
        return ctx
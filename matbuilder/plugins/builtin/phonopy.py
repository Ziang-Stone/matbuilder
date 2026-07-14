# -*- coding: utf-8 -*-
"""
内置插件：Phonopy 超胞生成（声子计算准备）
"""
import os
import numpy as np

from matbuilder.plugins.base import PluginBase
from matbuilder.core.hooks import HookContext
from matbuilder.utils.logging import Logger


class PhonopyPlugin(PluginBase):
    name = "phonopy_interface"
    version = "0.1.0"
    description = "Generate supercells for phonon calculations (Phonopy)"
    author = "MatBuilder Team"

    def on_after_transform(self, ctx: HookContext) -> HookContext:
        """在超胞变换后自动生成 Phonopy 所需的 POSCAR-* 文件"""
        params = ctx.params or {}
        operation = params.get("operation")
        
        # 仅在超胞操作后触发
        if operation != "supercell":
            return ctx
        
        structure = ctx.result
        if structure is None:
            return ctx
        
        # 获取超胞尺寸
        factors = params.get("factors", [2, 2, 2])
        if not factors or factors == [1, 1, 1]:
            return ctx
        
        # 生成位移结构（简谐近似：沿每个原子正负方向微移）
        output_dir = ctx.context.settings.struct_dir if ctx.context else "."
        
        # 写入一个超胞的 POSCAR
        base_name = params.get("output", "phonopy")
        if not base_name.endswith(".vasp"):
            base_name += ".vasp"
        outpath = os.path.join(output_dir, base_name)
        ctx.context.backend.write_structure(structure, outpath)
        Logger.info(f"  [Plugin] Phonopy supercell saved: {outpath}")
        
        # 尝试调用 phonopy 生成位移（如果安装）
        try:
            import phonopy
            from phonopy import Phonopy
            from phonopy.structure.atoms import PhonopyAtoms
            
            # 转换结构
            p_atoms = PhonopyAtoms(
                symbols=[str(s.specie) for s in structure],
                cell=structure.lattice.matrix,
                positions=structure.frac_coords
            )
            
            # 创建 Phonopy 对象并生成位移
            ph = Phonopy(p_atoms, [[1,0,0],[0,1,0],[0,0,1]])
            ph.generate_displacements(distance=0.01)
            ph.save("phonopy_disp.yaml")
            Logger.info(f"  [Plugin] Generated phonopy displacements in ./phonopy_disp.yaml")
        except ImportError:
            Logger.info("  [Plugin] phonopy not installed. Skipping displacement generation.")
        except Exception as e:
            Logger.warn(f"  [Plugin] Phonopy error: {e}")
        
        return ctx
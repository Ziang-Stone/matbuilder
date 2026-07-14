# -*- coding: utf-8 -*-
"""
内置插件：POTCAR 推荐与生成
"""
import os
from collections import Counter

from matbuilder.plugins.base import PluginBase
from matbuilder.core.hooks import HookContext
from matbuilder.utils.logging import Logger


class POTCARPlugin(PluginBase):
    name = "potcar_suggester"
    version = "0.1.0"
    description = "Suggest POTCAR settings for VASP calculations"
    author = "MatBuilder Team"

    def on_after_load(self, ctx: HookContext) -> HookContext:
        """加载结构后，输出 POTCAR 推荐信息"""
        structure = ctx.structure
        if structure is None:
            return ctx
        
        # 统计元素
        species = [str(site.specie) for site in structure]
        counts = Counter(species)
        
        Logger.info(f"  [Plugin] POTCAR suggestion for {', '.join(counts.keys())}:")
        for elem, num in counts.items():
            # 简易推荐：根据元素推荐标准赝势
            recommended_pp = {
                "H": "H", "He": "He",
                "Li": "Li_sv", "Be": "Be", "B": "B", "C": "C", "N": "N", "O": "O",
                "F": "F", "Ne": "Ne", "Na": "Na_pv", "Mg": "Mg", "Al": "Al",
                "Si": "Si", "P": "P", "S": "S", "Cl": "Cl", "Ar": "Ar",
                "K": "K_sv", "Ca": "Ca_sv", "Sc": "Sc_sv", "Ti": "Ti_sv",
                "V": "V_sv", "Cr": "Cr_pv", "Mn": "Mn_pv", "Fe": "Fe",
                "Co": "Co", "Ni": "Ni", "Cu": "Cu", "Zn": "Zn",
                "Ga": "Ga_d", "Ge": "Ge_d", "As": "As", "Se": "Se",
                "Br": "Br", "Kr": "Kr",
                "Rb": "Rb_sv", "Sr": "Sr_sv", "Y": "Y_sv", "Zr": "Zr_sv",
                "Nb": "Nb_sv", "Mo": "Mo_sv", "Tc": "Tc", "Ru": "Ru_pv",
                "Rh": "Rh_pv", "Pd": "Pd", "Ag": "Ag", "Cd": "Cd",
                "In": "In_d", "Sn": "Sn_d", "Sb": "Sb", "Te": "Te",
                "I": "I", "Xe": "Xe",
                "Cs": "Cs_sv", "Ba": "Ba_sv", "La": "La", "Ce": "Ce",
                "Pr": "Pr_3", "Nd": "Nd_3", "Pm": "Pm_3", "Sm": "Sm_3",
                "Eu": "Eu", "Gd": "Gd_3", "Tb": "Tb_3", "Dy": "Dy_3",
                "Ho": "Ho_3", "Er": "Er_3", "Tm": "Tm_3", "Yb": "Yb_2",
                "Lu": "Lu_3", "Hf": "Hf_pv", "Ta": "Ta_pv", "W": "W_sv",
                "Re": "Re", "Os": "Os", "Ir": "Ir", "Pt": "Pt",
                "Au": "Au", "Hg": "Hg", "Tl": "Tl_d", "Pb": "Pb_d",
                "Bi": "Bi_d", "Po": "Po_d", "At": "At", "Rn": "Rn"
            }
            pp = recommended_pp.get(elem, f"{elem}")
            Logger.info(f"    {elem} ({num} atoms) → {pp} (PBE, standard)")
        
        Logger.info("  [Plugin] Note: Check VASP POTCAR library for exact files.")
        return ctx
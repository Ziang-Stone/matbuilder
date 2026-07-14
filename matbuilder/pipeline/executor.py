# -*- coding: utf-8 -*-
"""
流水线执行引擎
"""

import os
from typing import Dict, Any

from matbuilder.core.context import Context
from matbuilder.core.registry import ModuleRegistry
from matbuilder.backends.factory import BackendFactory
from matbuilder.config.settings import Settings
from matbuilder.utils.logging import Logger

from .workflow import Workflow, WorkflowStep, StepType


class PipelineExecutor:
    """YAML 配置工作流执行器"""
    
    def __init__(self, context: Context = None):
        self.settings = Settings()
        self.context = context or Context(settings=self.settings)
        self.context.backend = BackendFactory.create(self.settings.backend)
        self.results: Dict[str, Any] = {}  # 步骤结果缓存
        self.structures: Dict[str, Any] = {}  # 结构缓存（支持多结构）
    
    def execute(self, workflow: Workflow):
        """执行完整工作流"""
        Logger.banner(f"Pipeline: {workflow.name}")
        if workflow.description:
            Logger.info(workflow.description)
        
        print(f"\n  Total steps: {len(workflow.steps)}")
        print("-" * 72)
        
        for i, step in enumerate(workflow.steps, 1):
            print(f"\n  >>> Step {i}/{len(workflow.steps)}: {step.name}")
            print(f"      Type: {step.step_type.value}")
            
            # 检查条件
            if step.condition and not self._check_condition(step.condition):
                Logger.warn(f"  Condition '{step.condition}' not met, skipping.")
                continue
            
            try:
                result = self._execute_step(step)
                self.results[step.name] = result
                if step.output_name:
                    self.structures[step.output_name] = result
                Logger.success(f"  Completed: {step.name}")
            except Exception as e:
                Logger.error(f"  Failed: {step.name}")
                Logger.error(f"  Error: {e}")
                import traceback
                traceback.print_exc()
                # 根据配置决定是否继续
                if not self.settings.get("pipeline_continue_on_error", False):
                    Logger.error("  Pipeline aborted.")
                    break
        
        Logger.banner("Pipeline Complete")
        Logger.info(f"  Success: {len([r for r in self.results.values() if r is not None])}/{len(workflow.steps)}")
    
    def _check_condition(self, condition: str) -> bool:
        """检查执行条件"""
        # 简单条件解析
        if condition == "prev.success":
            return len(self.results) > 0 and list(self.results.values())[-1] is not None
        if condition.startswith("has."):
            key = condition.split(".")[1]
            return key in self.structures
        return True
    
    def _execute_step(self, step: WorkflowStep):
        """执行单个步骤"""
        method_map = {
            StepType.LOAD: self._exec_load,
            StepType.STRAIN: self._exec_strain,
            StepType.TRANSFORM: self._exec_transform,
            StepType.CONVERT: self._exec_convert,
            StepType.BEND: self._exec_bend,
            StepType.CUSTOM: self._exec_custom,
        }
        
        handler = method_map.get(step.step_type)
        if not handler:
            raise ValueError(f"Unknown step type: {step.step_type}")
        
        return handler(step.params)
    
    def _exec_load(self, params: dict):
        """加载结构"""
        filepath = params.get("file", self.settings.input_path)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        structure, metadata = self.context.backend.load_structure(filepath)
        self.context.set_structure(structure, filepath, metadata)
        return structure
    
    def _exec_strain(self, params: dict):
        """执行应变"""
        from matbuilder.modules.strain.operations import StrainOperations
        
        if not self.context.has_structure():
            raise RuntimeError("No structure loaded. Add a 'load' step first.")
        
        strain_type = params["type"]  # uniaxial, biaxial, etc.
        direction = params["direction"]
        value = params["value"] / 100.0  # 百分比转小数
        mode = params.get("mode", "standard")
        poisson = params.get("poisson")
        
        F = StrainOperations.get_strain_matrix(strain_type, direction, value, mode, poisson)
        new_structure = self.context.backend.apply_strain(self.context.structure, F)
        
        # 保存
        outname = params.get("output", f"strain_{strain_type}_{direction}_{params['value']}.vasp")
        outpath = os.path.join(self.settings.struct_dir, outname)
        self.context.backend.write_structure(new_structure, outpath)
        
        return new_structure
    
    def _exec_transform(self, params: dict):
        """执行结构变换"""
        if not self.context.has_structure():
            raise RuntimeError("No structure loaded.")
        
        operation = params["operation"]  # supercell, rotate, mirror, translate
        
        if operation == "supercell":
            nx, ny, nz = params.get("factors", [2, 2, 2])
            new_structure = self.context.structure.copy()
            new_structure.make_supercell([nx, ny, nz])
            
        elif operation == "rotate":
            axis = params.get("axis", "z")
            angle = params.get("angle", 90)
            from pymatgen.transformations.standard_transformations import RotationTransformation
            rot = RotationTransformation(
                [1 if a == axis else 0 for a in ['x', 'y', 'z']], angle
            )
            new_structure = rot.apply_transformation(self.context.structure)
            
        elif operation == "mirror":
            plane = params.get("plane", "xy")
            flip_axis = {"xy": 2, "yz": 0, "xz": 1}[plane]
            new_structure = self.context.structure.copy()
            for site in new_structure:
                coords = list(site.coords)
                coords[flip_axis] *= -1
                site.coords = coords
                
        elif operation == "translate":
            t = params.get("vector", [0.5, 0, 0])
            new_structure = self.context.structure.copy()
            new_structure.translate_sites(
                indices=range(len(new_structure)),
                vector=t,
                frac_coords=True
            )
        else:
            raise ValueError(f"Unknown transform: {operation}")
        
        # 保存
        outname = params.get("output", f"{operation}.vasp")
        outpath = os.path.join(self.settings.struct_dir, outname)
        self.context.backend.write_structure(new_structure, outpath)
        
        return new_structure
    
    def _exec_convert(self, params: dict):
        """执行格式转换"""
        if not self.context.has_structure():
            raise RuntimeError("No structure loaded.")
        
        fmt = params["format"]  # cif, xyz, lammps, abacus, qe
        outname = params.get("output", f"converted.{fmt}")
        outpath = os.path.join(self.settings.struct_dir, outname)
        
        # 使用 convert 模块的写入方法
        from matbuilder.modules.convert.module import ConvertModule
        converter = ConvertModule()
        converter._write_structure(self.context, self.context.structure, fmt, outpath)
        
        return outpath
    
    def _exec_bend(self, params: dict):
        """执行弯曲"""
        if not self.context.has_structure():
            raise RuntimeError("No structure loaded.")
        
        operation = params["operation"]  # cylindrical, nanotube, etc.
        
        from matbuilder.modules.bend.module import BendModule
        bender = BendModule()
        
        # 简化调用，实际使用内部方法
        if operation == "nanotube":
            n, m = params.get("n", 5), params.get("m", 5)
            # 执行纳米管卷曲...
            pass
        
        return self.context.structure
    
    def _exec_custom(self, params: dict):
        """执行自定义脚本"""
        script_path = params.get("script")
        if script_path and os.path.exists(script_path):
            # 执行外部 Python 脚本
            exec(open(script_path).read(), {
                "context": self.context,
                "structure": self.context.structure,
            })
        return self.context.structure
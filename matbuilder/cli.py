# -*- coding: utf-8 -*-
"""
MatBuilder 主 CLI — v0.5
集成：对称性分析、插件系统
"""

import os
import glob
import sys
from collections import Counter

import matbuilder.modules

from matbuilder.config.settings import Settings
from matbuilder.core.context import Context
from matbuilder.core.registry import ModuleRegistry
from matbuilder.core.pipeline import PipelineExecutor as InteractiveExecutor
from matbuilder.core.hooks import HookPoint, HookContext
from matbuilder.backends.factory import BackendFactory
from matbuilder.utils.logging import Logger
from matbuilder.utils.validators import (
    get_float_input, get_int_input, get_choice_input, get_yes_no_input
)

# v0.4 流水线
from matbuilder.pipeline.executor import PipelineExecutor as YamlExecutor
from matbuilder.pipeline.yaml_parser import load_workflow_from_yaml

# v0.5 插件系统
from matbuilder.plugins import plugin_manager


class MatBuilderCLI:
    def __init__(self):
        self.settings = Settings()
        self.context = Context(settings=self.settings)
        self.executor = InteractiveExecutor(self.context)
        self.context.backend = BackendFactory.create(self.settings.backend)
        
        # 加载插件（v0.5）
        plugin_manager.discover_and_load()

    def _list_vasp_files(self):
        struct_dir = self.settings.struct_dir
        if not os.path.exists(struct_dir):
            return []
        patterns = [
            os.path.join(struct_dir, "*.vasp"),
            os.path.join(struct_dir, "*.VASP"),
        ]
        files = []
        for p in patterns:
            files.extend(glob.glob(p))
        return sorted(set(files))

    def _select_structure_file(self):
        files = self._list_vasp_files()
        if not files:
            Logger.error(f"No .vasp files found in '{self.settings.struct_dir}/'")
            return None

        if len(files) == 1:
            default_file = os.path.basename(files[0])
            Logger.info(f"Found single file: {default_file}")
            confirm = input(f"  Use this file? [Y/n]: ").strip().lower()
            if confirm in ['', 'y', 'yes']:
                return files[0]

        print(f"\n  Available structure files in '{self.settings.struct_dir}/':")
        for i, f in enumerate(files, 1):
            fname = os.path.basename(f)
            marker = "  ← default" if fname == self.settings.input_file else ""
            print(f"    [{i}]  {fname}{marker}")
        print(f"    [0]  Enter filename manually")

        while True:
            choice = input("\n  Select: ").strip()
            if choice == '0':
                fname = input("  Enter filename (in structs/): ").strip()
                filepath = os.path.join(self.settings.struct_dir, fname)
                if os.path.exists(filepath):
                    return filepath
                else:
                    Logger.error(f"File not found: {filepath}")
            try:
                idx = int(choice)
                if 1 <= idx <= len(files):
                    return files[idx - 1]
                else:
                    Logger.error("Invalid selection.")
            except ValueError:
                Logger.error("Please enter a number.")

    def load_structure(self):
        """加载结构，触发插件钩子"""
        # 触发 BEFORE_LOAD
        hook_ctx = HookContext(event=HookPoint.BEFORE_LOAD, context=self.context)
        plugin_manager.trigger_hook_point(HookPoint.BEFORE_LOAD, hook_ctx)

        filepath = self._select_structure_file()
        if filepath is None:
            return False

        self.settings.input_file = os.path.basename(filepath)
        try:
            structure, metadata = self.context.backend.load_structure(filepath)
            self.context.set_structure(structure, filepath, metadata)

            # 触发 AFTER_LOAD
            hook_ctx = HookContext(event=HookPoint.AFTER_LOAD, context=self.context, 
                                   structure=structure, params={"file": filepath})
            plugin_manager.trigger_hook_point(HookPoint.AFTER_LOAD, hook_ctx)

            params = self.context.backend.get_lattice_params(structure)
            species = [str(site.specie) for site in structure]
            counts = Counter(species)
            elements = list(counts.keys())

            Logger.info(f"Loaded: {filepath}")
            Logger.info(f"Elements : {' '.join(elements)}  |  Total: {len(structure)} atoms")
            Logger.info(f"Lattice  : a={params['a']:.4f}  b={params['b']:.4f}  c={params['c']:.4f}")
            Logger.info(f"Angles   : α={params['alpha']:.2f}  β={params['beta']:.2f}  γ={params['gamma']:.2f}")
            return True
        except Exception as e:
            Logger.error(str(e))
            return False

    def _settings_edit_menu(self):
        while True:
            Logger.banner("Settings Editor")
            settings_dict = self.settings.to_dict()
            keys = list(settings_dict.keys())
            print("\n  Current Settings:")
            for i, (key, value) in enumerate(settings_dict.items(), 1):
                print(f"    [{i}]  {key:25s} = {value}")
            print(f"\n    [r]  Reset to defaults")
            print(f"    [s]  Save & Back")
            print(f"    [0]  Back without saving")
            print("-" * 72)
            choice = input("\n  Select item to edit: ").strip().lower()
            if choice == '0':
                break
            elif choice == 'r':
                self.settings.reset_defaults()
                Logger.success("Settings reset to defaults.")
            elif choice == 's':
                Logger.success("Settings saved.")
                break
            else:
                try:
                    idx = int(choice)
                    if 1 <= idx <= len(keys):
                        key = keys[idx - 1]
                        current = getattr(self.settings, key)
                        print(f"\n  Current: {key} = {current}")
                        if isinstance(current, bool):
                            new_val = get_yes_no_input(f"  New value for {key}:", default=current)
                        elif isinstance(current, int):
                            new_val = get_int_input(f"  New value: ")
                        elif isinstance(current, float):
                            new_val = get_float_input(f"  New value: ")
                        elif isinstance(current, tuple):
                            new_val = tuple(map(int, input(f"  New value (space-separated): ").split()))
                        else:
                            new_val = input(f"  New value: ").strip()
                        setattr(self.settings, key, new_val)
                        Logger.success(f"{key} updated to {new_val}")
                    else:
                        Logger.error("Invalid selection.")
                except ValueError as e:
                    Logger.error(f"Invalid input: {e}")

    def _pipeline_menu(self):
        while True:
            Logger.banner("Pipeline Mode (YAML Batch)")
            print("\n  ------------------- Options ---------------------")
            Logger.menu_item("1", "Run Workflow       (执行 YAML 工作流)")
            Logger.menu_item("2", "Create Template    (生成示例工作流)")
            Logger.menu_item("3", "Validate Workflow  (验证 YAML 语法)")
            Logger.menu_item("0", "Back to Main Menu")
            print("-" * 72)
            choice = input("\n  Select: ").strip()
            if choice == '0':
                break
            elif choice == '1':
                self._run_yaml_workflow()
            elif choice == '2':
                self._create_template()
            elif choice == '3':
                self._validate_workflow()
            else:
                Logger.error("Invalid option.")
                input("  Press Enter...")

    def _run_yaml_workflow(self):
        import glob
        workflow_dir = "workflows"
        if not os.path.exists(workflow_dir):
            os.makedirs(workflow_dir)
        yaml_files = sorted(glob.glob(os.path.join(workflow_dir, "*.yaml")))
        yaml_files.extend(sorted(glob.glob(os.path.join(workflow_dir, "*.yml"))))
        if not yaml_files:
            Logger.error(f"No YAML files found in '{workflow_dir}/'")
            input("  Press Enter...")
            return
        print(f"\n  Available workflows:")
        for i, f in enumerate(yaml_files, 1):
            print(f"    [{i}]  {os.path.basename(f)}")
        print(f"    [0]  Enter path manually")
        choice = input("\n  Select: ").strip()
        try:
            if choice == '0':
                path = input("  Enter YAML path: ").strip()
            else:
                path = yaml_files[int(choice) - 1]
        except (ValueError, IndexError):
            Logger.error("Invalid selection.")
            input(); return
        try:
            workflow = load_workflow_from_yaml(path)
            executor = YamlExecutor()
            executor.execute(workflow)
        except Exception as e:
            Logger.error(f"Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
        input("\n  Press Enter...")

    def _create_template(self):
        template = '''name: strain_batch_example
description: Batch generate uniaxial strain structures from -5% to +5%
steps:
  - name: load_structure
    type: load
    params:
      file: structs/PCM.vasp
    output: base
  - name: strain_neg5
    type: strain
    params:
      type: uniaxial
      direction: a
      value: -5
      mode: standard
      output: PCM_a_-5.vasp
  - name: strain_0
    type: strain
    params:
      type: uniaxial
      direction: a
      value: 0
      mode: standard
      output: PCM_a_0.vasp
  - name: strain_pos5
    type: strain
    params:
      type: uniaxial
      direction: a
      value: 5
      mode: standard
      output: PCM_a_+5.vasp
'''
        workflow_dir = "workflows"
        os.makedirs(workflow_dir, exist_ok=True)
        path = os.path.join(workflow_dir, "template_strain.yaml")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(template)
        Logger.success(f"Template created: {path}")
        input("  Press Enter...")

    def _validate_workflow(self):
        path = input("  Enter YAML path to validate: ").strip()
        if not os.path.exists(path):
            Logger.error(f"File not found: {path}")
            input(); return
        try:
            workflow = load_workflow_from_yaml(path)
            print(f"\n  Workflow: {workflow.name}")
            print(f"  Description: {workflow.description}")
            print(f"  Steps: {len(workflow.steps)}")
            for i, step in enumerate(workflow.steps, 1):
                print(f"    [{i}] {step.name} ({step.step_type.value})")
            Logger.success("Validation passed!")
        except Exception as e:
            Logger.error(f"Validation failed: {e}")
        input("\n  Press Enter...")

    # ========== v0.5 新增：插件管理菜单 ==========
    def _plugin_menu(self):
        while True:
            Logger.banner("Plugin Manager")
            print("\n  ------------------- Plugins ---------------------")
            plugins = plugin_manager.list_plugins()
            if not plugins:
                Logger.info("No plugins loaded.")
            else:
                for name, plugin in plugins.items():
                    status = "✓" if plugin.enabled else "✗"
                    print(f"    [{status}] {name} v{plugin.version} - {plugin.description}")
            print("\n  ------------------- Actions ---------------------")
            Logger.menu_item("1", "Reload Plugins       (重新加载插件)")
            Logger.menu_item("2", "Enable Plugin        (启用插件)")
            Logger.menu_item("3", "Disable Plugin       (禁用插件)")
            Logger.menu_item("0", "Back to Main Menu")
            print("-" * 72)
            choice = input("\n  Select: ").strip()
            if choice == '0':
                break
            elif choice == '1':
                plugin_manager._loaded = False
                plugin_manager.discover_and_load()
                Logger.success("Plugins reloaded.")
            elif choice == '2' or choice == '3':
                pname = input("  Plugin name: ").strip()
                if pname in plugins:
                    if choice == '2':
                        plugin_manager.enable_plugin(pname)
                        Logger.success(f"Enabled: {pname}")
                    else:
                        plugin_manager.disable_plugin(pname)
                        Logger.success(f"Disabled: {pname}")
                else:
                    Logger.error(f"Plugin '{pname}' not found.")
            else:
                Logger.error("Invalid option.")
            input("  Press Enter...")

    def main(self):
        from matbuilder._version import __version__
        Logger.banner(f"MatBuilder v{__version__}  |  Material Structure Modeling Toolkit")

        if not self.load_structure():
            Logger.warn("Please place .vasp files in structs/ directory.")
            input("\n  Press Enter to exit...")
            return

        while True:
            Logger.banner("Main Menu")
            Logger.info(f"Current: {self.settings.input_file}")
            print()
            Logger.menu_item("1", "Strain Modeling      (应变建模)")
            Logger.menu_item("2", "Transform            (超胞/旋转/镜像/平移)")
            Logger.menu_item("3", "Convert              (格式转换)")
            Logger.menu_item("4", "Bend                 (弯曲/纳米管/喇叭)")
            Logger.menu_item("5", "Reload Structure     (重新加载结构)")
            Logger.menu_item("6", "Settings             (编辑全局设置)")
            Logger.menu_item("7", "Pipeline             (YAML 批处理工作流)")
            Logger.menu_item("8", "Symmetry             (对称性分析)")
            Logger.menu_item("9", "Plugins              (插件管理)")
            Logger.menu_item("10", "2D Materials Modeling (二维材料建模)")   # ← 新增
            Logger.menu_item("0", "Exit")
            print("-" * 72)

            choice = input("\n  Select: ").strip()

            if choice == '0':
                Logger.info("Goodbye!")
                break

            # 所有模块统一映射
            module_map = {
                '1': 'strain',
                '2': 'transform',
                '3': 'convert',
                '4': 'bend',
                '8': 'symmetry',
                '10': 'struct2d',          # ← 新增
            }

            if choice in module_map:
                module_name = module_map[choice]
                module_class = ModuleRegistry.get(module_name)
                if module_class:
                    module = module_class()
                    self.executor.run_interactive(module.run_interactive)
                else:
                    Logger.error(f"Module '{module_name}' not available.")
            elif choice == '5':
                self.load_structure()
            elif choice == '6':
                self._settings_edit_menu()
            elif choice == '7':
                self._pipeline_menu()
            elif choice == '9':
                self._plugin_menu()
            else:
                Logger.error("Invalid option.")    

def main():
    cli = MatBuilderCLI()
    cli.main()
GitHub README.md 文件已生成完毕。以下是完整内容，您可以直接复制使用：

---

```markdown
# MatBuilder

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.6.0-orange)](https://github.com/yourusername/MatBuilder)

**MatBuilder** (Material Structure Modeling Toolkit) 是一款面向计算材料学的交互式晶体结构建模工具包。采用类似 [VASPkit](https://vaspkit.com/) 的菜单式交互界面，为 VASP、ABACUS、Quantum ESPRESSO、LAMMPS 等主流计算软件提供结构预处理支持。

---

## 功能概览

| 模块 | 版本 | 功能描述 |
|------|------|---------|
| **Strain** | v0.1 | 5种应变模式（单轴/双轴/剪切/纯剪切/静水压）× 3种修正模式（标准/泊松比/体积守恒） |
| **Transform** | v0.2 | 超胞构建、旋转、镜像、平移、真空层添加 |
| **Convert** | v0.3 | 6种格式互转（POSCAR ↔ CIF ↔ XYZ ↔ LAMMPS ↔ ABACUS ↔ QE） |
| **Bend** | v0.4 | 5种弯曲/卷曲模式（圆柱/球面/纳米管/喇叭/波纹） |
| **Pipeline** | v0.4 | YAML 配置批处理，可复现工作流 |
| **Symmetry** | v0.5 | 空间群分析、Wyckoff 位置、应变对称性追踪 |
| **Plugins** | v0.5 | 事件钩子插件系统（内置 KPOINTS/POTCAR/Phonopy 插件） |
| **Struct2D** | v0.6 | 9种2D建模功能（Slab/单层/转角/异质结/缺陷/超晶格/纳米带/界面/滑移铁电） |

---

## 安装

### 环境要求

- Python >= 3.9
- numpy >= 1.20.0
- pymatgen >= 2023.0.0
- ase >= 3.22.0
- spglib >= 2.0.0

### 快速安装

```bash
# 克隆仓库
git clone https://github.com/Ziang-Stone/matbuilder.git
cd MatBuilder

# 创建并激活虚拟环境（推荐）
conda create -n matbuilder python=3.10
conda activate matbuilder

# 安装依赖
pip install -r requirements.txt

# 安装 MatBuilder
pip install -e .        # 开发模式
# 或
pip install .           # 生产模式
```

### 验证安装

```bash
matbuilder --version
# 预期输出: MatBuilder 0.6.0
```

---

## 快速开始

### 交互式使用

```bash
# 在项目根目录下创建 structs/ 文件夹
mkdir structs
cp your_structure.vasp structs/

# 启动交互界面
matbuilder
```

### 编程式使用

```python
from pathlib import Path
from matbuilder.modules.strain.module import StrainModule
from matbuilder.backends.pymatgen import PymatgenBackend

# 初始化后端
backend = PymatgenBackend()
structure = backend.read_structure("structs/PCM.vasp")

# 应用单轴应变（泊松比修正）
module = StrainModule()
module.apply_uniaxial(structure, direction='a', strain=0.05, mode='poisson', poisson=0.3)
```

---

## 功能展示

### 应变建模

```
========================================================================
    Strain Modeling
========================================================================
  [1] Uniaxial Strain      (单轴: a / b / c)
  [2] Biaxial Strain       (双轴: ab / bc / ac)
  [3] Simple Shear         (简单剪切)
  [4] Pure Shear           (纯剪切)
  [5] Hydrostatic          (三轴静水压)
------------------------------------------------------------------------
```

### 2D结构建模

```
========================================================================
    Struct2D - 2D Structure Modeling
========================================================================
  [1] Slab Model           (表面切割)
  [2] Monolayer Extraction (单层剥离)
  [3] Twist Stacking       (转角堆叠)
  [4] Heterostructure      (异质结)
  [5] Defects & Doping     (缺陷与掺杂)
  [6] Superlattice         (超晶格)
  [7] Nanoribbon           (纳米带)
  [8] Substrate Interface  (衬底界面)
  [9] Sliding Ferroelectricity (滑移铁电)
------------------------------------------------------------------------
```

### 流水线批处理

```yaml
# workflows/strain_series.yaml
name: uniaxial_strain_series
steps:
  - name: load
    type: load
    params:
      file: structs/PCM.vasp

  - name: strain_neg5
    type: strain
    params:
      type: uniaxial
      direction: a
      value: -5
      mode: poisson
      poisson: 0.3
      output: PCM_a_-5.vasp

  - name: strain_pos5
    type: strain
    params:
      type: uniaxial
      direction: a
      value: 5
      mode: poisson
      poisson: 0.3
      output: PCM_a_+5.vasp
```

执行：
```bash
matbuilder --pipeline workflows/strain_series.yaml
```

---

## 项目结构

```
MatBuilder/
├── run.py                          # 入口脚本
├── pyproject.toml                  # 项目配置
├── requirements.txt                # 依赖列表
├── README.md                       # 本文件
├── LICENSE                         # MIT 许可证
├── structs/                        # 用户结构文件目录
│   └── PCM.vasp
├── workflows/                      # YAML 工作流目录
│   └── template_strain.yaml
├── src/
│   └── matbuilder/
│       ├── __init__.py
│       ├── _version.py             # 版本号
│       ├── main.py                 # 编程入口
│       ├── cli.py                  # 交互式 CLI
│       │
│       ├── core/                   # 核心框架
│       │   ├── base.py             # ModuleBase + BackendBase
│       │   ├── context.py          # 运行时上下文
│       │   ├── registry.py         # 模块自动注册
│       │   └── pipeline.py         # 交互式执行器
│       │
│       ├── backends/               # 后端适配
│       │   ├── pymatgen.py         # pymatgen 适配器
│       │   └── factory.py
│       │
│       ├── config/                 # 配置管理
│       │   └── settings.py
│       │
│       ├── utils/                  # 工具集
│       │   ├── logging.py          # 彩色日志
│       │   └── validators.py       # 输入校验
│       │
│       ├── modules/                # 业务模块
│       │   ├── strain/             # 应变建模
│       │   ├── transform/          # 结构变换
│       │   ├── convert/            # 格式转换
│       │   ├── bend/               # 弯曲建模
│       │   ├── symmetry/           # 对称性分析
│       │   └── struct2d/           # 2D结构建模
│       │
│       ├── pipeline/               # 流水线框架
│       │   ├── workflow.py
│       │   ├── executor.py
│       │   └── yaml_parser.py
│       │
│       └── plugins/                # 插件系统
│           ├── base.py             # 插件抽象基类
│           ├── manager.py          # 插件管理器
│           └── builtin/            # 内置插件
│               ├── kpoints.py
│               ├── potcar.py
│               └── phonopy.py
```

---

## 文档

- [完整安装与使用手册](docs/MatBuilder_v0.6.0_完整安装与使用手册.md)
- [滑移铁电DFT计算指南](docs/滑移铁电的VASP计算流程说明.md)
- [API 文档](docs/API.md) (开发中)

---

## 版本更新日志

| 版本 | 发布日期 | 主要更新 |
|------|---------|---------|
| v0.6.0 | 2026-07-13 | Struct2D模块（9种2D建模功能）、滑移铁电结构生成 |
| v0.5.0 | 2026-07-12 | 对称性分析模块、插件系统 |
| v0.4.0 | 2026-07-12 | Bend模块、Pipeline YAML批处理 |
| v0.3.0 | 2026-07-11 | Convert模块（6种格式互转） |
| v0.2.0 | 2026-07-11 | Transform模块（超胞/旋转/镜像/平移） |
| v0.1.0 | 2026-07-11 | 初始版本，应变建模模块 |

---

## 引用

如果您在研究中使用了 MatBuilder，请考虑引用：

```bibtex
@software{matbuilder2026,
  title = {MatBuilder: Material Structure Modeling Toolkit},
  author = {MatBuilder Development Team},
  year = {2026},
  version = {0.6.0},
  url = {https://github.com/Ziang-Stone/matbuilder}
}
```

---

## 许可证

本项目采用 [MIT 许可证](LICENSE) 开源。

---

## 联系我们

- **问题反馈**：[GitHub Issues](https://github.com/Ziang-Stone/matbuilder/issues)
- **邮件联系**：leiyang@ctgu.edu.cn

---

**MatBuilder Team** | 计算材料学结构建模工具
```
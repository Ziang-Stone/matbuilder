# -*- coding: utf-8 -*-
"""
编程入口 — 非交互式 API 调用
"""

from matbuilder.core.context import Context
from matbuilder.config.settings import Settings
from matbuilder.modules.strain.module import StrainModule


def apply_strain_example():
    """编程式调用示例"""
    settings = Settings()
    ctx = Context(settings=settings)
    # 加载结构...
    # module = StrainModule()
    # module.run(ctx)
    pass


if __name__ == "__main__":
    apply_strain_example()

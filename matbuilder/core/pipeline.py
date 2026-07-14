# -*- coding: utf-8 -*-
"""
流水线执行器 — 简化版
"""

from typing import List, Callable


class PipelineExecutor:
    """顺序执行步骤"""
    
    def __init__(self, context):
        self.ctx = context
        self.steps: List[Callable] = []
    
    def add_step(self, step: Callable):
        self.steps.append(step)
        return self  # 链式调用
    
    def run(self):
        for step in self.steps:
            step(self.ctx)
    
    def run_interactive(self, menu_func: Callable):
        """
        交互式模式：将控制权交给模块自身的菜单函数
        """
        menu_func(self.ctx)

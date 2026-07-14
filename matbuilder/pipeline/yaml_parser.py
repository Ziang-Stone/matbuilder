# -*- coding: utf-8 -*-
"""
YAML 工作流解析器
"""

import yaml
import os

from .workflow import Workflow, WorkflowStep, StepType


def load_workflow_from_yaml(filepath: str) -> Workflow:
    """从 YAML 文件加载工作流"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Workflow file not found: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    return Workflow.from_dict(data)


def save_workflow_to_yaml(workflow: Workflow, filepath: str):
    """保存工作流到 YAML 文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(workflow.to_dict(), f, default_flow_style=False, allow_unicode=True)
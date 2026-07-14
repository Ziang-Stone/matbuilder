# -*- coding: utf-8 -*-
"""
工作流定义：步骤抽象与数据传递
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum


class StepType(Enum):
    """步骤类型"""
    LOAD = "load"           # 加载结构
    STRAIN = "strain"       # 应变
    TRANSFORM = "transform" # 结构变换
    CONVERT = "convert"     # 格式转换
    BEND = "bend"           # 弯曲
    CUSTOM = "custom"       # 自定义脚本


@dataclass
class WorkflowStep:
    """工作流步骤"""
    name: str
    step_type: StepType
    params: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None  # 执行条件（如 "prev.success"）
    output_name: Optional[str] = None  # 输出结构别名
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.step_type.value,
            "params": self.params,
            "condition": self.condition,
            "output": self.output_name,
        }


@dataclass
class Workflow:
    """工作流定义"""
    name: str
    description: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_step(self, step: WorkflowStep):
        self.steps.append(step)
        return self
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Workflow":
        """从字典创建工作流"""
        steps = []
        for s in data.get("steps", []):
            steps.append(WorkflowStep(
                name=s["name"],
                step_type=StepType(s["type"]),
                params=s.get("params", {}),
                condition=s.get("condition"),
                output_name=s.get("output"),
            ))
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            steps=steps,
            metadata=data.get("metadata", {}),
        )
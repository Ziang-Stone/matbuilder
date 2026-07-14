# -*- coding: utf-8 -*-
"""
输入校验工具 — v0.5+ (支持 struct2d)
"""

from typing import Optional, List, Callable, Any
import sys


def _get_input(prompt: str, default: Any = None,
               validator: Optional[Callable[[str], bool]] = None) -> str:
    """
    底层输入函数：支持默认值、校验、重试
    """
    if default is not None:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "

    while True:
        try:
            user_input = input(full_prompt).strip()
            if not user_input and default is not None:
                return str(default)
            if not user_input:
                print("  ! 输入不能为空，请重新输入")
                continue
            if validator and not validator(user_input):
                print("  ! 输入格式不正确，请重新输入")
                continue
            return user_input
        except (EOFError, KeyboardInterrupt):
            print("\n  用户取消输入")
            raise SystemExit
        except UnicodeDecodeError:
            print("  ! 输入包含非标准字符，请重新输入（仅使用数字和字母）")
            continue


def get_float_input(prompt: str, default: Optional[float] = None,
                    min_val: Optional[float] = None,
                    max_val: Optional[float] = None) -> float:
    """安全的浮点数输入"""
    def validator(s: str) -> bool:
        try:
            val = float(s)
            if min_val is not None and val < min_val:
                print(f"  ! 值必须 ≥ {min_val}")
                return False
            if max_val is not None and val > max_val:
                print(f"  ! 值必须 ≤ {max_val}")
                return False
            return True
        except ValueError:
            return False
    default_str = f"{default:.4f}" if default is not None else None
    return float(_get_input(prompt, default_str, validator))


def get_int_input(prompt: str, default: Optional[int] = None,
                  min_val: Optional[int] = None,
                  max_val: Optional[int] = None) -> int:
    """安全的整数输入"""
    def validator(s: str) -> bool:
        try:
            val = int(s)
            if min_val is not None and val < min_val:
                print(f"  ! 值必须 ≥ {min_val}")
                return False
            if max_val is not None and val > max_val:
                print(f"  ! 值必须 ≤ {max_val}")
                return False
            return True
        except ValueError:
            return False
    default_str = str(default) if default is not None else None
    return int(_get_input(prompt, default_str, validator))


def get_choice_input(prompt: str, choices: List[str], default: Optional[int] = None) -> int:
    """
    获取选项输入（返回选项编号）
    """
    print(f"\n{prompt}")
    for i, choice in enumerate(choices, 1):
        marker = " (默认)" if default == i else ""
        print(f"  {i}) {choice}{marker}")

    def validator(s: str) -> bool:
        try:
            val = int(s)
            return 1 <= val <= len(choices)
        except ValueError:
            return False

    default_str = str(default) if default is not None else None
    return int(_get_input("请选择", default_str, validator))


def get_yes_no_input(prompt: str, default: bool = True) -> bool:
    """Yes/No 确认"""
    def validator(s: str) -> bool:
        return s.lower() in ['y', 'yes', 'n', 'no', 'true', 'false', '1', '0', '']

    default_str = "Y" if default else "N"
    user_input = _get_input(prompt, default_str, validator).lower()
    return user_input in ['y', 'yes', 'true', '1'] or (not user_input and default)


def get_tuple_input(prompt: str, length: int = 3, dtype: type = int) -> tuple:
    """获取元组输入，如超胞 (2,2,2)"""
    def validator(s: str) -> bool:
        try:
            parts = s.replace(',', ' ').split()
            if len(parts) != length:
                print(f"  ! 需要 {length} 个值，当前 {len(parts)} 个")
                return False
            tuple(dtype(p) for p in parts)
            return True
        except ValueError:
            print(f"  ! 数值转换失败")
            return False

    raw = _get_input(prompt, None, validator)
    parts = raw.replace(',', ' ').split()
    return tuple(dtype(p) for p in parts)
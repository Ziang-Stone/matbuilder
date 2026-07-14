# -*- coding: utf-8 -*-
"""
终端美化输出
"""


class Logger:
    """ANSI 彩色日志"""
    
    HEADER  = '\033[95m'
    BLUE    = '\033[94m'
    CYAN    = '\033[96m'
    GREEN   = '\033[92m'
    WARNING = '\033[93m'
    FAIL    = '\033[91m'
    END     = '\033[0m'
    BOLD    = '\033[1m'
    
    @classmethod
    def banner(cls, text: str):
        print("\n" + "=" * 72)
        print(f"    {cls.BOLD}{text}{cls.END}")
        print("=" * 72)
    
    @classmethod
    def info(cls, msg: str):
        print(f"  {cls.CYAN}[Info]{cls.END} {msg}")
    
    @classmethod
    def warn(cls, msg: str):
        print(f"  {cls.WARNING}[Warn]{cls.END} {msg}")
    
    @classmethod
    def error(cls, msg: str):
        print(f"  {cls.FAIL}[Error]{cls.END} {msg}")
    
    @classmethod
    def success(cls, msg: str):
        print(f"  {cls.GREEN}[OK]{cls.END} {msg}")
    
    @classmethod
    def menu_item(cls, key: str, desc: str):
        print(f"    [{cls.BOLD}{key}{cls.END}]  {desc}")
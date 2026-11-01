# -*- coding: utf-8 -*-
"""
pytest 公共配置：把项目根目录加入模块搜索路径，
保证直接执行 `pytest` 或 `python run.py test` 都能 import 到 src 和 config。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

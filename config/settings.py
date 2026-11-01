# -*- coding: utf-8 -*-
"""
全局配置文件。
所有脚本统一从这里读取路径和数据库连接，避免在代码里到处写死路径。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录（本文件的上两级：config/ 的上一级）
ROOT_DIR = Path(__file__).resolve().parent.parent

# 读取 .env 中的配置（如果 .env 不存在也不报错，使用下面的默认值）
load_dotenv(ROOT_DIR / ".env")

# ---------- 路径配置 ----------
RAW_DIR = ROOT_DIR / "data" / "raw"            # 多源原始数据
WAREHOUSE_DIR = ROOT_DIR / "data" / "warehouse"  # SQLite 数据库文件目录
OUTPUT_DIR = ROOT_DIR / "outputs"              # 指标计算结果、评估报告输出
DDL_DIR = ROOT_DIR / "src" / "models"          # 建表 DDL 目录

# ---------- 数据库配置 ----------
# 默认走 SQLite，保证不装 MySQL 也能跑通全链路；在 .env 里改成 mysql 连接串即可切换
DB_URL = os.getenv("DB_URL", "sqlite:///data/warehouse/warehouse.db")
# SQLAlchemy 的 sqlite 相对路径是相对“运行目录”的，这里改成绝对路径最稳妥
if DB_URL.startswith("sqlite:///") and not DB_URL.startswith("sqlite:////"):
    _rel_path = DB_URL.replace("sqlite:///", "", 1)
    DB_URL = f"sqlite:///{(ROOT_DIR / _rel_path).as_posix()}"

# 数据库方言：mysql 或 sqlite（拼 Prompt 时要告诉大模型该写哪种 SQL）
DB_DIALECT = "mysql" if DB_URL.startswith("mysql") else "sqlite"

# ---------- 大模型配置 ----------
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# ---------- 模拟数据的业务参数（固定窗口，保证评估题里的日期永远有数据）----------
DATA_START_DATE = "2026-07-19"   # 数据起始日期
DATA_END_DATE = "2026-10-16"     # 数据结束日期
RANDOM_SEED = 42                 # 随机种子，保证每次生成的数据一致、可复现


def ensure_dirs() -> None:
    """程序运行前确保必要目录存在。"""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

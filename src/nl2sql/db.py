# -*- coding: utf-8 -*-
"""
数据库只读访问
==============

NL2SQL 链路统一通过这里执行 SQL，返回列名和行数据。
"""
from sqlalchemy import text

from src.etl.load import get_engine


def run_query(sql: str) -> tuple[list[str], list[tuple]]:
    """执行查询，返回 (列名列表, 行数据列表)。

    出错时由上层捕获异常；连接随用随关。
    """
    engine = get_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [tuple(row) for row in result.fetchall()]
        return columns, rows
    finally:
        engine.dispose()

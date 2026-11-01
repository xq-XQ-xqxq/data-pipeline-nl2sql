# -*- coding: utf-8 -*-
"""
数仓库级数据质量测试（需要先跑过 ETL：python run.py）
====================================================

这是数据工程里的“数据质量监控”思路，等价于给数据库写断言：
  - 表非空
  - 主键唯一
  - 事实表外键在维度表中都能找到（参照完整性）
  - 枚举字段取值合法
没跑过 ETL（库里还没表）时自动跳过，不影响其余测试。
"""
import pandas as pd
import pytest

from src.etl.load import get_engine


def _table_exists(engine, table: str) -> bool:
    try:
        pd.read_sql(f"SELECT * FROM {table} LIMIT 1", engine)
        return True
    except Exception:  # noqa: BLE001
        return False


@pytest.fixture(scope="module")
def tables():
    engine = get_engine()
    if not _table_exists(engine, "fact_user_event"):
        pytest.skip("数仓尚未初始化，请先执行 python run.py")
    data = {
        name: pd.read_sql(f"SELECT * FROM {name}", engine)
        for name in ["dim_date", "dim_user", "dim_product", "dim_channel", "fact_user_event"]
    }
    engine.dispose()
    return data


def test_all_tables_not_empty(tables):
    for name, df in tables.items():
        assert len(df) > 0, f"{name} 为空，ETL 可能失败"


def test_fact_primary_key_unique(tables):
    fact = tables["fact_user_event"]
    assert fact["event_id"].is_unique, "事实表 event_id 出现重复"


def test_fact_referential_integrity(tables):
    """事实表里的外键必须在维度表中存在。"""
    fact = tables["fact_user_event"]
    assert set(fact["user_id"]) <= set(tables["dim_user"]["user_id"]), "存在关联不到用户的事件"
    assert set(fact["product_id"]) <= set(tables["dim_product"]["product_id"]), "存在关联不到商品的事件"
    assert set(fact["channel_id"]) <= set(tables["dim_channel"]["channel_id"]), "存在关联不到渠道的事件"
    assert set(fact["date_id"]) <= set(tables["dim_date"]["date_id"]), "存在关联不到日期的事件"


def test_event_type_domain(tables):
    valid = {"view", "cart", "order", "pay"}
    actual = set(tables["fact_user_event"]["event_type"].unique())
    assert actual <= valid, f"出现非法事件类型：{actual - valid}"


def test_amount_non_negative(tables):
    fact = tables["fact_user_event"]
    assert (fact["amount"].dropna() >= 0).all(), "存在负金额"


def test_dim_date_weekend_domain(tables):
    assert set(tables["dim_date"]["is_weekend"].unique()) <= {0, 1}

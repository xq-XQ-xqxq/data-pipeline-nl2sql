# -*- coding: utf-8 -*-
"""
数据清洗逻辑的单元测试（数据质量“左移”：清洗规则先测过，再放进 ETL）。
"""
import pandas as pd

from src.etl.transform import (
    build_dim_date,
    clean_events,
    clean_products,
    clean_users,
)


# ---------- 用户表清洗 ----------

def test_users_deduplicate_by_user_id():
    """重复导出的用户行应按 user_id 去重。"""
    raw = pd.DataFrame({
        "user_id": ["U001", "U001", "U002"],
        "gender": ["男", "男", "女"],
        "age": ["25", "25", "30"],
        "city": ["北京", "北京", "上海"],
        "register_date": ["2026-08-01", "2026-08-01", "2026-09-01"],
    })
    out = clean_users(raw)
    assert len(out) == 2
    assert out["user_id"].tolist() == ["U001", "U002"]


def test_users_gender_is_standardized():
    """性别脏写法要统一成 男/女/未知。"""
    raw = pd.DataFrame({
        "user_id": ["U1", "U2", "U3", "U4"],
        "gender": ["M", "male", " 女 ", ""],
        "age": ["25", "26", "27", "28"],
        "city": ["北京", "上海", "广州", "深圳"],
        "register_date": ["2026-08-01"] * 4,
    })
    out = clean_users(raw).set_index("user_id")
    assert out.loc["U1", "gender"] == "男"
    assert out.loc["U2", "gender"] == "男"
    assert out.loc["U3", "gender"] == "女"
    assert out.loc["U4", "gender"] == "未知"


def test_users_abnormal_age_is_fixed():
    """年龄异常值（负数、超大值）要被中位数替换，且最终年龄都在合理区间。"""
    raw = pd.DataFrame({
        "user_id": ["U1", "U2", "U3", "U4", "U5"],
        "gender": ["男"] * 5,
        "age": ["20", "22", "24", "999", "-5"],
        "city": ["北京"] * 5,
        "register_date": ["2026-08-01"] * 5,
    })
    out = clean_users(raw)
    assert (out["age"] >= 10).all() and (out["age"] <= 100).all()
    # 正常值不应被改动
    assert out.loc[out["user_id"] == "U1", "age"].iloc[0] == 20


def test_users_mixed_date_formats_are_parsed():
    """三种日期写法都要能解析，无法解析的置空（NULL）。"""
    raw = pd.DataFrame({
        "user_id": ["U1", "U2", "U3", "U4"],
        "gender": ["男"] * 4,
        "age": ["25"] * 4,
        "city": ["北京"] * 4,
        "register_date": ["2026-08-01", "2026/8/1", "2026年8月1日", "未知"],
    })
    out = clean_users(raw)
    parsed = out["register_date"]
    assert parsed.iloc[0] == pd.Timestamp("2026-08-01")
    assert parsed.iloc[1] == pd.Timestamp("2026-08-01")
    assert parsed.iloc[2] == pd.Timestamp("2026-08-01")
    assert pd.isna(parsed.iloc[3])


# ---------- 商品表清洗 ----------

def test_products_missing_category_and_bad_price():
    raw = pd.DataFrame({
        "product_id": ["P1", "P2", "P3"],
        "product_name": ["手机1", "衣服1", "食品1"],
        "category": ["手机数码", None, "食品生鲜"],
        "price": ["1000", "0", "-50"],
    })
    out = clean_products(raw)
    assert out.loc[out["product_id"] == "P2", "category"].iloc[0] == "未分类"
    assert (out["price"] > 0).all()


# ---------- 事件表清洗 ----------

def test_events_dedup_and_type_filter():
    raw = pd.DataFrame({
        "event_id": ["E1", "E1", "E2", "E3"],
        "user_id": ["U1", "U1", "U2", "U3"],
        "product_id": ["P1", "P1", "P2", "P3"],
        "event_type": ["view", "view", "hacker", "pay"],
        "channel": ["微信", "微信", "抖音", "直接访问"],
        "event_time": ["2026-10-16 10:00:00"] * 4,
        "amount": ["", "", "", "99.5"],
    })
    out = clean_events(raw)
    assert out["event_id"].tolist() == ["E1", "E3"]  # E1 去重，E2 非法类型被丢弃


def test_events_channel_standardized_and_bad_time_dropped():
    raw = pd.DataFrame({
        "event_id": ["E1", "E2", "E3"],
        "user_id": ["U1", "U2", "U3"],
        "product_id": ["P1", "P2", "P3"],
        "event_type": ["view", "view", "view"],
        "channel": ["WeChat", " 信息流广告 ", "douyin"],
        "event_time": ["2026-10-16 10:00:00", "2026-13-40 99:99:99", "2026-10-16 12:00:00"],
        "amount": [""] * 3,
    })
    out = clean_events(raw)
    # 非法时间的 E2 被丢弃
    assert out["event_id"].tolist() == ["E1", "E3"]
    assert set(out["channel"]) == {"微信", "抖音"}


# ---------- 日期维度 ----------

def test_dim_date_covers_full_window():
    dim_date = build_dim_date()
    assert len(dim_date) == 90  # 2026-07-19 ~ 2026-10-16 共 90 天
    assert dim_date["date_id"].iloc[0] == 20260719
    assert dim_date["date_id"].iloc[-1] == 20261016
    # 2026-10-16 是周五（工作日 0）；10-17 周六（周末 1），抽一天验证
    fri = dim_date.loc[dim_date["date_id"] == 20261016, "is_weekend"].iloc[0]
    sat = dim_date.loc[dim_date["date_id"] == 20260725, "is_weekend"].iloc[0]  # 2026-07-25 周六
    assert fri == 0 and sat == 1

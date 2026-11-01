# -*- coding: utf-8 -*-
"""
ETL 第 2 步：Transform（清洗转换）
==================================

把三张原始表清洗成数仓需要的 5 张表：
  dim_user / dim_product / dim_channel / dim_date / fact_user_event

清洗规则都写在各自函数里，方便用 pytest 单测（见 tests/test_transform.py）。
"""
import pandas as pd

from config.settings import DATA_END_DATE, DATA_START_DATE

VALID_EVENT_TYPES = {"view", "cart", "order", "pay"}

# 渠道脏写法 -> 标准名（与数据生成脚本里的对应关系保持一致）
CHANNEL_MAP = {
    "微信": "微信", "wechat": "微信",
    "抖音": "抖音", "douyin": "抖音",
    "搜索引擎": "搜索引擎",
    "直接访问": "直接访问",
    "信息流广告": "信息流广告",
}

# 渠道固定排序，保证每次跑 channel_id 都稳定
CANONICAL_CHANNELS = sorted(set(CHANNEL_MAP.values()))

GENDER_MAP = {
    "男": "男", "m": "男", "male": "男",
    "女": "女", "f": "女", "female": "女",
}


def _parse_mixed_date(series: pd.Series) -> pd.Series:
    """统一解析多种写法的日期：2026-08-01 / 2026/8/1 / 2026年8月1日；无法解析返回 NaT。"""
    s = series.astype(str).str.strip()
    s = s.str.replace("年", "-", regex=False).str.replace("月", "-", regex=False)
    s = s.str.replace("日", "", regex=False).str.replace("/", "-", regex=False)
    return pd.to_datetime(s, errors="coerce", format="mixed")


def clean_users(df: pd.DataFrame) -> pd.DataFrame:
    """清洗用户表：去空格 -> 去重 -> 性别标准化 -> 年龄异常处理 -> 日期解析。"""
    df = df.copy()
    df["user_id"] = df["user_id"].str.strip()
    df["city"] = df["city"].str.strip()

    # 1) 删除完全重复的行（同一 user_id 重复导出）
    df = df.drop_duplicates(subset=["user_id"], keep="first")

    # 2) 性别统一：M/male 一律算男；空值或无法识别的填“未知”
    df["gender"] = df["gender"].fillna("").str.strip().str.lower().map(GENDER_MAP).fillna("未知")

    # 3) 年龄转数值，不合理的值（<10 或 >100）置空，再用整体中位数填补
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    df.loc[(df["age"] < 10) | (df["age"] > 100), "age"] = pd.NA
    df["age"] = df["age"].fillna(df["age"].median()).round().astype("int64")

    # 4) 注册日期：多格式解析，解析失败的脏值置 NaT（入库后是 NULL）
    df["register_date"] = _parse_mixed_date(df["register_date"])

    return df[["user_id", "gender", "age", "city", "register_date"]].reset_index(drop=True)


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    """清洗商品表：缺失分类填“未分类”，异常价格用品类中位数填补。"""
    df = df.copy()
    df["product_id"] = df["product_id"].str.strip()
    df["product_name"] = df["product_name"].str.strip()
    df["category"] = df["category"].fillna("未分类").str.strip()
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

    # 0、负数都视为异常价格
    df.loc[df["price"] <= 0, "price"] = pd.NA
    # 优先用“同品类中位数”补，缺不到再用全局中位数
    df["price"] = df.groupby("category")["price"].transform(lambda s: s.fillna(s.median()))
    df["price"] = df["price"].fillna(df["price"].median()).round(2)

    df = df.drop_duplicates(subset=["product_id"], keep="first")
    return df[["product_id", "product_name", "category", "price"]].reset_index(drop=True)


def clean_events(df: pd.DataFrame) -> pd.DataFrame:
    """清洗事件表：去重 -> 事件类型过滤 -> 渠道标准化 -> 时间解析。"""
    df = df.copy()
    df["event_id"] = df["event_id"].str.strip()

    # 1) 按 event_id 去重
    df = df.drop_duplicates(subset=["event_id"], keep="first")

    # 2) 事件类型只保留 view/cart/order/pay，其余脏数据直接丢弃
    df["event_type"] = df["event_type"].fillna("").str.strip().str.lower()
    df = df[df["event_type"].isin(VALID_EVENT_TYPES)]

    # 3) 渠道名统一（WeChat -> 微信，去掉前后空格）
    df["channel"] = df["channel"].fillna("").str.strip().str.lower().map(CHANNEL_MAP)
    df = df[df["channel"].notna()]

    # 4) 时间解析，非法时间行丢弃；金额转数值（空值保持 NaN）
    df["event_time"] = pd.to_datetime(df["event_time"], errors="coerce", format="mixed")
    df = df[df["event_time"].notna()]
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    return df[["event_id", "user_id", "product_id", "event_type",
               "channel", "event_time", "amount"]].reset_index(drop=True)


def build_dim_date() -> pd.DataFrame:
    """生成日期维度表：覆盖模拟数据的完整时间窗口。"""
    dates = pd.date_range(DATA_START_DATE, DATA_END_DATE, freq="D")
    return pd.DataFrame({
        "date_id": [int(d.strftime("%Y%m%d")) for d in dates],
        "full_date": dates.strftime("%Y-%m-%d"),
        "year": dates.year,
        "month": dates.month,
        "day": dates.day,
        "week_of_year": [int(d.strftime("%V")) for d in dates],
        "quarter": ((dates.month - 1) // 3 + 1),
        "is_weekend": [int(d.weekday() >= 5) for d in dates],
    })


def build_dim_channel() -> pd.DataFrame:
    """生成渠道维度表（渠道来自固定字典，ID 按名称排序，保证稳定）。"""
    return pd.DataFrame({
        "channel_id": range(1, len(CANONICAL_CHANNELS) + 1),
        "channel_name": CANONICAL_CHANNELS,
    })


def transform_all(raw: dict) -> dict:
    """把抽取出来的三张原始表，整体转换成数仓五张表。"""
    users = clean_users(raw["users"])
    products = clean_products(raw["products"])
    events = clean_events(raw["events"])

    dim_date = build_dim_date()
    dim_channel = build_dim_channel()

    # ---- 组装事实表：把渠道名、日期换成维度表主键 ----
    fact = events.copy()
    channel_to_id = dict(zip(dim_channel["channel_name"], dim_channel["channel_id"]))
    fact["channel_id"] = fact["channel"].map(channel_to_id)
    fact["date_id"] = fact["event_time"].dt.strftime("%Y%m%d").astype(int)

    # 只保留能关联上用户、商品、日期的事件（参照完整性）
    fact = fact.merge(users[["user_id"]], on="user_id", how="inner")
    fact = fact.merge(products[["product_id"]], on="product_id", how="inner")
    fact = fact.merge(dim_date[["date_id"]], on="date_id", how="inner")

    fact = fact[["event_id", "user_id", "product_id", "channel_id",
                 "date_id", "event_type", "event_time", "amount"]]

    # 用户注册日期转成 date 对象，写入 MySQL 才会是 DATE 而不是时间戳
    users_out = users.copy()
    users_out["register_date"] = users_out["register_date"].dt.date

    return {
        "dim_date": dim_date,
        "dim_user": users_out,
        "dim_product": products,
        "dim_channel": dim_channel,
        "fact_user_event": fact,
    }

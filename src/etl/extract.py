# -*- coding: utf-8 -*-
"""
ETL 第 1 步：Extract（抽取）
从三个不同来源读取原始数据，读进来是什么样就是什么样，本步骤不做任何清洗。
"""
import json

import pandas as pd

from config.settings import RAW_DIR


def extract_users() -> pd.DataFrame:
    """来源1：业务库导出的用户 CSV。"""
    return pd.read_csv(RAW_DIR / "users.csv", encoding="utf-8-sig", dtype=str)


def extract_products() -> pd.DataFrame:
    """来源2：商品服务 API 导出的 JSON（先读 JSON 再转 DataFrame）。"""
    with open(RAW_DIR / "products.json", encoding="utf-8") as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    # CSV 读进来的数字默认是字符串，这里统一转成字符串，和 CSV 来源保持一致
    df["price"] = df["price"].astype(str)
    return df


def extract_events() -> pd.DataFrame:
    """来源3：前端埋点日志 CSV。"""
    return pd.read_csv(RAW_DIR / "events.csv", encoding="utf-8-sig", dtype=str)


def extract_all() -> dict:
    """一次性抽取三个数据源。"""
    return {
        "users": extract_users(),
        "products": extract_products(),
        "events": extract_events(),
    }

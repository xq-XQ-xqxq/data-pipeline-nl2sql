# -*- coding: utf-8 -*-
"""
多源模拟数据生成脚本
====================

模拟真实公司里三种不同来源、不同格式的数据：
  1. users.csv     —— 业务数据库导出的用户表（CSV）
  2. products.json —— 商品服务通过 API 导出的商品数据（JSON）
  3. events.csv    —— 前端埋点日志（CSV，日志风格）

重点：为了让后面的 ETL 清洗环节有意义，这里故意制造了真实项目里常见的“脏数据”：
  - 用户表：重复行、性别写法不统一、年龄异常值、日期格式混乱、城市带空格
  - 商品表：缺失分类、价格为 0 或负数、字段为 null
  - 事件表：重复事件、非法事件类型、时间格式错误、渠道名中英文混用

运行方式：python -m src.data_gen.generate_mock_data
"""
import json
import random

import pandas as pd

from config.settings import (
    DATA_END_DATE,
    DATA_START_DATE,
    RAW_DIR,
    RANDOM_SEED,
    ensure_dirs,
)

# ---------- 业务维度常量（后续评估题里用到的名称都来自这里，不要随意改）----------
CITIES = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安"]
CATEGORIES = ["手机数码", "服饰鞋包", "食品生鲜", "家居日用", "美妆个护"]
# 埋点渠道：故意给出多种“脏写法”，由清洗环节统一
CHANNELS_RAW = ["微信", "WeChat", "抖音", "douyin", "搜索引擎", "直接访问", "信息流广告", " 信息流广告 "]
CHANNEL_CANONICAL = {
    "微信": "微信", "wechat": "微信",
    "抖音": "抖音", "douyin": "抖音",
    "搜索引擎": "搜索引擎",
    "直接访问": "直接访问",
    "信息流广告": "信息流广告",
}
EVENT_TYPES = ["view", "cart", "order", "pay"]  # 浏览 -> 加购 -> 下单 -> 支付

N_USERS = 1000      # 用户数
N_PRODUCTS = 150    # 商品数
N_DAYS = (pd.Timestamp(DATA_END_DATE) - pd.Timestamp(DATA_START_DATE)).days + 1


def _messy_date(ts: pd.Timestamp) -> str:
    """把标准日期随机变成三种格式，模拟业务库里混乱的日期写法。"""
    style = random.random()
    if style < 0.6:
        return ts.strftime("%Y-%m-%d")
    elif style < 0.9:
        return ts.strftime("%Y/%m/%d")          # 斜杠格式
    else:
        return f"{ts.year}年{ts.month}月{ts.day}日"  # 中文格式


def generate_users() -> pd.DataFrame:
    """生成用户表（含脏数据）。"""
    rows = []
    genders_clean = ["男", "女"]
    genders_messy = ["男", "女", "M", "male", "女 ", "", "男"]

    for i in range(1, N_USERS + 1):
        uid = f"U{i:05d}"
        gender = random.choice(genders_messy)
        age = random.randint(18, 60)
        # 约 3% 的年龄写成异常值
        if random.random() < 0.03:
            age = random.choice([999, -5, 200])
        city = random.choice(CITIES)
        if random.random() < 0.1:
            city = f"  {city} "  # 城市两侧混入空格
        reg_day = pd.Timestamp(DATA_START_DATE) + pd.Timedelta(days=random.randint(0, N_DAYS - 1))
        rows.append({
            "user_id": uid,
            "gender": gender,
            "age": age,
            "city": city,
            "register_date": _messy_date(reg_day),
        })

    df = pd.DataFrame(rows)
    # 再复制 20 行完全重复的数据，模拟重复导出
    df = pd.concat([df, df.sample(20, random_state=RANDOM_SEED)], ignore_index=True)
    # 少量注册日期改成无法解析的脏值
    df.loc[df.sample(15, random_state=1).index, "register_date"] = "未知"
    return df


def generate_products() -> list[dict]:
    """生成商品列表（含脏数据），最终写成 JSON。"""
    products = []
    for i in range(1, N_PRODUCTS + 1):
        category = random.choice(CATEGORIES)
        price = round(random.uniform(9.9, 4999), 2)
        item = {
            "product_id": f"P{i:04d}",
            "product_name": f"{category}商品{i:03d}",
            "category": category,
            "price": price,
        }
        r = random.random()
        if r < 0.05:
            item["category"] = None         # 缺失分类
        elif r < 0.08:
            item["price"] = 0               # 异常价格
        elif r < 0.11:
            item["price"] = -random.randint(1, 100)  # 负价格
        products.append(item)
    return products


def generate_events() -> pd.DataFrame:
    """生成用户行为埋点日志（漏斗逐级衰减 + 脏数据）。"""
    rows = []
    event_counter = 0
    start = pd.Timestamp(DATA_START_DATE)

    # 每个用户有一个“偏好渠道”：75% 的会话走偏好渠道，其余随机。
    # 这样渠道维度才有真实的区分度（否则 90 天下来人人用过所有渠道）。
    canonical_channels = ["微信", "抖音", "搜索引擎", "直接访问", "信息流广告"]
    channel_weights = [0.28, 0.24, 0.18, 0.18, 0.12]
    preferred = {
        u: random.choices(canonical_channels, weights=channel_weights, k=1)[0]
        for u in range(1, N_USERS + 1)
    }

    for day_offset in range(N_DAYS):
        day = start + pd.Timedelta(days=day_offset)
        # 每天约 45% 的用户活跃
        active_users = random.sample(range(1, N_USERS + 1), int(N_USERS * 0.45))

        for u in active_users:
            uid = f"U{u:05d}"
            # 每个活跃用户当天产生 1~4 次浏览会话
            for _ in range(random.randint(1, 4)):
                pid = f"P{random.randint(1, N_PRODUCTS):04d}"
                if random.random() < 0.75:
                    channel = preferred[u]                # 偏好渠道（标准写法）
                else:
                    channel = random.choice(CHANNELS_RAW)  # 偶尔走其他渠道（可能是脏写法）
                hour = random.randint(8, 23)
                minute = random.randint(0, 59)
                ts = day.replace(hour=hour, minute=minute, second=0)

                # 漏斗：浏览 ->(35%) 加购 ->(45%) 下单 ->(80%) 支付
                reached = ["view"]
                if random.random() < 0.35:
                    reached.append("cart")
                    if random.random() < 0.45:
                        reached.append("order")
                        if random.random() < 0.80:
                            reached.append("pay")

                for etype in reached:
                    event_counter += 1
                    amount = ""
                    if etype in ("order", "pay"):
                        amount = round(random.uniform(20, 2000), 2)
                    rows.append({
                        "event_id": f"E{event_counter:08d}",
                        "user_id": uid,
                        "product_id": pid,
                        "event_type": etype,
                        "channel": channel,
                        "event_time": ts.strftime("%Y-%m-%d %H:%M:%S"),
                        "amount": amount,
                    })

    df = pd.DataFrame(rows)
    # ---- 注入脏数据 ----
    # 1) 约 1% 完全重复的事件行
    df = pd.concat([df, df.sample(frac=0.01, random_state=RANDOM_SEED)], ignore_index=True)
    # 2) 非法事件类型
    bad_idx = df.sample(30, random_state=2).index
    df.loc[bad_idx, "event_type"] = random.choice(["click", "hacker", ""])
    # 3) 少量无法解析的时间
    df.loc[df.sample(20, random_state=3).index, "event_time"] = "2026-13-40 99:99:99"
    return df


def main() -> None:
    random.seed(RANDOM_SEED)
    ensure_dirs()

    users_df = generate_users()
    products = generate_products()
    events_df = generate_events()

    users_path = RAW_DIR / "users.csv"
    products_path = RAW_DIR / "products.json"
    events_path = RAW_DIR / "events.csv"

    users_df.to_csv(users_path, index=False, encoding="utf-8-sig")
    products_path.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
    events_df.to_csv(events_path, index=False, encoding="utf-8-sig")

    print("模拟数据已生成：")
    print(f"  1. 用户数据   {users_path}  共 {len(users_df)} 行（含重复/脏值）")
    print(f"  2. 商品数据   {products_path}  共 {len(products)} 条（JSON 格式）")
    print(f"  3. 埋点日志   {events_path}  共 {len(events_df)} 行（含重复/脏值）")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
业务指标的 pandas 实现
======================

指标口径与 query_templates.sql 完全一致，但用 pandas 计算：
好处是不依赖数据库方言，MySQL / SQLite 跑出来的结果都一样，也方便和 SQL 结果对账。

指标清单（14 个，覆盖日活、留存、转化三大类）：
  DAU / PV / 新增用户 / 加购用户 / 下单用户 / 支付用户 / 订单量 /
  GMV / 客单价AOV / 浏览-支付转化率 / 次日留存 / 7日留存 /
  渠道汇总 / 品类GMV / 复购用户数 / 工作日与周末平均DAU
"""
import pandas as pd

from src.etl.load import get_engine


def load_warehouse() -> dict:
    """把数仓 5 张表读成 DataFrame。"""
    engine = get_engine()
    tables = {
        name: pd.read_sql(f"SELECT * FROM {name}", engine)
        for name in ["dim_date", "dim_user", "dim_product", "dim_channel", "fact_user_event"]
    }
    engine.dispose()
    return tables


def calc_daily_metrics(tables: dict) -> pd.DataFrame:
    """按天汇总的核心指标表（指标 1-8 的日粒度版本）。"""
    fact = tables["fact_user_event"].copy()
    users = tables["dim_user"].copy()
    fact["dt"] = pd.to_datetime(fact["event_time"]).dt.normalize()

    # 各事件类型的去重用户数（透视成列：view/cart/order/pay 各一列）
    pivot = (
        fact.groupby(["dt", "event_type"])["user_id"]
        .nunique()
        .unstack(fill_value=0)
        .reindex(columns=["view", "cart", "order", "pay"], fill_value=0)
    )
    daily = pd.DataFrame(index=pivot.index)
    daily["dau"] = fact.groupby("dt")["user_id"].nunique()                 # 指标1 DAU
    daily["pv"] = fact[fact["event_type"] == "view"].groupby("dt").size()  # 指标2 PV
    daily["cart_users"] = pivot["cart"]
    daily["order_users"] = pivot["order"]
    daily["pay_users"] = pivot["pay"]

    order_cnt = (
        fact[fact["event_type"] == "order"].groupby("dt").size()
        .rename("order_count")                                             # 指标4 订单量
    )
    pay = fact[fact["event_type"] == "pay"]
    gmv = pay.groupby("dt")["amount"].sum().rename("gmv")                  # 指标5 GMV

    daily = daily.join(order_cnt, how="left").join(gmv, how="left")
    daily["order_count"] = daily["order_count"].fillna(0).astype(int)
    daily["pv"] = daily["pv"].fillna(0).astype(int)
    daily["gmv"] = daily["gmv"].fillna(0.0).round(2)
    daily["aov"] = (daily["gmv"] / daily["pay_users"].replace(0, pd.NA)).round(2)  # 指标6 客单价
    # 指标8：浏览-支付转化率 = 当天支付去重用户 / 当天浏览去重用户
    daily["view_to_pay_rate"] = (
        daily["pay_users"] / pivot["view"].replace(0, pd.NA)
    ).astype(float).round(4)

    # 指标3 新增用户（来自用户维度表的注册日期）
    users["register_date"] = pd.to_datetime(users["register_date"])
    new_users = users.groupby("register_date").size().rename("new_users")
    daily = daily.join(new_users, how="left")
    daily["new_users"] = daily["new_users"].fillna(0).astype(int)

    return daily.reset_index()


def calc_retention(tables: dict) -> pd.DataFrame:
    """指标9/10：次日留存率、7 日留存率（当天活跃用户在 N 天后仍活跃的比例）。"""
    fact = tables["fact_user_event"].copy()
    fact["dt"] = pd.to_datetime(fact["event_time"]).dt.normalize()
    active = fact.groupby("dt")["user_id"].apply(set)

    rows = []
    for dt, users_today in active.items():
        row = {"dt": dt, "active_users": len(users_today)}
        for gap, col in [(1, "d1_retention"), (7, "d7_retention")]:
            users_future = active.get(dt + pd.Timedelta(days=gap), set())
            kept = len(users_today & users_future)
            row[col] = round(kept / len(users_today), 4) if users_today else None
        rows.append(row)
    return pd.DataFrame(rows)


def calc_funnel(tables: dict, on_date: str | None = None) -> pd.DataFrame:
    """指标7：当日漏斗（浏览 -> 加购 -> 下单 -> 支付），含步骤转化率。

    on_date 形如 '2026-10-16'；不传则默认取数据中最后一天。
    注意必须按天（或固定短窗口）统计：窗口拉长到几十天，用户多次访问后
    几乎所有人都会走到支付，漏斗就失去了区分度。
    """
    fact = tables["fact_user_event"].copy()
    fact["dt"] = pd.to_datetime(fact["event_time"]).dt.strftime("%Y-%m-%d")
    if on_date is None:
        on_date = fact["dt"].max()
    fact = fact[fact["dt"] == on_date]

    stages = ["view", "cart", "order", "pay"]
    users = {
        s: set(fact.loc[fact["event_type"] == s, "user_id"])
        for s in stages
    }
    rows = []
    base = len(users["view"])
    for i, s in enumerate(stages):
        n = len(users[s])
        step_rate = n / len(users[stages[i - 1]]) if i > 0 and len(users[stages[i - 1]]) else 1.0
        rows.append({
            "dt": on_date,
            "stage": {"view": "浏览", "cart": "加购", "order": "下单", "pay": "支付"}[s],
            "users": n,
            "step_rate": round(step_rate, 4),       # 相对上一步
            "overall_rate": round(n / base, 4) if base else None,  # 相对第一步
        })
    return pd.DataFrame(rows)


def calc_channel_summary(tables: dict, days: int = 7) -> pd.DataFrame:
    """指标11：最近 N 天（默认 7 天）各渠道活跃用户、支付用户、GMV。

    同样不能用全窗口：90 天里几乎每个用户都用过所有渠道，渠道就没有区分度了。
    """
    fact = tables["fact_user_event"].copy()
    fact["dt"] = pd.to_datetime(fact["event_time"]).dt.strftime("%Y-%m-%d")
    last_day = fact["dt"].max()
    start_day = (pd.Timestamp(last_day) - pd.Timedelta(days=days - 1)).strftime("%Y-%m-%d")
    fact = fact[(fact["dt"] >= start_day) & (fact["dt"] <= last_day)]

    fact = fact.merge(tables["dim_channel"], on="channel_id", how="left")
    grouped = fact.groupby("channel_name")
    summary = pd.DataFrame({
        "active_users": grouped["user_id"].nunique(),
        "pay_users": fact[fact["event_type"] == "pay"]
        .groupby("channel_name")["user_id"].nunique(),
        "gmv": fact[fact["event_type"] == "pay"]
        .groupby("channel_name")["amount"].sum(),
    }).fillna(0).reset_index()
    summary["pay_users"] = summary["pay_users"].astype(int)
    summary["gmv"] = summary["gmv"].round(2)
    return summary.sort_values("gmv", ascending=False)


def calc_category_gmv(tables: dict) -> pd.DataFrame:
    """指标12：各品类 GMV 与支付笔数。"""
    pay = tables["fact_user_event"]
    pay = pay[pay["event_type"] == "pay"].merge(
        tables["dim_product"], on="product_id", how="left"
    )
    out = (
        pay.groupby("category")
        .agg(gmv=("amount", "sum"), pay_count=("event_id", "count"))
        .reset_index()
    )
    out["gmv"] = out["gmv"].round(2)
    return out.sort_values("gmv", ascending=False)


def calc_repeat_pay_users(tables: dict) -> int:
    """指标14：支付 >= 2 次的复购用户数。"""
    pay = tables["fact_user_event"]
    pay = pay[pay["event_type"] == "pay"]
    per_user = pay.groupby("user_id").size()
    return int((per_user >= 2).sum())


def calc_weekend_vs_workday(tables: dict, daily: pd.DataFrame) -> pd.DataFrame:
    """指标13：工作日 / 周末的平均 DAU。"""
    df = daily.copy()
    # dt 是时间戳、dim_date.full_date 在 SQLite 里是字符串，统一成 'YYYY-MM-DD' 再关联
    df["full_date"] = pd.to_datetime(df["dt"]).dt.strftime("%Y-%m-%d")
    df = df.merge(
        tables["dim_date"][["full_date", "is_weekend"]],
        on="full_date", how="left",
    )
    df["day_type"] = df["is_weekend"].map({1: "周末", 0: "工作日"})
    return (
        df.groupby("day_type")["dau"].mean().round(1)
        .rename("avg_dau").reset_index()
    )


def calc_all() -> dict:
    """计算全部指标，返回 {结果名: DataFrame}。"""
    tables = load_warehouse()
    daily = calc_daily_metrics(tables)
    return {
        "metrics_daily": daily,
        "retention": calc_retention(tables),
        "funnel": calc_funnel(tables),
        "channel_summary": calc_channel_summary(tables),
        "category_gmv": calc_category_gmv(tables),
        "weekend_vs_workday": calc_weekend_vs_workday(tables, daily),
        "repeat_pay_users": pd.DataFrame(
            [{"metric": "复购用户数", "value": calc_repeat_pay_users(tables)}]
        ),
    }

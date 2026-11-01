# -*- coding: utf-8 -*-
"""
表结构元数据
============

两个用途：
1. NL2SQL 模块把这里的“建表说明”注入给大模型（表结构注入）；
2. SQL 合法性校验时用它做表名白名单。

注意：字段说明要和 schema_mysql.sql / schema_sqlite.sql 保持一致。
"""

# 表名白名单：大模型生成的 SQL 只允许访问这 5 张表
ALLOWED_TABLES = {
    "dim_date", "dim_user", "dim_product", "dim_channel", "fact_user_event",
}

# 每张表的中文名（解释结果时用）
TABLE_COMMENTS = {
    "dim_date": "日期维度表",
    "dim_user": "用户维度表",
    "dim_product": "商品维度表",
    "dim_channel": "渠道维度表",
    "fact_user_event": "用户行为事件事实表",
}

# 注入给大模型的表结构描述（刻意写成建表语句风格，模型最熟悉）
SCHEMA_TEXT = """\
本数据库是一个电商数据分析数仓，采用星型模型，共 5 张表：

CREATE TABLE dim_date ( -- 日期维度表
    date_id      INT,       -- 日期主键，格式 YYYYMMDD，例如 20261016
    full_date    DATE,      -- 完整日期，例如 2026-10-16
    year         INT,       -- 年
    month        INT,       -- 月 1-12
    day          INT,       -- 日 1-31
    week_of_year INT,       -- 当年第几周
    quarter      INT,       -- 季度 1-4
    is_weekend   INT        -- 是否周末：1=周末，0=工作日
);

CREATE TABLE dim_user ( -- 用户维度表，一个用户一行
    user_id       VARCHAR, -- 用户编号，例如 U00001
    gender        VARCHAR, -- 性别，取值：男 / 女 / 未知
    age           INT,     -- 年龄
    city          VARCHAR, -- 城市：北京/上海/广州/深圳/杭州/成都/武汉/西安
    register_date DATE     -- 注册日期
);

CREATE TABLE dim_product ( -- 商品维度表
    product_id   VARCHAR,     -- 商品编号，例如 P0001
    product_name VARCHAR,     -- 商品名称，例如 手机数码商品001
    category     VARCHAR,     -- 品类：手机数码/服饰鞋包/食品生鲜/家居日用/美妆个护
    price        DECIMAL      -- 商品单价（元）
);

CREATE TABLE dim_channel ( -- 渠道维度表
    channel_id   INT,     -- 渠道编号
    channel_name VARCHAR  -- 渠道：微信/抖音/搜索引擎/直接访问/信息流广告
);

CREATE TABLE fact_user_event ( -- 用户行为事件事实表，一条埋点事件一行
    event_id    VARCHAR,      -- 事件编号
    user_id     VARCHAR,      -- 用户编号，关联 dim_user.user_id
    product_id  VARCHAR,      -- 商品编号，关联 dim_product.product_id
    channel_id  INT,          -- 渠道编号，关联 dim_channel.channel_id
    date_id     INT,          -- 日期主键，关联 dim_date.date_id
    event_type  VARCHAR,      -- 事件类型：view=浏览, cart=加购, order=下单, pay=支付
    event_time  DATETIME,     -- 事件发生时间
    amount      DECIMAL       -- 下单/支付金额（元）；view、cart 事件为 NULL
);

常用写法提示：
- 日活用户：COUNT(DISTINCT user_id)，可按 date_id 分组。
- 查具体日期请用 dim_date.full_date = '2026-10-16' 关联事实表，不要直接猜 date_id。
- 查渠道/商品/用户属性时，必须用对应字段 JOIN 维度表。
- 金额相关只统计 event_type = 'pay' 的行。
"""

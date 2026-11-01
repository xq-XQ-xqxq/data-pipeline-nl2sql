-- =====================================================================
-- 数仓星型模型建表 DDL（SQLite 版本，零安装本地练习用）
-- 表结构与 schema_mysql.sql 完全一致，仅语法按 SQLite 调整
-- ETL 程序会根据 .env 里的 DB_URL 自动选择本文件或 MySQL 版本
-- =====================================================================

CREATE TABLE IF NOT EXISTS dim_date (
    date_id      INTEGER PRIMARY KEY,   -- 日期主键 YYYYMMDD
    full_date    TEXT    NOT NULL,      -- 完整日期 YYYY-MM-DD
    year         INTEGER NOT NULL,
    month        INTEGER NOT NULL,
    day          INTEGER NOT NULL,
    week_of_year INTEGER NOT NULL,
    quarter      INTEGER NOT NULL,
    is_weekend   INTEGER NOT NULL       -- 1=周末 0=工作日
);

CREATE TABLE IF NOT EXISTS dim_user (
    user_id       TEXT PRIMARY KEY,
    gender        TEXT NOT NULL,        -- 男/女/未知
    age           INTEGER,
    city          TEXT NOT NULL,
    register_date TEXT                  -- 脏值清洗后置 NULL
);

CREATE TABLE IF NOT EXISTS dim_product (
    product_id   TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category     TEXT NOT NULL,
    price        REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_channel (
    channel_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS fact_user_event (
    event_id    TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    product_id  TEXT NOT NULL,
    channel_id  INTEGER NOT NULL,
    date_id     INTEGER NOT NULL,
    event_type  TEXT NOT NULL,          -- view/cart/order/pay
    event_time  TEXT NOT NULL,
    amount      REAL
);

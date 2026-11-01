-- =====================================================================
-- 数仓星型模型建表 DDL（MySQL 8.x 版本，老师技术栈交付物）
-- 结构：4 张维度表（dim_*） + 1 张事实表（fact_user_event）
-- 用法：先建库 CREATE DATABASE dw_demo DEFAULT CHARSET utf8mb4;
--       再执行：mysql -u root -p dw_demo < src/models/schema_mysql.sql
-- =====================================================================

-- 维度表1：日期维度表（一行代表一天，做按周/月/周末统计时用它）
CREATE TABLE IF NOT EXISTS dim_date (
    date_id      INT          PRIMARY KEY COMMENT '日期主键，格式 YYYYMMDD，如 20261016',
    full_date    DATE         NOT NULL COMMENT '完整日期',
    year         INT          NOT NULL COMMENT '年',
    month        INT          NOT NULL COMMENT '月(1-12)',
    day          INT          NOT NULL COMMENT '日(1-31)',
    week_of_year INT          NOT NULL COMMENT '一年中的第几周',
    quarter      INT          NOT NULL COMMENT '季度(1-4)',
    is_weekend   TINYINT      NOT NULL COMMENT '是否周末：1=周末，0=工作日'
) COMMENT='日期维度表';

-- 维度表2：用户维度表（一行一个用户，变化缓慢，典型 SCD 思路）
CREATE TABLE IF NOT EXISTS dim_user (
    user_id       VARCHAR(10) PRIMARY KEY COMMENT '用户编号',
    gender        VARCHAR(4)  NOT NULL COMMENT '性别：男/女/未知',
    age           INT         COMMENT '年龄（异常值清洗后）',
    city          VARCHAR(20) NOT NULL COMMENT '所在城市',
    register_date DATE        COMMENT '注册日期（无法解析的脏值置为 NULL）'
) COMMENT='用户维度表';

-- 维度表3：商品维度表
CREATE TABLE IF NOT EXISTS dim_product (
    product_id   VARCHAR(10)     PRIMARY KEY COMMENT '商品编号',
    product_name VARCHAR(50)     NOT NULL COMMENT '商品名称',
    category     VARCHAR(20)     NOT NULL COMMENT '商品品类',
    price        DECIMAL(10, 2)  NOT NULL COMMENT '商品单价（元）'
) COMMENT='商品维度表';

-- 维度表4：渠道维度表（用户从哪个渠道来的）
CREATE TABLE IF NOT EXISTS dim_channel (
    channel_id   INT         PRIMARY KEY AUTO_INCREMENT COMMENT '渠道主键',
    channel_name VARCHAR(20) NOT NULL UNIQUE COMMENT '渠道名称'
) COMMENT='渠道维度表';

-- 事实表：用户行为事件事实表（一行一个埋点事件，数据量最大的表）
-- 外键风格关联四张维度表：date_id / user_id / product_id / channel_id
CREATE TABLE IF NOT EXISTS fact_user_event (
    event_id    VARCHAR(12)    PRIMARY KEY COMMENT '事件编号',
    user_id     VARCHAR(10)    NOT NULL COMMENT '用户编号 -> dim_user.user_id',
    product_id  VARCHAR(10)    NOT NULL COMMENT '商品编号 -> dim_product.product_id',
    channel_id  INT            NOT NULL COMMENT '渠道编号 -> dim_channel.channel_id',
    date_id     INT            NOT NULL COMMENT '事件日期 -> dim_date.date_id',
    event_type  VARCHAR(10)    NOT NULL COMMENT '事件类型：view/cart/order/pay',
    event_time  DATETIME       NOT NULL COMMENT '事件发生时间',
    amount      DECIMAL(12, 2) COMMENT '订单/支付金额，浏览和加购事件为 NULL',
    KEY idx_user (user_id),
    KEY idx_date (date_id),
    KEY idx_type (event_type)
) COMMENT='用户行为事件事实表';

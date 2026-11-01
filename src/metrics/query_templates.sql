-- =====================================================================
-- 业务指标 SQL 查询模板（MySQL 8.x 方言）
-- =====================================
-- 约定：日期参数示例统一写 '2026-10-16'，实际使用时替换为目标日期；
--       时间区间统一用 dim_date.full_date 关联，避免手写 date_id。
-- 每个指标都有对应的 pandas 实现（metrics_pandas.py），两者口径一致。
-- =====================================================================

-- 指标1：日活 DAU —— 当天产生过任意行为的去重用户数
SELECT d.full_date AS dt,
       COUNT(DISTINCT f.user_id) AS dau
FROM fact_user_event f
JOIN dim_date d ON d.date_id = f.date_id
WHERE d.full_date = '2026-10-16'
GROUP BY d.full_date;

-- 指标2：PV —— 当天浏览(view)事件总次数（不去重）
SELECT COUNT(*) AS pv
FROM fact_user_event f
JOIN dim_date d ON d.date_id = f.date_id
WHERE d.full_date = '2026-10-16'
  AND f.event_type = 'view';

-- 指标3：新增用户数 —— 当天注册的用户数
SELECT COUNT(*) AS new_users
FROM dim_user
WHERE register_date = '2026-10-16';

-- 指标4：当日下单用户数 / 订单量
SELECT COUNT(DISTINCT user_id) AS order_users,
       COUNT(*)                AS order_count
FROM fact_user_event f
JOIN dim_date d ON d.date_id = f.date_id
WHERE d.full_date = '2026-10-16'
  AND f.event_type = 'order';

-- 指标5：GMV —— 当天支付事件金额之和
SELECT COALESCE(SUM(amount), 0) AS gmv
FROM fact_user_event f
JOIN dim_date d ON d.date_id = f.date_id
WHERE d.full_date = '2026-10-16'
  AND f.event_type = 'pay';

-- 指标6：客单价 AOV —— GMV / 支付用户数（按人去重，不按笔数）
SELECT SUM(amount) / COUNT(DISTINCT user_id) AS aov
FROM fact_user_event f
JOIN dim_date d ON d.date_id = f.date_id
WHERE d.full_date = '2026-10-16'
  AND f.event_type = 'pay';

-- 指标7：当日漏斗（各步骤去重人数；必须按天或短窗口，长窗口会因用户多次访问而失真）
SELECT event_type,
       COUNT(DISTINCT user_id) AS users
FROM fact_user_event f
JOIN dim_date d ON d.date_id = f.date_id
WHERE d.full_date = '2026-10-16'
  AND f.event_type IN ('view', 'cart', 'order', 'pay')
GROUP BY event_type;
-- 步骤转化率在代码里计算：本步人数 / 上一步人数

-- 指标8：浏览-支付整体转化率 —— 区间内支付用户数 / 浏览用户数
SELECT COUNT(DISTINCT CASE WHEN f.event_type = 'pay'  THEN f.user_id END) * 1.0
     / COUNT(DISTINCT CASE WHEN f.event_type = 'view' THEN f.user_id END) AS view_to_pay_rate
FROM fact_user_event f
JOIN dim_date d ON d.date_id = f.date_id
WHERE d.full_date BETWEEN '2026-10-10' AND '2026-10-16';

-- 指标9：次日留存率 —— 当天活跃用户中，第二天仍活跃的占比（MySQL 日期写法）
SELECT COUNT(DISTINCT t1.user_id) * 1.0 / COUNT(DISTINCT t0.user_id) AS d1_retention
FROM fact_user_event t0
JOIN dim_date d0 ON d0.date_id = t0.date_id AND d0.full_date = '2026-10-15'
LEFT JOIN fact_user_event t1
       ON t1.user_id = t0.user_id
      AND t1.date_id = DATE_FORMAT(DATE_ADD(d0.full_date, INTERVAL 1 DAY), '%Y%m%d') + 0;

-- 指标10：7 日留存率（把 INTERVAL 1 DAY 换成 INTERVAL 7 DAY）
SELECT COUNT(DISTINCT t7.user_id) * 1.0 / COUNT(DISTINCT t0.user_id) AS d7_retention
FROM fact_user_event t0
JOIN dim_date d0 ON d0.date_id = t0.date_id AND d0.full_date = '2026-10-09'
LEFT JOIN fact_user_event t7
       ON t7.user_id = t0.user_id
      AND t7.date_id = DATE_FORMAT(DATE_ADD(d0.full_date, INTERVAL 7 DAY), '%Y%m%d') + 0;

-- 指标11：各渠道活跃用户数与 GMV（区间）
SELECT c.channel_name,
       COUNT(DISTINCT f.user_id) AS active_users,
       SUM(CASE WHEN f.event_type = 'pay' THEN f.amount ELSE 0 END) AS gmv
FROM fact_user_event f
JOIN dim_channel c ON c.channel_id = f.channel_id
JOIN dim_date d ON d.date_id = f.date_id
WHERE d.full_date BETWEEN '2026-10-10' AND '2026-10-16'
GROUP BY c.channel_name
ORDER BY gmv DESC;

-- 指标12：各品类 GMV 排行（区间）
SELECT p.category,
       SUM(f.amount) AS gmv,
       COUNT(*)      AS pay_count
FROM fact_user_event f
JOIN dim_product p ON p.product_id = f.product_id
JOIN dim_date d ON d.date_id = f.date_id
WHERE d.full_date BETWEEN '2026-10-01' AND '2026-10-16'
  AND f.event_type = 'pay'
GROUP BY p.category
ORDER BY gmv DESC;

-- 指标13：工作日 vs 周末的平均 DAU
SELECT CASE WHEN d.is_weekend = 1 THEN '周末' ELSE '工作日' END AS day_type,
       AVG(x.dau) AS avg_dau
FROM (
    SELECT date_id, COUNT(DISTINCT user_id) AS dau
    FROM fact_user_event
    GROUP BY date_id
) x
JOIN dim_date d ON d.date_id = x.date_id
GROUP BY d.is_weekend;

-- 指标14：复购用户数 —— 区间内支付 >= 2 次的用户
SELECT COUNT(*) AS repeat_pay_users
FROM (
    SELECT user_id
    FROM fact_user_event f
    JOIN dim_date d ON d.date_id = f.date_id
    WHERE d.full_date BETWEEN '2026-10-01' AND '2026-10-16'
      AND f.event_type = 'pay'
    GROUP BY user_id
    HAVING COUNT(*) >= 2
) t;

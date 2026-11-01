# ETL 流程与调度说明

> 对应项目要求：用 Python + SQL 采集清洗多源数据，设计 5 张维度表与事实表，写清 ETL 流程与调度方式。

## 1. 数据源（多源、异构）

| 来源 | 文件 | 格式 | 说明 |
|---|---|---|---|
| 业务数据库导出 | `data/raw/users.csv` | CSV（utf-8-sig） | 用户资料，含重复行、性别/年龄/日期脏数据 |
| 商品服务 API 导出 | `data/raw/products.json` | JSON | 商品信息，含缺失分类、0 元/负价格 |
| 前端埋点日志 | `data/raw/events.csv` | CSV | 用户行为事件 view/cart/order/pay，含重复事件、非法类型、坏时间、渠道中英文混用 |

数据由 `src/data_gen/generate_mock_data.py` 用固定随机种子（42）生成，可复现，时间窗口固定为 2026-07-19 ~ 2026-10-16。

## 2. 数仓模型（星型模型，5 张表）

```
                    dim_date（日期维度）
                          │
dim_user（用户） ── fact_user_event（用户行为事件事实表） ── dim_product（商品）
                          │
                    dim_channel（渠道维度）
```

| 表 | 类型 | 主键 | 粒度（一行代表什么） |
|---|---|---|---|
| dim_date | 维度表 | date_id（YYYYMMDD） | 一天 |
| dim_user | 维度表 | user_id | 一个用户 |
| dim_product | 维度表 | product_id | 一个商品 |
| dim_channel | 维度表 | channel_id | 一个获客渠道 |
| fact_user_event | 事实表 | event_id | 一条埋点事件（浏览/加购/下单/支付） |

DDL 交付物：`src/models/schema_mysql.sql`（MySQL 8.x，老师技术栈版本）、`src/models/schema_sqlite.sql`（本地零安装练习版本），两版结构一致。

## 3. ETL 流程

代码按 E/T/L 三个文件拆开：

| 步骤 | 代码 | 主要逻辑 |
|---|---|---|
| Extract 抽取 | `src/etl/extract.py` | pandas 读 CSV、`json.load` 读 JSON，原样读取不修改 |
| Transform 清洗转换 | `src/etl/transform.py` | 见下方清洗规则；并把渠道名/日期替换为维度表外键，组装事实表 |
| Load 加载 | `src/etl/load.py` | 先 DROP 再按 DDL 建表，`DataFrame.to_sql` 批量写入，入库顺序：先维度后事实 |

**清洗规则（与单元测试一一对应，见 `tests/test_transform.py`）：**

- 用户表：按 `user_id` 去重；性别 `M/male/男` 统一为男，空值为未知；年龄 <10 或 >100 置空后用中位数填补；注册日期兼容 `2026-08-01`、`2026/8/1`、`2026年8月1日` 三种格式，无法解析置 NULL；城市去空格。
- 商品表：缺失分类填"未分类"；0/负价格置空后用品类中位数（兜底全局中位数）填补；按 `product_id` 去重。
- 事件表：按 `event_id` 去重；事件类型只保留 view/cart/order/pay；渠道 `WeChat/douyin/带空格` 统一为标准渠道名；非法时间行丢弃；金额转数值。

**加载策略：全量重刷（Full Refresh）。** 每次运行重建全部表，保证脚本可重复执行、结果幂等。生产环境增量场景一般改为按日期分区追加 + Upsert。

**数据质量校验：** `tests/test_data_quality_db.py` 在入库后检查：表非空、事实表主键唯一、四个外键的参照完整性、事件类型枚举合法、金额非负。

## 4. 调度方式

- 学习项目使用 **APScheduler**（`src/scheduler/run_scheduler.py`）：BlockingScheduler + CronTrigger，每天 02:00（Asia/Shanghai）执行一次 `run_etl()`，`max_instances=1` 防止任务重叠，失败时打印告警（代码中保留了接邮件/钉钉/企微告警的位置）。
- Windows 上长期运行可用 `python -m src.scheduler.run_scheduler` 挂一个命令行窗口，或注册为"任务计划程序"定时任务；Linux 上可用 systemd / crontab。
- 公司生产环境的对应方案是 **Airflow / DolphinScheduler**：把 E/T/L 拆成 DAG 节点管理依赖、重试过数、超时告警、数据质量卡点，本项目的函数拆分方式就是为迁移到 DAG 做准备。

## 5. 运行方式

```bash
pip install -r requirements.txt          # 安装依赖
python -m src.data_gen.generate_mock_data  # ① 生成原始数据
python -m src.etl.run_etl --gen            # ② 重生成数据并跑 ETL（或不加 --gen 只跑 ETL）
python -m src.scheduler.run_scheduler      # ③ 启动每日调度（可选）
python run.py                              # 一键：造数 → ETL → 指标
```

切换 MySQL：复制 `.env.example` 为 `.env`，把 `DB_URL` 改成 `mysql+pymysql://...`，先执行 `src/models/schema_mysql.sql` 建库建表，其余代码不变。

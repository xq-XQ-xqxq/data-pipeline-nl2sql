# 数据分析智能体与轻量数据管道

这是一个数据开发方向的个人项目，完整实现了一条从数据采集到智能查询的链路：从多源数据采集清洗入仓，到业务指标计算，再到接入大模型实现自然语言查数，让不会写 SQL 的人也能用日常语言获取数据。

技术上用的是 Python、pandas、SQL，数据库默认用 SQLite（不用装东西就能跑），也支持换成 MySQL。大模型接的是 DeepSeek，通义千问也能用。

## 项目大概干了什么

三块内容：

1. 数据采集和建模
   造了 CSV 和 JSON 两种格式的源数据（故意留了脏数据），写了 ETL 脚本把数据洗干净、入仓，建了一个星型模型，四张维度表（日期、用户、商品、渠道）加一张用户行为事实表。用 APScheduler 做了定时调度，每天凌晨自动跑一次。

2. 指标计算
   用 SQL 和 pandas 各写了一遍，一共 14 个指标：日活、次日/7 日留存、漏斗转化、GMV、客单价、渠道对比、品类排行这些。都整理进了指标字典，SQL 也有模板，改个日期就能复用。

3. 自然语言查数（NL2SQL）
   接入大模型，用户输入一句话，系统自动生成 SQL，经过合法性校验后执行，再把结果翻译成人话。准备了 30 道题做评估，目前 SQL 都能跑通，结果正确率大概 93%。

另外还写了一组 pytest 用例，主要检查 ETL 的清洗规则对不对、生成的 SQL 安不安全（不能有删改操作）、以及入库后的数据完整性（主键唯一、外键能对上、枚举值在范围内）。

## 目录结构

```
数据开发项目/
├── config/settings.py        # 数据库、大模型、路径等配置
├── src/
│   ├── data_gen/             # 造多源模拟数据（含脏数据）
│   ├── etl/                  # 抽取、清洗、加载
│   ├── models/               # 建表 DDL，以及给大模型看的表结构
│   ├── metrics/              # SQL 模板 + pandas 指标实现
│   ├── nl2sql/               # 大模型调用、SQL 校验、问答编排
│   └── scheduler/            # 定时调度
├── eval/questions.json       # 30 道评估题和参考 SQL
├── tests/                    # pytest 数据质量校验
├── docs/                     # ETL 流程说明、指标字典
├── requirements.txt
├── .env.example              # 配置模板，复制成 .env 再填
└── run.py                    # 入口
```

## 怎么跑起来

环境需要 Python 3.10 以上。

先装依赖：

```bash
pip install -r requirements.txt
```

然后把配置模板复制一份：

```bash
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env
```

打开 `.env`，主要填大模型的 key：

```env
DB_URL=sqlite:///data/warehouse/warehouse.db

LLM_API_KEY=sk-你的key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

key 去 [DeepSeek 开放平台](https://platform.deepseek.com) 申请就行。如果暂时不填，数据部分（造数、ETL、指标、测试）都能正常跑，只有自然语言查数那部分会用不了。

## 可以用的命令

```bash
python run.py          # 全链路：造数据 → ETL入库 → 算指标
python run.py nl2sql   # 进入交互模式，直接用大白话问数据
python run.py eval     # 跑 30 道评估题，看大模型准不准
python run.py test     # 跑数据质量测试
```

跑 `python run.py` 之后会生成：
- `data/raw/` 下三份源数据
- `data/warehouse/warehouse.db` 数仓文件，5 张表，大概 16 万条事件
- `outputs/` 下 7 个指标结果 CSV

进 `nl2sql` 交互后可以这么问：

```
你> 2026-10-16 的日活是多少？
你> 各渠道的支付 GMV 分别是多少？
你> 女性用户的平均年龄是多少？
你> 10月上半月GMV最高的三个品类是什么？
```

系统会把生成的 SQL、执行结果、还有人话解释一起打印出来。

## 换成 MySQL

项目默认用 SQLite 是为了方便，也支持 MySQL。先在 MySQL 里建个库：

```sql
CREATE DATABASE dw_demo DEFAULT CHARSET utf8mb4;
```

然后把 `.env` 里的 `DB_URL` 改成：

```env
DB_URL=mysql+pymysql://root:你的密码@localhost:3306/dw_demo?charset=utf8mb4
```

其他代码不用动，重新跑 `python run.py` 就行。

## 一些实现上的考虑

- 数仓用星型模型，事实表 `fact_user_event` 关联四张维度表。
- ETL 每次都是全量重刷（先删后建），脚本可以反复跑，结果一致。
- 大模型生成的 SQL 会过五重校验：只能单条、只能查、不能含删改关键字、只能访问指定的表、自动加 LIMIT 100，避免误操作。
- 随机种子固定成 42，每次生成的数据一样，方便对比和回归。

## 常见问题

**没填大模型 key 能跑吗？**
能。数据部分和测试都不依赖 key，只有 `nl2sql` 和 `eval` 需要。

**评估正确率为什么不是 100%？**
目前 28/30，错的那两道其实 SQL 逻辑没问题，是结果集比对的时候形状不一样（比如模型输出成一行多列，参考答案是多行一列），或者浮点并列时 LIMIT 取的行顺序不同。

**能换别的大模型吗？**
可以，改 `.env` 里的 `LLM_BASE_URL` 和 `LLM_MODEL` 就行，走的是 OpenAI 兼容协议。比如通义千问用 `https://dashscope.aliyuncs.com/compatible-mode/v1`，模型选 `qwen-plus`。

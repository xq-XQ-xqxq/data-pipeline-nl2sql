# 数据分析智能体与轻量数据管道

一个用于补齐数据开发链路的学习项目：从**多源采集清洗**到**指标计算**，再到接入大模型的**自然语言查数（NL2SQL）**，把 AI 能力接到数据侧。

---

## 技术栈

Python · SQL · pandas · MySQL（默认 SQLite 零安装）· 大模型 API（DeepSeek / 通义千问）

---

## 项目能做什么

| 模块 | 能力 |
|---|---|
| 数据采集与建模 | 从 CSV / JSON 多源采集，清洗脏数据，入仓建立星型模型（4 张维度表 + 1 张事实表），每日自动调度 ETL |
| 指标与查询 | 用 SQL 与 pandas 实现 14 个业务指标（日活、留存、转化漏斗、GMV、客单价等），输出指标字典与查询模板 |
| LLM 数据问答 | 接入大模型实现 NL2SQL：表结构注入 → SQL 合法性校验 → 执行 → 人话解释，30 题评估准确率 93.3% |

**有 vs 没有的区别**：把"散落各处的脏数据、口径混乱的指标、查数要找分析师"变成"统一数仓、标准化指标、业务方用自然语言秒级自助查数"。

---

## 目录结构

```
数据开发项目/
├── config/settings.py        # 全局配置（数据库、大模型、路径）
├── src/
│   ├── data_gen/             # 多源模拟数据生成（含故意构造的脏数据）
│   ├── etl/                  # Extract 抽取 / Transform 清洗 / Load 加载
│   ├── models/               # 建表 DDL + 表结构元数据（注入大模型用）
│   ├── metrics/              # SQL 查询模板 + pandas 指标实现
│   ├── nl2sql/               # LLM 调用 / SQL 校验 / 问答编排
│   └── scheduler/            # APScheduler 定时调度
├── eval/questions.json       # 30 道 NL2SQL 评估题（含参考 SQL）
├── tests/                    # 数据质量校验（pytest：清洗规则/SQL 安全/库级完整性）
├── docs/                     # ETL 流程说明 + 指标字典
├── requirements.txt
├── .env.example              # 配置模板（复制为 .env 后填 key）
└── run.py                    # 一键入口
```

---

## 快速开始（从零运行）

### 1. 克隆仓库

```bash
git clone <你的仓库地址>
cd 数据开发项目
```

### 2. 环境要求

- Python **3.10** 及以上
- pip

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

复制配置模板：

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

编辑 `.env`：

```env
# 数据库：默认用 SQLite，零安装即可体验
DB_URL=sqlite:///data/warehouse/warehouse.db

# 大模型（NL2SQL 模块需要）
LLM_API_KEY=sk-你的API_KEY
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

> 大模型 Key 可去 [DeepSeek 开放平台](https://platform.deepseek.com) 申请。如果暂时不填，数据侧（ETL+指标）仍可正常运行，只有 NL2SQL 问答和评估会跳过。

### 5. 运行数据全链路（造数 → ETL → 指标）

```bash
python run.py
```

成功后会看到：

- `data/raw/` 生成 3 份多源数据（含脏数据）
- `data/warehouse/warehouse.db` 生成 SQLite 数仓（5 张表，约 16.6 万行事件）
- `outputs/` 生成 7 份指标 CSV（漏斗、渠道、留存、品类 GMV 等）

### 6. 体验自然语言查数

```bash
python run.py nl2sql
```

出现 `你>` 提示符后直接提问，例如：

```
你> 2026-10-16 的日活是多少？
你> 各渠道的支付 GMV 分别是多少？
你> 女性用户的平均年龄是多少？
你> 10月上半月GMV最高的三个品类是什么？
```

系统会自动：生成 SQL → 校验 → 执行 → 用人话解释结果。

### 7. 运行 30 题评估

```bash
python run.py eval
```

输出 SQL 可执行率与结果正确率，详细对拍报告写入 `outputs/eval_report.csv`。

### 8. 数据质量校验

```bash
python run.py test
```

对 ETL 产出做 24 项校验（清洗规则、SQL 安全、主键/外键/值域完整性）。

---

## 切换到 MySQL

老师技术栈要求 MySQL，切到 MySQL 只需两步：

1. 在 MySQL 中建库：

```sql
CREATE DATABASE dw_demo DEFAULT CHARSET utf8mb4;
```

2. 修改 `.env`：

```env
DB_URL=mysql+pymysql://root:你的密码@localhost:3306/dw_demo?charset=utf8mb4
```

代码无需改动，重新 `python run.py` 即可（建表 DDL 会自动选用 MySQL 方言）。

---

## 一键入口速查

| 命令 | 作用 |
|---|---|
| `python run.py` | 造数 + ETL + 指标计算 |
| `python run.py nl2sql` | 自然语言查数（交互模式） |
| `python run.py eval` | 跑 30 题评估，输出准确率 |
| `python run.py test` | 数据质量校验（pytest） |

---

## 核心设计要点

- **星型模型**：`fact_user_event` 事实表关联 `dim_date` / `dim_user` / `dim_product` / `dim_channel` 四张维度表。
- **ETL 全量重刷**：每次执行 DROP + 重建，保证脚本幂等、结果可复现。
- **SQL 安全校验五重关**：单语句、只读、关键字黑名单、表白名单、自动 `LIMIT 100`，杜绝误删库。
- **固定随机种子**：`RANDOM_SEED=42`，每次生成数据完全一致，便于评估与回归。

---

## 常见问题

**Q：没配大模型 key 能跑吗？**
A：能。`python run.py`（数据侧）和 `python run.py test` 都不依赖 key。只有 `nl2sql` 和 `eval` 需要。

**Q：评估正确率为什么不是 100%？**
A：目前 28/30 = 93.3%。两题"不一致"是评估器比对粒度导致：模型用横向透视（1 行多列）而参考 SQL 用纵向（多行），或浮点并列时 `LIMIT 3` 取行顺序不同，SQL 逻辑本身是对的。

**Q：可以换别的大模型吗？**
A：可以。改 `.env` 里的 `LLM_BASE_URL` 和 `LLM_MODEL` 即可，项目用 OpenAI 兼容协议。例如通义千问：`LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`，`LLM_MODEL=qwen-plus`。

---

## 验证状态

- ETL 入库：165,940 行事件 / 5 张表 ✅
- 数据质量测试：24 passed ✅
- 30 题评估：SQL 可执行率 100%，结果正确率 93.3% ✅

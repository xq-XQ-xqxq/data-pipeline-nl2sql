# -*- coding: utf-8 -*-
"""
ETL 第 3 步：Load（加载入库）
==============================

策略：全量重刷（Full Refresh）。
练习项目数据量小，每次加载先 DROP 再按 DDL 重建，保证脚本可以反复执行、结果幂等。
真实公司里增量场景会改成按分区追加 + 数据质量校验。
"""
from sqlalchemy import create_engine, text

from config.settings import DB_DIALECT, DB_URL, DDL_DIR, WAREHOUSE_DIR

# 入库顺序：先维度后事实（虽然练习库没建外键约束，保持好习惯）
TABLE_ORDER = ["dim_date", "dim_channel", "dim_user", "dim_product", "fact_user_event"]


def get_engine():
    """创建数据库引擎；SQLite 时自动确保数据库目录存在。"""
    if DB_DIALECT == "sqlite":
        WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
    return create_engine(DB_URL, future=True)


def _split_sql(sql_text: str) -> list[str]:
    """把 DDL 文件按分号拆成可执行的单条语句，顺便去掉整行注释。"""
    lines = [ln for ln in sql_text.splitlines() if not ln.strip().startswith("--")]
    statements = " \n".join(lines).split(";")
    return [s.strip() for s in statements if s.strip()]


def recreate_tables(engine) -> None:
    """先删后建：保证整库结构与 DDL 文件严格一致。"""
    ddl_file = DDL_DIR / (
        "schema_mysql.sql" if DB_DIALECT == "mysql" else "schema_sqlite.sql"
    )
    sql_text = ddl_file.read_text(encoding="utf-8")

    with engine.begin() as conn:
        # 先删表
        for table in reversed(TABLE_ORDER):
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        # 再按 DDL 建表
        for stmt in _split_sql(sql_text):
            conn.execute(text(stmt))


def load_all(tables: dict) -> None:
    """把转换好的 5 个 DataFrame 写入数据库。"""
    engine = get_engine()
    recreate_tables(engine)

    # to_sql = pandas 封装好的批量 INSERT；append 表示表已建好只追加数据。
    # 分批提交（每批 1000 行）：避免 SQLite 单条语句变量数超限，也避免大事务过长。
    with engine.begin() as conn:
        for table in TABLE_ORDER:
            df = tables[table]
            df.to_sql(table, con=conn, if_exists="append", index=False, chunksize=1000)
    engine.dispose()

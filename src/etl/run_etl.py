# -*- coding: utf-8 -*-
"""
ETL 总入口：抽取 -> 清洗转换 -> 加载入库

命令行运行：
    python -m src.etl.run_etl            # 正常跑一遍
    python -m src.etl.run_etl --gen      # 先重新生成模拟数据，再跑 ETL

调度器（src/scheduler/run_scheduler.py）每天调用的也是这里的 run_etl()。
"""
import sys

from src.etl.extract import extract_all
from src.etl.load import load_all
from src.etl.transform import transform_all


def run_etl() -> dict:
    """执行完整 ETL，返回每张表的行数（供调度日志 / 数据质量校验使用）。"""
    print("[1/3] 抽取原始数据 ...")
    raw = extract_all()
    print(f"      users={len(raw['users'])}  products={len(raw['products'])}  events={len(raw['events'])}")

    print("[2/3] 清洗转换 ...")
    tables = transform_all(raw)

    print("[3/3] 全量重刷入库 ...")
    load_all(tables)

    counts = {name: len(df) for name, df in tables.items()}
    for name, cnt in counts.items():
        print(f"      {name:<18}{cnt:>8} 行")
    print("ETL 完成。")
    return counts


def main() -> None:
    if "--gen" in sys.argv:
        from src.data_gen.generate_mock_data import main as gen_main
        gen_main()
    run_etl()


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
项目一键入口
============

在项目根目录执行：
    python run.py              # 生成模拟数据 -> ETL入库 -> 计算指标（全流程）
    python run.py nl2sql       # 进入自然语言查数（需要先在 .env 配好大模型 key）
    python run.py eval         # 跑 30 条 NL2SQL 评估题（需要大模型 key）
    python run.py test         # 运行 pytest 数据质量测试

分步骤运行也可以：
    python -m src.data_gen.generate_mock_data
    python -m src.etl.run_etl --gen
    python -m src.metrics.run_metrics
"""
import sys


def run_pipeline() -> None:
    """数据侧主链路：造数 -> ETL -> 指标。"""
    from src.data_gen.generate_mock_data import main as gen_main
    from src.etl.run_etl import run_etl
    from src.metrics.run_metrics import main as metrics_main

    print("=" * 60)
    print("第 1 步：生成多源模拟数据")
    print("=" * 60)
    gen_main()

    print("=" * 60)
    print("第 2 步：ETL（抽取-清洗-加载）")
    print("=" * 60)
    run_etl()

    print("=" * 60)
    print("第 3 步：计算业务指标")
    print("=" * 60)
    metrics_main()


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"

    if cmd == "all":
        run_pipeline()
    elif cmd == "nl2sql":
        from src.nl2sql.chat import main as chat_main
        chat_main()
    elif cmd == "eval":
        from eval.run_eval import main as eval_main
        eval_main()
    elif cmd == "test":
        import pytest
        sys.exit(pytest.main(["-v", "tests"]))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

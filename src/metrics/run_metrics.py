# -*- coding: utf-8 -*-
"""
指标计算入口：把全部指标结果输出到 outputs/ 目录（CSV，可用 Excel 打开）。

运行：python -m src.metrics.run_metrics
"""
from config.settings import OUTPUT_DIR
from src.metrics.metrics_pandas import calc_all


def main() -> None:
    results = calc_all()
    print(f"指标计算完成，结果写入 {OUTPUT_DIR}")
    print("-" * 60)

    for name, df in results.items():
        path = OUTPUT_DIR / f"{name}.csv"
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"{name:<20}{len(df):>5} 行  -> {path.name}")

    # 在控制台展示几个最常面试的指标结果
    print("-" * 60)
    funnel = results["funnel"]
    print("整体漏斗：")
    print(funnel.to_string(index=False))
    print("-" * 60)
    print("渠道汇总：")
    print(results["channel_summary"].to_string(index=False))


if __name__ == "__main__":
    main()

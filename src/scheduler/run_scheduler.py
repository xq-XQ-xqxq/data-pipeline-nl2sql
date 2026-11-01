# -*- coding: utf-8 -*-
"""
轻量调度器
==========

用 APScheduler 每天凌晨 2:00 自动跑一遍 ETL（全量重刷昨天/最近的数据）。

运行：python -m src.scheduler.run_scheduler
停止：在命令行窗口按 Ctrl + C

说明：这是学习项目里的“轻量调度方式”。公司里大数据量场景通常换成
Airflow / DolphinScheduler，按 DAG 管理任务依赖、失败重试和告警，
思路完全一样：定时触发 -> 跑 ETL -> 失败告警。
"""
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.etl.run_etl import run_etl


def job_daily_etl() -> None:
    """每天执行的 ETL 任务：成功打印行数，失败抛出异常（可在此接邮件/钉钉告警）。"""
    try:
        counts = run_etl()
        print(f"[调度] 今日 ETL 成功：{counts}")
    except Exception as e:  # noqa: BLE001
        # 练习：把错误打到控制台；真实项目这里接告警（邮件/钉钉/企微）
        print(f"[调度][告警] ETL 执行失败：{e}")
        raise


def main() -> None:
    scheduler = BlockingScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        job_daily_etl,
        trigger=CronTrigger(hour=2, minute=0),  # 每天 02:00
        id="daily_etl",
        max_instances=1,
        coalesce=True,
    )
    print("调度器已启动：每天 02:00 执行 ETL，按 Ctrl+C 退出。")
    print("（提示：想马上试跑一次，请用 python -m src.etl.run_etl）")
    scheduler.start()


if __name__ == "__main__":
    main()

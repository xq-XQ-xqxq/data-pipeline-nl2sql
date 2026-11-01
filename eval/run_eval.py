# -*- coding: utf-8 -*-
"""
NL2SQL 30 题批量评估
====================

评估方法（结果集比对，大模型应用测试的常见做法）：
  对每道题：
    1. 执行人工编写的参考 SQL，得到“标准答案结果集”
    2. 走完整 NL2SQL 链路得到大模型 SQL 的结果集
    3. 两边做无序多重集合比对（数字统一保留两位小数）

统计三个指标：
  - 可执行率：SQL 通过校验且成功执行的比例
  - 结果正确率：结果集与参考完全一致的比例
  - 平均每题耗时

详细对拍结果输出到 outputs/eval_report.csv，方便分析失败 case、回归对比。

运行：python run.py eval
"""
import json
import time
from decimal import Decimal

from config.settings import OUTPUT_DIR
from src.nl2sql.chat import answer_question
from src.nl2sql.db import run_query

QUESTIONS_PATH = OUTPUT_DIR.parent / "eval" / "questions.json"


def normalize_value(v) -> str:
    """把数据库返回值规范成可比较的字符串：数字保留 2 位，空值统一，日期转字符串。"""
    if v is None:
        return "<NULL>"
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float, Decimal)):
        return f"{float(v):.2f}"
    return str(v).strip()


def normalize_rows(rows: list[tuple]) -> list[tuple[str, ...]]:
    return sorted(tuple(normalize_value(v) for v in row) for row in rows)


def main() -> None:
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    reports = []
    executable = 0
    correct = 0
    start_all = time.time()

    for item in questions:
        qid, question, ref_sql = item["id"], item["question"], item["reference_sql"]
        print(f"[{qid:>2}/{len(questions)}] {question}")

        # 参考 SQL 是人工写的可信 SQL，直接执行
        try:
            _, ref_rows = run_query(ref_sql)
            ref_norm = normalize_rows(ref_rows)
        except Exception as e:  # noqa: BLE001
            print(f"      参考 SQL 执行失败，请检查题目：{e}")
            continue

        t0 = time.time()
        r = answer_question(question, need_explain=False)
        cost = round(time.time() - t0, 2)

        is_correct = False
        if r["valid"]:
            executable += 1
            is_correct = normalize_rows(r["rows"]) == ref_norm
            correct += int(is_correct)

        status = "正确" if is_correct else ("可执行但结果不一致" if r["valid"] else "失败")
        print(f"      -> {status}（{cost}s）" + ("" if is_correct else f"  原因：{r['error']}"))

        reports.append({
            "id": qid,
            "category": item["category"],
            "question": question,
            "generated_sql": r["sql"],
            "status": status,
            "error": r["error"],
            "cost_seconds": cost,
        })

    total = len(reports)
    print("\n" + "=" * 60)
    print(f"评估完成：共 {total} 题，总耗时 {round(time.time() - start_all, 1)}s")
    print(f"SQL 可执行率：{executable}/{total} = {executable / total:.1%}")
    print(f"结果正确率：  {correct}/{total} = {correct / total:.1%}")
    print("=" * 60)

    # 落盘报告（CSV 便于用 Excel 逐题分析，JSON 便于程序读取做回归对比）
    import csv
    report_csv = OUTPUT_DIR / "eval_report.csv"
    with open(report_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f, fieldnames=["id", "category", "question", "generated_sql", "status", "error", "cost_seconds"]
        )
        writer.writeheader()
        writer.writerows(reports)

    summary = {
        "total": total,
        "executable": executable,
        "correct": correct,
        "executable_rate": round(executable / total, 4),
        "accuracy": round(correct / total, 4),
    }
    (OUTPUT_DIR / "eval_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"详细报告：{report_csv}")


if __name__ == "__main__":
    main()

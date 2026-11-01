# -*- coding: utf-8 -*-
"""
自然语言查数（NL2SQL）主链路
============================

完整流程（对应老师要求的三点：表结构注入 / SQL 合法性校验 / 结果解释）：

    用户问题
       │
       ├─ 1. 调大模型生成 SQL（Prompt 中已注入表结构）
       ├─ 2. 安全校验（只读、表白名单、单语句、自动 LIMIT）
       ├─ 3. 执行查询拿到结果
       └─ 4. 再调大模型，把结果解释成人话

运行方式：
    python run.py nl2sql                       # 交互模式
    python -m src.nl2sql.chat "昨天的日活是多少"  # 单问模式
"""
import sys

from src.nl2sql import llm
from src.nl2sql.db import run_query
from src.nl2sql.validator import validate_sql


def answer_question(question: str, need_explain: bool = True) -> dict:
    """核心编排函数；评估脚本也复用它。

    返回 dict：valid / sql / columns / rows / answer / error
    """
    result = {"question": question, "valid": False, "sql": "",
              "columns": [], "rows": [], "answer": "", "error": ""}

    # 1) 生成 SQL
    try:
        sql = llm.generate_sql(question)
    except Exception as e:  # noqa: BLE001
        result["error"] = f"大模型调用失败：{e}"
        return result
    result["sql"] = sql

    # 2) 校验 SQL
    ok, safe_sql, reason = validate_sql(sql)
    if not ok:
        result["error"] = f"SQL 校验未通过：{reason}"
        return result
    result["sql"] = safe_sql

    # 3) 执行查询
    try:
        columns, rows = run_query(safe_sql)
    except Exception as e:  # noqa: BLE001
        result["error"] = f"SQL 执行失败：{e}"
        return result
    result["columns"], result["rows"] = columns, rows
    result["valid"] = True

    # 4) 结果解释（评估时可以关掉，省 token）
    if need_explain:
        try:
            result["answer"] = llm.explain_result(question, safe_sql, columns, rows)
        except Exception as e:  # noqa: BLE001
            result["answer"] = f"（结果已查到，但解释失败：{e}）"

    return result


def _print_result(r: dict) -> None:
    if r["error"]:
        print(f"\n[出错] {r['error']}")
        print(f"[模型生成的SQL] {r['sql']}")
        return
    print(f"\n[生成并通过校验的 SQL]\n{r['sql']}")
    print(f"\n[查询结果] 共 {len(r['rows'])} 行")
    for row in r["rows"][:20]:
        print("  ", row)
    if r["answer"]:
        print(f"\n[大模型解释]\n{r['answer']}")


def main() -> None:
    # 单问模式：python -m src.nl2sql.chat "你的问题"
    if len(sys.argv) > 1:
        _print_result(answer_question(" ".join(sys.argv[1:])))
        return

    # 交互模式
    print("=" * 60)
    print("自然语言查数：输入业务问题，回车查数；输入 q 退出")
    print("例如：2026-10-16 的日活是多少？")
    print("=" * 60)
    while True:
        question = input("\n你的问题> ").strip()
        if question.lower() in ("q", "quit", "exit"):
            break
        if not question:
            continue
        _print_result(answer_question(question))


if __name__ == "__main__":
    main()

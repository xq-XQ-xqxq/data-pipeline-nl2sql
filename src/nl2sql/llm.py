# -*- coding: utf-8 -*-
"""
大模型调用（OpenAI 兼容协议：DeepSeek / 通义千问等都可以）
==========================================================

两个能力：
  generate_sql()  —— 表结构注入，让模型把自然语言翻译成 SQL
  explain_result() —— 把查询结果翻译回人话
"""
from openai import OpenAI

from config.settings import DB_DIALECT, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from src.models.schema_meta import SCHEMA_TEXT

SQL_SYSTEM_PROMPT = f"""你是一名严谨的数据分析师。请根据给定的表结构，把用户的中文问题翻译成一条 {DB_DIALECT.upper()} 查询 SQL。

{SCHEMA_TEXT}

硬性要求：
1. 只能输出一条可直接执行的 SQL，不要任何解释、不要 markdown 代码块标记。
2. 只能使用上面给出的表和字段，禁止编造表名、字段名。
3. 只能写只读查询（SELECT / WITH），禁止任何增删改操作。
4. 涉及日期条件时用 dim_date.full_date 关联，日期字符串格式为 'YYYY-MM-DD'。
5. 查询结果默认加 LIMIT 100；统计“数量/金额”时请给出清晰的英文列别名。
"""

EXPLAIN_SYSTEM_PROMPT = """你是一名数据分析助手。用户用中文提出了业务问题，系统执行 SQL 得到了结果。
请基于结果用简洁的中文回答用户的问题：直接给结论，必要时补充 1-2 句解读。
如果结果为空，就如实说明没有查到数据，不要编造数字。"""


def get_client() -> OpenAI | None:
    """没配 API Key 时返回 None，上层据此给出友好提示。"""
    if not LLM_API_KEY or "请在这里填" in LLM_API_KEY:
        return None
    return OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=60)


def _chat(client: OpenAI, system: str, user: str) -> str:
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,  # 查数场景要稳定，不要创造性发挥
    )
    return resp.choices[0].message.content.strip()


def generate_sql(question: str) -> str:
    """自然语言 -> SQL。"""
    client = get_client()
    if client is None:
        raise RuntimeError(
            "尚未配置大模型 API Key：请复制 .env.example 为 .env，填入 LLM_API_KEY 后重试。"
        )
    return _chat(client, SQL_SYSTEM_PROMPT, question)


def explain_result(question: str, sql: str, columns: list[str], rows: list[tuple]) -> str:
    """问题 + SQL + 结果 -> 中文解释。"""
    client = get_client()
    if client is None:
        raise RuntimeError("尚未配置大模型 API Key，无法解释结果。")

    # 结果最多展示前 20 行，避免超 Token
    preview_rows = rows[:20]
    user_content = (
        f"用户问题：{question}\n\n"
        f"执行的 SQL：{sql}\n\n"
        f"结果列名：{columns}\n"
        f"结果数据（共 {len(rows)} 行，最多展示 20 行）：{preview_rows}"
    )
    return _chat(client, EXPLAIN_SYSTEM_PROMPT, user_content)

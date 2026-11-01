# -*- coding: utf-8 -*-
"""
SQL 合法性 / 安全性校验
=======================

大模型生成的 SQL 不可信，执行前必须过这一关（这也是测试开发关心的输入校验点）：
  1. 只允许一条语句，防止堆叠注入（如 SELECT ...; DROP TABLE ...）
  2. 只允许 SELECT / WITH 开头的只读查询
  3. 关键字黑名单：INSERT/UPDATE/DELETE/DROP 等一律拒绝
  4. 表白名单：只能访问数仓里真实存在的 5 张表
  5. 没有 LIMIT 时自动补 LIMIT 100，防止一次查出全表

说明：这是练习级别的防护（正则方案）。生产级方案会接入数据库只读账号、
SQL 解析器（如 sqlglot）做 AST 校验和权限控制。
"""
import re

from src.models.schema_meta import ALLOWED_TABLES

# 禁止出现的危险关键字（按整词匹配，避免误伤字段名）
FORBIDDEN_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "truncate", "create",
    "replace", "grant", "revoke", "shutdown", "attach", "detach",
    "pragma", "load_file", "outfile", "call", "exec", "execute", "merge",
}

# 提取 FROM / JOIN 后面的表名
_TABLE_RE = re.compile(r"(?:from|join)\s+[`\"\[]?([a-zA-Z_][a-zA-Z0-9_]*)[`\"\]]?", re.IGNORECASE)
# 提取 CTE 临时表名：WITH t AS (...)、WITH RECURSIVE t AS (...)、以及逗号后的 a AS (...)
_CTE_RE = re.compile(r"(?:with|,)\s+(?:recursive\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+as\s*\(", re.IGNORECASE)
_WORD_RE = re.compile(r"[a-zA-Z_]+")
_LIMIT_RE = re.compile(r"\blimit\s+\d+", re.IGNORECASE)

MAX_ROWS = 100


def validate_sql(sql: str) -> tuple[bool, str, str]:
    """校验 SQL。

    返回：(是否通过, 校验后的SQL, 不通过原因)
    """
    if not sql or not sql.strip():
        return False, "", "SQL 为空"

    cleaned = sql.strip().rstrip(";").strip()

    # 1) 只允许一条语句：去掉结尾分号后，中间不能再出现分号
    if ";" in cleaned:
        return False, cleaned, "只允许执行一条 SQL 语句（检测到多余的分号）"

    # 去掉模型偶尔会带的 markdown 代码块标记
    cleaned = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", cleaned).strip()

    # 2) 必须是只读查询
    head = cleaned.split()[0].lower() if cleaned.split() else ""
    if head not in ("select", "with"):
        return False, cleaned, "只允许 SELECT / WITH 开头的只读查询"

    # 3) 危险关键字黑名单
    words = {w.lower() for w in _WORD_RE.findall(cleaned)}
    hit = words & FORBIDDEN_KEYWORDS
    if hit:
        return False, cleaned, f"SQL 中包含禁止的关键字：{', '.join(sorted(hit))}"

    # 4) 表白名单（WITH 里定义的 CTE 临时名允许引用，但必须至少用到一张真实表）
    cte_names = set(_CTE_RE.findall(cleaned))
    tables = set(_TABLE_RE.findall(cleaned))
    unknown = tables - ALLOWED_TABLES - cte_names
    if unknown:
        return False, cleaned, f"SQL 访问了不存在或无权限的表：{', '.join(sorted(unknown))}"
    if not (tables & ALLOWED_TABLES):
        return False, cleaned, "SQL 中没有引用任何数仓表"

    # 5) 自动补 LIMIT，避免大结果集
    if not _LIMIT_RE.search(cleaned):
        cleaned = f"{cleaned} LIMIT {MAX_ROWS}"

    return True, cleaned, ""

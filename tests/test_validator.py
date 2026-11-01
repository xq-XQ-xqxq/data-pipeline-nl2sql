# -*- coding: utf-8 -*-
"""
NL2SQL 安全校验器的单元测试。
这部分是“AI 生成 SQL”的安全护栏，也是测试开发视角最容易讲出东西的测试点。
"""
from src.nl2sql.validator import validate_sql


def test_plain_select_passes():
    ok, sql, reason = validate_sql(
        "SELECT user_id FROM fact_user_event WHERE event_type = 'view'"
    )
    assert ok, reason
    assert sql.upper().endswith("LIMIT 100")  # 自动补 LIMIT


def test_select_with_existing_limit_not_duplicated():
    ok, sql, _ = validate_sql("SELECT * FROM dim_user LIMIT 10")
    assert ok
    assert sql.upper().count("LIMIT") == 1


def test_with_cte_passes():
    ok, _, reason = validate_sql(
        "WITH t AS (SELECT user_id FROM fact_user_event GROUP BY user_id) "
        "SELECT COUNT(*) FROM t"
    )
    assert ok, reason


def test_delete_is_rejected():
    ok, _, reason = validate_sql("DELETE FROM dim_user")
    assert not ok
    assert "只读" in reason


def test_stacked_statement_is_rejected():
    """防 SQL 堆叠注入：SELECT 后面偷偷跟 DROP 必须被拦。"""
    ok, _, reason = validate_sql(
        "SELECT * FROM dim_user; DROP TABLE dim_user"
    )
    assert not ok
    assert "一条" in reason


def test_dangerous_keyword_is_rejected():
    ok, _, reason = validate_sql(
        "SELECT * FROM dim_user WHERE 1=1; UPDATE dim_user SET gender='x'"
    )
    assert not ok  # 堆叠语句先被拦

    ok2, _, reason2 = validate_sql(
        "SELECT * FROM dim_user WHERE gender IN (SELECT gender FROM dim_user) OR 1=(SELECT 1)"
    )
    assert ok2  # 正常子查询不应误伤


def test_unknown_table_is_rejected():
    ok, _, reason = validate_sql("SELECT * FROM mysql.user")
    assert not ok
    assert "无权限" in reason or "不存在" in reason


def test_sql_without_table_is_rejected():
    ok, _, _ = validate_sql("SELECT 1 + 1")
    assert not ok


def test_empty_sql_is_rejected():
    ok, _, _ = validate_sql("   ")
    assert not ok


def test_markdown_fence_is_accepted():
    """模型偶尔会输出 ```sql ... ``` 包裹，清理后应能通过。"""
    ok, sql, reason = validate_sql(
        "```sql\nSELECT COUNT(*) FROM dim_user\n```"
    )
    assert ok, reason
    assert not sql.startswith("```")

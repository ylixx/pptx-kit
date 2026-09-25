#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
checks.py — storyboard 页面的共享校验逻辑。

render_pptx.py 用它产生 [warn]（尽量出产物，不中断）；
verify_pptx.py 用它产生 FAIL（质量把关）。
只依赖标准库，可被两个脚本以同目录模块方式导入。

校验项：
  1. 页面字段（fields / images / chart / charts / table）与版式槽位的匹配
  2. 图表数据：categories / series 长度一致性、数值类型
  3. 表格数据：行结构完整性
"""


def check_chart_spec(spec, prefix=""):
    """校验单个 chart 数据对象，返回问题列表。"""
    issues = []
    if not isinstance(spec, dict):
        return [f"{prefix}chart 数据不是对象"]
    cats = spec.get("categories")
    series = spec.get("series")
    if not isinstance(cats, list):
        issues.append(f"{prefix}categories 缺失或不是数组")
        cats = []
    if not isinstance(series, dict) or not series:
        issues.append(f"{prefix}series 缺失或不是对象")
        series = series or {}
    for name, vals in series.items():
        if not isinstance(vals, list):
            issues.append(f"{prefix}系列 '{name}' 不是数值数组")
            continue
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool)
                   for v in vals):
            issues.append(f"{prefix}系列 '{name}' 含非数值元素")
        if cats and len(vals) != len(cats):
            issues.append(
                f"{prefix}系列 '{name}' 长度 {len(vals)} 与 categories "
                f"长度 {len(cats)} 不一致")
    return issues


def check_table_spec(spec, prefix=""):
    """校验表格数据对象，返回问题列表。"""
    if not isinstance(spec, dict):
        return [f"{prefix}table 数据不是对象"]
    rows = spec.get("rows")
    if not isinstance(rows, list) or not rows:
        return [f"{prefix}rows 缺失或为空"]
    widths = {len(r) for r in rows}
    if len(widths) > 1:
        issues = [f"{prefix}表格各行长度不一致: {sorted(widths)}"]
    else:
        issues = []
    for r, row in enumerate(rows, 1):
        if not isinstance(row, list):
            issues.append(f"{prefix}第 {r} 行不是数组")
    return issues


def page_issues(page, pat):
    """page vs 版式定义(patterns.json 条目) 的完整校验，返回问题列表。

    只做结构性检查（槽位匹配、chart/table 数据），不做字段值长度检查
    （超长告警在 render_pptx 内按 TEXT_LIMITS 做）。
    """
    issues = []
    for key in (page.get("fields") or {}):
        if key not in pat.get("text_slots", {}):
            issues.append(f"未知文本槽位 '{key}'，忽略")
    for key in (page.get("images") or {}):
        if key not in pat.get("image_slots", {}):
            issues.append(f"未知图片槽位 '{key}'，忽略")
    if page.get("chart") is not None and "chart_slot" not in pat:
        issues.append("该版式不支持 chart，忽略")
    if page.get("charts") is not None:
        for key, spec in (page.get("charts") or {}).items():
            if key not in pat.get("chart_slots", {}):
                issues.append(f"未知图表槽位 '{key}'，忽略")
                continue
            issues += check_chart_spec(spec, f"图表槽位 '{key}': ")
    if page.get("chart") is not None and "chart_slot" in pat:
        issues += check_chart_spec(page["chart"], "chart: ")
    if page.get("table") is not None and "table_slot" not in pat:
        issues.append("该版式不支持 table，忽略")
    if page.get("table") is not None and "table_slot" in pat:
        issues += check_table_spec(page["table"], "table: ")
    return issues

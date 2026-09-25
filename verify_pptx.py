#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_pptx.py — 渲染产物自动质检（storyboard + pptx 对照检查）。

用法：
  python3 verify_pptx.py storyboard.json out.pptx

检查项：
  1. 页数一致（storyboard pages == 幻灯片数）
  2. zip 完整性
  3. 模板占位文字零残留（"输入相关/这里可以/小标题/20XX…"）
  4. 每个字段值都能在对应页找到（防槽位错位；未知槽位字段降级为 WARN）
  5. 图表数据（chart/charts）与 storyboard 一致（含长度一致性 FAIL）
  6. 表格数据一致
  7. 每页有 notes 讲稿（缺失仅提示）
退出码：0=通过（允许 WARN），1=存在 FAIL。
"""

import json
import os
import sys
import zipfile

from pptx import Presentation

from checks import check_chart_spec

# 模板占位特征词（误报风险高、过于日常化的词不列入）
LEAK_WORDS = [
    "输入相关", "这里可以", "这里输入", "请输入", "这里是标题",
    "输入对应", "点击图片", "输入关键词", "小标题", "20XX",
    "千阳", "广财", "如何更换", "人物姓名", "xxxx",
]


def fail(msg):
    print(f"  ❌ FAIL: {msg}")
    return 1


def warn(msg):
    print(f"  ⚠️ WARN: {msg}")
    return 0


def all_texts(shape_holder, out):
    for sh in shape_holder.shapes:
        if sh.has_text_frame:
            out.append(sh.text_frame.text)
        if getattr(sh, "has_table", False) and sh.has_table:
            for r in range(len(sh.table.rows)):
                for c in range(len(sh.table.columns)):
                    out.append(sh.table.cell(r, c).text_frame.text)


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    sb = json.load(open(sys.argv[1], encoding="utf-8"))
    pptx_path = sys.argv[2]
    errors = warnings = 0

    # 可选加载 patterns.json：字段白名单（存在则未知槽位字段降级为 WARN）
    _here = os.path.dirname(os.path.abspath(__file__))
    _pat_path = os.path.join(_here, "patterns.json")
    patterns = None
    if os.path.exists(_pat_path):
        patterns = {k: v for k, v in
                    json.load(open(_pat_path, encoding="utf-8")).items()
                    if not k.startswith("_")}

    with zipfile.ZipFile(pptx_path) as z:
        if z.testzip() is not None:
            errors += fail("pptx zip 结构损坏")

    prs = Presentation(pptx_path)
    pages = sb["pages"]

    # 1. 页数
    if len(prs.slides) != len(pages):
        errors += fail(f"页数不一致: storyboard {len(pages)} 页 vs pptx {len(prs.slides)} 页")
    else:
        print(f"  ✅ 页数一致（{len(pages)} 页）")

    for idx, (page, slide) in enumerate(zip(pages, prs.slides), 1):
        pid = page.get("pattern", "?")
        pat = patterns.get(pid) if patterns else None
        texts = []
        all_texts(slide, texts)

        # 3. 占位残留
        for t in texts:
            for w in LEAK_WORDS:
                if w in t.lower():
                    errors += fail(f"第{idx}页 [{pid}] 模板占位文字残留: …{t[:24]}…")
                    break

        # 4. 字段对位（有白名单时，未知槽位字段只提示不判 FAIL）
        for k, v in (page.get("fields") or {}).items():
            if v is None or v == "":
                continue
            if pat is not None and k not in pat.get("text_slots", {}):
                warnings += warn(f"第{idx}页 [{pid}] 字段 {k} 不在版式 text_slots 中（输入问题，非产物问题）")
                continue
            if not any(str(v) in t for t in texts):
                errors += fail(f"第{idx}页 [{pid}] 字段 {k}={str(v)[:14]!r} 未落到页面")

        # 5. 图表数据
        chart_specs = {}
        if page.get("chart"):
            chart_specs["__single__"] = page["chart"]
        chart_specs.update(page.get("charts") or {})
        if chart_specs:
            # 5a. 数据长度/类型一致性（输入侧把关，直接 FAIL）
            for key, spec in chart_specs.items():
                for issue in check_chart_spec(spec, f"图表 {key} "):
                    errors += fail(f"第{idx}页 [{pid}] {issue}")
            # 5b. 产物侧：渲染出的图表数据应命中 storyboard 期望
            try:
                got = []
                for sh in slide.shapes:
                    if getattr(sh, "has_chart", False) and sh.has_chart:
                        ch = sh.chart
                        got.append((list(ch.plots[0].categories),
                                    {s.name: [round(float(x), 6) for x in s.values]
                                     for s in ch.series}))
                for key, spec in chart_specs.items():
                    want = (list(spec["categories"]),
                            {n: [round(float(x), 6) for x in v]
                             for n, v in spec["series"].items()})
                    if want not in got:
                        errors += fail(f"第{idx}页 [{pid}] 图表 {key} 数据不匹配")
            except Exception as e:
                errors += fail(f"第{idx}页 [{pid}] 读取产物图表数据失败: {e}")

        # 6. 表格数据
        if page.get("table"):
            want = [[str(c) for c in row] for row in page["table"]["rows"]]
            matched = False
            for sh in slide.shapes:
                if getattr(sh, "has_table", False) and sh.has_table:
                    t = sh.table
                    got = [[t.cell(r, c).text_frame.text
                            for c in range(len(t.columns))]
                           for r in range(len(t.rows))]
                    if all(got[r][c] == want[r][c]
                           for r in range(len(want))
                           for c in range(len(want[r]))):
                        matched = True
            if not matched:
                errors += fail(f"第{idx}页 [{pid}] 表格数据不匹配")

        # 7. notes
        if not page.get("notes"):
            warnings += 1
            warn(f"第{idx}页 [{pid}] 无讲稿 notes")

    print(f"\n{'✅ 质检通过' if errors == 0 else '❌ 质检未通过'}"
          f"（{errors} 项失败 / {warnings} 项提醒）")
    sys.exit(0 if errors == 0 else 1)


if __name__ == "__main__":
    main()

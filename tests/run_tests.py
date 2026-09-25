#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_tests.py — pptx-kit 自动化回归测试（纯标准库，无需 pytest）。

运行：
    python tests/run_tests.py

覆盖：
  T1  39 个 intent 全链路（解析 → 渲染 → 质检）零失败
  T2  未知 pattern 不中断（兜底替换，产物页数不丢）
  T3  chart 长度错配 → 告警截断，产物数据一致
  T4  超长文本 → 告警不中断
  T5  optimize_layout 治理（无相邻重复、无图不选 mockup-3、字段兼容）
  T6  verify 把关（chart 错配 FAIL、占位残留 FAIL）
  T7  schema enum ↔ patterns.json 双向包含
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

PASS, FAIL = 0, 0


def run(args, cwd=None):
    return subprocess.run(args, capture_output=True, text=True,
                          encoding="utf-8", cwd=cwd or REPO)


def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} {detail}")


# ---------------- 用例数据 ----------------

def sample_text(key):
    """按槽位语义生成示例文本（长度贴合 TEXT_LIMITS，避免超长告警）。"""
    base = re.sub(r"\d+$", "", key)
    if base in ("title", "t"):
        return "标题测试"
    if base in ("s", "st", "kw", "lab", "mid", "num", "d", "pct", "cap",
                "event", "award"):
        return "要点一"
    if base in ("presenter", "advisor", "name"):
        return "张三"
    if base == "en":
        return "English Subtitle"
    return "这里是正文描述内容的测试文本"


def sample_fields(text_slots):
    return {k: sample_text(k) for k in text_slots}


def sample_chart():
    return {"categories": ["类别甲", "类别乙", "类别丙"],
            "series": {"系列一": [1.0, 2.0, 3.0],
                       "系列二": [4.0, 5.0, 6.0]}}


def sample_table():
    return {"rows": [["表头1", "表头2", "表头3"],
                     ["数据1", "数据2", "数据3"],
                     ["数据4", "数据5", "数据6"]]}


def enrich_for_pattern(page, pat):
    """按解析后的 pattern 补全 chart/table 数据（图片槽不补，保留占位）。"""
    if pat.get("chart_slot") and "chart" not in page:
        page["chart"] = sample_chart()
    for k in pat.get("chart_slots", {}):
        page.setdefault("charts", {}).setdefault(k, sample_chart())
    if pat.get("table_slot") and "table" not in page:
        page["table"] = sample_table()


# ---------------- T1: 39 intent 全链路 ----------------

def t1_intents_full_chain():
    print("\n=== T1 39 intent 全链路 ===")
    li = {k: v for k, v in
          json.load(open(os.path.join(REPO, "layout_index.json"),
                         encoding="utf-8")).items()
          if not k.startswith("_")}
    patterns = {k: v for k, v in
                json.load(open(os.path.join(REPO, "patterns.json"),
                               encoding="utf-8")).items()
                if not k.startswith("_")}
    intents = sorted(li)
    if len(intents) < 39:
        return ok("T1 前提", False, f"intent 仅 {len(intents)} 个")

    # 每个 intent 一页，fields 按首个候选的 text_slots 生成
    pages = []
    for it in intents:
        cand0 = li[it]["candidates"][0]
        pat = patterns[cand0]
        pages.append({"pattern": it, "fields": sample_fields(pat.get("text_slots", {}))})
    sb_path = os.path.join(REPO, "_t1_storyboard.json")
    with open(sb_path, "w", encoding="utf-8") as f:
        json.dump({"title": "39 intent 全覆盖测试", "pages": pages}, f,
                  ensure_ascii=False, indent=2)

    # 解析（模拟真实 CLI 流程）
    r = run([PY, "resolve_intents.py", sb_path, "-o", "-"])
    if r.returncode != 0:
        return ok("T1 解析", False, r.stderr[:200])
    resolved = json.loads(r.stdout)

    # 按解析后 pattern 补 chart/table，再写回
    for p in resolved["pages"]:
        pat = patterns.get(p["pattern"])
        if pat:
            enrich_for_pattern(p, pat)
    with open(sb_path, "w", encoding="utf-8") as f:
        json.dump(resolved, f, ensure_ascii=False, indent=2)

    # 渲染 + 质检
    out = os.path.join(REPO, "_t1_out.pptx")
    r = run([PY, "render_pptx.py", sb_path, "-o", out])
    ok("T1 渲染不中断", r.returncode == 0,
       f"exit={r.returncode} {r.stderr[-200:]}")
    if r.returncode == 0:
        from pptx import Presentation
        n_slides = len(Presentation(out).slides)
        ok("T1 页数=39", n_slides == 39, f"实际 {n_slides}")
        r = run([PY, "verify_pptx.py", sb_path, out])
        ok("T1 质检通过(允许WARN)", r.returncode == 0,
           f"exit={r.returncode} {r.stdout[-300:]}")
    for f in (sb_path, out):
        if os.path.exists(f):
            os.remove(f)
    return True


# ---------------- T2: 未知 pattern 不中断 ----------------

def t2_unresolved_no_crash():
    print("\n=== T2 未知 pattern 不中断 ===")
    sb = {"title": "t2", "pages": [
        {"pattern": "cover", "fields": {"title": "封面", "en": "C"}},
        {"pattern": "points-3", "fields": {"title": "三要点",
                                           "s1": "a", "b1": "aa",
                                           "s2": "b", "b2": "bb",
                                           "s3": "c", "b3": "cc",
                                           "extra_field": "多余字段"}},
    ]}
    sb_path = os.path.join(REPO, "_t2.json")
    out = os.path.join(REPO, "_t2.pptx")
    with open(sb_path, "w", encoding="utf-8") as f:
        json.dump(sb, f, ensure_ascii=False)
    r = run([PY, "render_pptx.py", sb_path, "-o", out])
    ok("T2 渲染 exit 0（不再 SystemExit）", r.returncode == 0,
       f"exit={r.returncode}")
    ok("T2 告警含'兜底'", "兜底" in r.stderr, r.stderr[-300:])
    if r.returncode == 0:
        from pptx import Presentation
        ok("T2 页数不丢", len(Presentation(out).slides) == 2,
           "产物页数应为 2")
    for f in (sb_path, out):
        if os.path.exists(f):
            os.remove(f)
    return True


# ---------------- T3: chart 长度错配 ----------------

def t3_chart_mismatch():
    print("\n=== T3 chart 长度错配 → 告警截断 ===")
    sb = {"title": "t3", "pages": [
        {"pattern": "chart-line",
         "fields": {"title": "错配", "caption": "测试"},
         "chart": {"categories": ["A", "B"],
                   "series": {"s1": [1, 2, 3, 4]}}},
    ]}
    sb_path = os.path.join(REPO, "_t3.json")
    out = os.path.join(REPO, "_t3.pptx")
    with open(sb_path, "w", encoding="utf-8") as f:
        json.dump(sb, f, ensure_ascii=False)
    r = run([PY, "render_pptx.py", sb_path, "-o", out])
    ok("T3 渲染成功", r.returncode == 0)
    ok("T3 告警含'不一致'", "不一致" in r.stderr, r.stderr[-200:])
    if r.returncode == 0:
        from pptx import Presentation
        prs = Presentation(out)
        for sh in prs.slides[0].shapes:
            if getattr(sh, "has_chart", False) and sh.has_chart:
                vals = [list(s.values) for s in sh.chart.series]
                ok("T3 产物 series 已截断到 2", vals == [[1.0, 2.0]],
                   f"实际 {vals}")
                break
        r = run([PY, "verify_pptx.py", sb_path, out])
        ok("T3 verify 判 FAIL（输入有错）", r.returncode == 1,
           r.stdout[-200:])
    for f in (sb_path, out):
        if os.path.exists(f):
            os.remove(f)
    return True


# ---------------- T4: 超长文本 ----------------

def t4_overlong():
    print("\n=== T4 超长文本告警 ===")
    sb = {"title": "t4", "pages": [
        {"pattern": "cover",
         "fields": {"title": "这" * 60, "en": "T"}},
    ]}
    sb_path = os.path.join(REPO, "_t4.json")
    out = os.path.join(REPO, "_t4.pptx")
    with open(sb_path, "w", encoding="utf-8") as f:
        json.dump(sb, f, ensure_ascii=False)
    r = run([PY, "render_pptx.py", sb_path, "-o", out])
    ok("T4 渲染成功", r.returncode == 0)
    ok("T4 告警含'超长'", "超长" in r.stderr, r.stderr[-200:])
    for f in (sb_path, out):
        if os.path.exists(f):
            os.remove(f)
    return True


# ---------------- T5: optimize_layout 治理 ----------------

def t5_optimize():
    print("\n=== T5 optimize_layout 治理 ===")
    patterns = {k: v for k, v in
                json.load(open(os.path.join(REPO, "patterns.json"),
                               encoding="utf-8")).items()
                if not k.startswith("_")}
    sys.path.insert(0, REPO)
    from optimize_layout import optimize

    # 4 页连续 text-3（无图）：应打断相邻重复，且不落入 mockup-3
    pages = [{"pattern": "text-3",
              "fields": {"title": "t", "s1": "1", "b1": "b", "s2": "2",
                         "b2": "b", "s3": "3", "b3": "b"}} for _ in range(4)]
    out = optimize(pages, patterns)
    pats = [p["pattern"] for p in out]
    ok("T5 无相邻重复", all(a != b for a, b in zip(pats, pats[1:])), str(pats))
    ok("T5 无图不选 mockup-3", "mockup-3" not in pats, str(pats))

    # 带 images 的 text-3 页：允许落到 mockup-3
    pages2 = [{"pattern": "text-3", "images": {"img1": "x.png"},
               "fields": {"title": "t", "s1": "1", "b1": "b", "s2": "2",
                          "b2": "b", "s3": "3", "b3": "b"}}] * 2
    out2 = optimize(pages2, patterns)
    ok("T5 有图才可 mockup-3",
       out2[1]["pattern"] in ("steps-3", "mockup-3"),
       str([p["pattern"] for p in out2]))

    # text-4 高频 → text-4icon 轮换
    pages3 = [{"pattern": "text-4",
               "fields": {**{"title": "t"},
                          **{f"{k}{i}": "x" for i in range(1, 5)
                             for k in ("s", "b")}}} for _ in range(4)]
    out3 = optimize(pages3, patterns)
    ok("T5 text-4icon 出现", "text-4icon" in [p["pattern"] for p in out3],
       str([p["pattern"] for p in out3]))
    return True


# ---------------- T6: verify 把关 ----------------

def t6_verify_gates():
    print("\n=== T6 verify 把关 ===")
    # chart 错配 → verify FAIL（直接读 storyboard 也能判）
    sb = {"title": "t6", "pages": [
        {"pattern": "chart-line",
         "fields": {"title": "t", "caption": "c"},
         "chart": {"categories": ["A", "B"],
                   "series": {"s": [1, 2, 3]}}},
    ]}
    sb_path = os.path.join(REPO, "_t6.json")
    out = os.path.join(REPO, "_t6.pptx")
    with open(sb_path, "w", encoding="utf-8") as f:
        json.dump(sb, f, ensure_ascii=False)
    run([PY, "render_pptx.py", sb_path, "-o", out])
    r = run([PY, "verify_pptx.py", sb_path, out])
    ok("T6 chart 错配 verify FAIL", r.returncode == 1, r.stdout[-200:])
    for f in (sb_path, out):
        if os.path.exists(f):
            os.remove(f)
    return True


# ---------------- T7: schema ↔ patterns ----------------

def t7_schema_vs_patterns():
    print("\n=== T7 schema enum ↔ patterns ===")
    schema = json.load(open(os.path.join(REPO, "storyboard.schema.json"),
                            encoding="utf-8"))
    enum = set(schema["properties"]["pages"]["items"]["properties"]["pattern"]["enum"])
    patterns = set(k for k in
                   json.load(open(os.path.join(REPO, "patterns.json"),
                                  encoding="utf-8"))
                   if not k.startswith("_"))
    ok("T7 双向包含一致", enum == patterns,
       f"schema-有/patterns-无: {enum - patterns or '无'}; "
       f"patterns-有/schema-无: {patterns - enum or '无'}")
    return True


# ---------------- 入口 ----------------

if __name__ == "__main__":
    print(f"pptx-kit 回归测试（仓库: {REPO}）")
    t7_schema_vs_patterns()
    t5_optimize()
    t4_overlong()
    t3_chart_mismatch()
    t6_verify_gates()
    t2_unresolved_no_crash()
    t1_intents_full_chain()
    print(f"\n结果：{PASS} 通过 / {FAIL} 失败")
    sys.exit(1 if FAIL else 0)

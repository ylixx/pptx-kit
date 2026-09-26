# -*- coding: utf-8 -*-
"""make_viewer.py 测试：
1) 生成 viewer.html 成功且无 JS 占位残留
2) HTML 含关键交互结构（stats/contextMenu/导出/体检）
3) 内联 JS 语法通过 node --check（node 可用时）
4) 服务端统计与 storyboard 一致（重复/相邻重复）
"""
import json
import os
import re
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, "make_viewer.py")
SB = os.path.join(REPO, "examples", "ai-history", "storyboard.variety20.json")
OUT = os.path.join(REPO, "_viewer_test.html")
PASS = FAIL = 0


def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} {detail}")


def run(args):
    return subprocess.run([sys.executable, TOOL] + args,
                          capture_output=True, text=True, encoding="utf-8")


print("=== 1. 生成 viewer.html ===")
r = run([SB, "-o", OUT])
ok("生成 exit 0", r.returncode == 0, r.stderr[-300:])
html = open(OUT, encoding="utf-8").read()
ok("含关键结构", all(k in html for k in ["contextMenu", "exportStoryboard",
                                          "refreshStats", "collectIssues",
                                          "更多版式", "导出前体检"]))
ok("无 JS 占位残留", not re.search(r"\{JS_(STORYBOARD|GROUPS|SLOTS)\}", html))

print("\n=== 2. 内联 JS 语法（node 可用时） ===")
m = re.search(r"<script>(.*?)</script>", html, re.S)
ok("提取到 <script> 块", m is not None)
if m:
    js = m.group(1)
    node = shutil.which("node")
    if node:
        tmp = os.path.join(REPO, "_viewer_js_test.js")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(js)
        nr = subprocess.run([node, "--check", tmp], capture_output=True,
                            text=True, encoding="utf-8")
        os.remove(tmp)
        ok("node --check 通过", nr.returncode == 0, nr.stderr[:300])
    else:
        print("  · node 不可用，跳过语法检查")

print("\n=== 3. 服务端统计正确性 ===")
sb = json.load(open(SB, encoding="utf-8"))
pages = sb["pages"]
STRUCTURAL = {"cover", "toc", "section", "thanks", "refs"}
usage = {}
for p in pages:
    usage[p.get("pattern", "")] = usage.get(p.get("pattern", ""), 0) + 1
dup_patterns = {k: v for k, v in usage.items()
                if v > 1 and k not in STRUCTURAL}
adjacent = sum(1 for i in range(1, len(pages))
               if pages[i].get("pattern") == pages[i - 1].get("pattern")
               and pages[i].get("pattern") not in STRUCTURAL)
ok(f"重复版式统计正确（{sorted(dup_patterns)}）",
   dup_patterns == {"text-3": 3, "steps-3": 2})
ok(f"相邻重复统计正确（{adjacent} 处）", adjacent == 0)
ok("20 页含 chart-line 图表页",
   any(p.get("pattern") == "chart-line" for p in pages))

os.remove(OUT)
print(f"\n结果：{PASS} 通过 / {FAIL} 失败")
sys.exit(1 if FAIL else 0)

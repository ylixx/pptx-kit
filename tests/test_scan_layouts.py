# -*- coding: utf-8 -*-
"""scan_layouts.py 测试：
1) 语法/帮助正常
2) --check 校验现有 49 版式映射 0 漂移
3) --map 用真实模板 slide14 手动映射，生成的条目与 patterns.json text-3 完全一致
4) 命名扫描对未命名页正确报"未识别槽位"
5) merge 写回 patterns/schema/layout（用副本文件），验证三文件同步
"""
import json
import os
import shutil
import subprocess
import sys

# 仓库根 = tests/ 的父目录（本文件位于 tests/ 下）
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, "scan_layouts.py")
TMP = os.path.join(REPO, "_scan_test")
PASS = FAIL = 0

def run(args, cwd=None):
    return subprocess.run([sys.executable, TOOL] + args,
                          capture_output=True, text=True, encoding="utf-8",
                          cwd=cwd or REPO)

def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✅ {name}")
    else:
        FAIL += 1; print(f"  ❌ {name} {detail}")

# 1) --check
print("=== 1. 校验既有映射 ===")
r = run(["--check"])
ok("--check exit 0（0 漂移）", r.returncode == 0, r.stdout[-200:])

# 2) --map 生成条目 vs patterns.json text-3
print("\n=== 2. --map 索引准确性（slide14 vs text-3） ===")
os.makedirs(TMP, exist_ok=True)
for f in ["patterns.json", "layout_index.json", "storyboard.schema.json"]:
    shutil.copy2(os.path.join(REPO, f), os.path.join(TMP, f))
r = run(["--page", "14", "--id", "_test-3", "--desc", "测试版式",
         "--map", "title=15,s1=1,b1=3,s2=6,b2=8,s3=11,b3=13",
         "--intent", "points-3", "--patterns", os.path.join(TMP, "patterns.json"),
         "--layout", os.path.join(TMP, "layout_index.json"),
         "--schema", os.path.join(TMP, "storyboard.schema.json")])
ok("--map 写回 exit 0", r.returncode == 0, r.stderr[-200:])
got = json.load(open(os.path.join(TMP, "patterns.json"), encoding="utf-8"))["_test-3"]
want = json.load(open(os.path.join(REPO, "patterns.json"), encoding="utf-8"))["text-3"]
# 索引与槽位映射应完全一致（desc 为用户参数，单独验证）
ok("生成条目索引与 text-3 完全一致",
   got["slide"] == want["slide"] and got["text_slots"] == want["text_slots"],
   f"got={got['text_slots']} want={want['text_slots']}")
ok("desc 参数生效", got["desc"] == "测试版式")
schema = json.load(open(os.path.join(TMP, "storyboard.schema.json"), encoding="utf-8"))
enum = schema["properties"]["pages"]["items"]["properties"]["pattern"]["enum"]
ok("schema enum 已同步 _test-3", "_test-3" in enum)
layout = json.load(open(os.path.join(TMP, "layout_index.json"), encoding="utf-8"))
ok("layout_index points-3 候选已加 _test-3",
   "_test-3" in layout["points-3"]["candidates"])
bak = os.path.exists(os.path.join(TMP, "patterns.json.bak"))
ok("写回前已备份 .bak", bak)

# 3) 命名扫描对未命名页 → 正确报"未识别"
print("\n=== 3. 命名扫描（未命名页应报错） ===")
r = run(["--page", "14", "--id", "_test-x", "--dry-run"])
ok("未命名页 exit 1 + 提示", r.returncode == 1 and "未识别到任何槽位" in r.stdout)

# 4) 重复 id 冲突保护
print("\n=== 4. id 冲突保护 ===")
r = run(["--page", "14", "--id", "_test-3", "--map", "title=15",
         "--patterns", os.path.join(TMP, "patterns.json")])
ok("重复 id 报错（需 --force）", r.returncode != 0 and "已存在" in (r.stderr or ""))

# 5) 全模板盘点（参考 pptx-from-layouts 的 profile 思路）
print("\n=== 5. --inventory 全模板盘点 ===")
r = run(["--inventory"])
ok("inventory exit 0", r.returncode == 0, r.stderr[-200:])
ok("输出含版式族聚类", "版式族聚类" in r.stdout and "指纹" in r.stdout)
ok("输出含逐页明细与已接入对照", "逐页明细" in r.stdout and "text-3" in r.stdout)
ok("输出未接入清单", "未接入且含文本的页" in r.stdout)
ok("能识别 section 变体族（页3-8）",
   "页[3,4,5,6,7,8]" in r.stdout.replace(" ", "").replace("页[", "页["),
   "若失败可能是模板结构变化")

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n结果：{PASS} 通过 / {FAIL} 失败")
sys.exit(1 if FAIL else 0)

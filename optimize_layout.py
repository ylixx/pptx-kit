#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
optimize_layout.py — 版式多样性后处理（视觉节奏优化）

扫描 storyboard.json，把连续重复或全局高频的内容版式，
自动替换为"字段兼容、无空位风险"的等价候选版式，
从而让每页布局尽量不重复，且不丢失任何文字内容。

用法：
    python3 optimize_layout.py storyboard.json [-o out.json] [--max-repeat 3]

替换原则：
- 仅替换内容版式（结构页 cover/toc/section/thanks/qa/refs 不动）
- 候选版式必须能容纳本页全部 fields（字段兼容硬条件）
- 需要图片槽的候选（如 mockup-3）仅在本页已有 images 时才可选，避免空图占位
- 优先打断"相邻相同（含视觉等价族内相邻）"，其次压制"全局高频"
"""
import json
import sys
import argparse
from collections import Counter

# 字段兼容的等价替换候选（同组 s/b，无强制图片依赖优先）
EQUIV = {
    "text-3": ["steps-3", "mockup-3"],
    "text-4": ["text-4icon"],
}
# 带强制图片槽的候选：仅当页面已有 images 时才允许替换到它们
IMG_REQUIRED = {"mockup-3"}
STRUCT = {"cover", "toc", "section", "thanks", "qa", "refs"}


def _compatible(patterns, cand, page):
    """候选版式的 text_slots 必须 ⊇ 本页 fields 全部 key。"""
    fk = set((page.get("fields") or {}).keys())
    slots = set(patterns.get(cand, {}).get("text_slots", {}))
    return fk.issubset(slots)


def _can_use(patterns, cand, page):
    return _compatible(patterns, cand, page) and (
        cand not in IMG_REQUIRED or bool(page.get("images")))


def _visual_dup(cand, last):
    """当前版式与上一页是否视觉重复（含等价族内，如 text-3 与 steps-3）。"""
    if cand == last:
        return True
    return last in EQUIV.get(cand, [])


def optimize(pages, patterns=None, max_repeat=3):
    patterns = patterns or {}
    result = []
    last = None
    freq = Counter()
    for p in pages:
        pat = p["pattern"]
        cand = pat

        # 1) 相邻重复（含等价族内）→ 换等价候选
        if pat in EQUIV and pat not in STRUCT and _visual_dup(cand, last):
            for alt in EQUIV[pat]:
                if alt != last and _can_use(patterns, alt, p):
                    cand = alt
                    break

        # 2) 全局高频 → 换等价候选（选频次未达上限者）
        if cand in EQUIV and cand not in STRUCT and freq[cand] >= max_repeat:
            for alt in EQUIV[cand]:
                if freq[alt] < max_repeat and _can_use(patterns, alt, p):
                    cand = alt
                    break

        p2 = dict(p)
        p2["pattern"] = cand
        result.append(p2)
        last = cand
        freq[cand] += 1
    return result


def main():
    ap = argparse.ArgumentParser(description="版式多样性后处理")
    ap.add_argument("storyboard", help="输入 storyboard.json")
    ap.add_argument("-o", "--output", help="输出路径（默认覆盖原文件）")
    ap.add_argument("--max-repeat", type=int, default=3,
                    help="同一内容版式全局最大出现次数（默认 3）")
    a = ap.parse_args()

    with open(a.storyboard, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 加载 patterns.json 做字段兼容校验（可选：不存在则只做结构替换）
    try:
        with open("patterns.json", "r", encoding="utf-8") as f:
            patterns = {k: v for k, v in json.load(f).items()
                        if not k.startswith("_")}
    except OSError:
        patterns = {}

    before = Counter(p["pattern"] for p in data["pages"])
    data["pages"] = optimize(data["pages"], patterns, a.max_repeat)
    after = Counter(p["pattern"] for p in data["pages"])

    out = a.output or a.storyboard
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"已优化 -> {out}")
    print("变化：")
    for k in sorted(set(before) | set(after)):
        if before[k] != after[k]:
            print(f"  {k}: {before[k]} -> {after[k]}")


if __name__ == "__main__":
    sys.exit(main())

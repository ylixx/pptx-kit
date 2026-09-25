#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
optimize_layout.py — 版式多样性后处理（视觉节奏优化）

扫描 storyboard.json，把连续重复或全局高频的内容版式，
自动替换为"字段兼容、无图片依赖"的等价候选版式，
从而让每页布局尽量不重复，且不丢失任何文字内容。

用法：
    python3 optimize_layout.py storyboard.json [-o out.json] [--max-repeat 3]

替换原则：
- 仅替换内容版式（结构页 cover/toc/section/thanks/qa/refs 不动）
- 等价候选字段数一致、无强制图片槽，文字 s*/b* 一一对应，内容零丢失
- 优先打断"相邻相同"，其次压制"全局高频"
"""
import json
import sys
import argparse
from collections import Counter

# 字段兼容的等价替换候选（同组数 s/b，无强制图片依赖优先）
EQUIV = {
    "text-3": ["steps-3", "mockup-3"],
    "text-4": ["text-4icon"],
}
STRUCT = {"cover", "toc", "section", "thanks", "qa", "refs"}


def optimize(pages, max_repeat=3):
    result = []
    last = None
    freq = Counter()
    for p in pages:
        pat = p["pattern"]
        cand = pat

        # 1) 相邻重复 → 换等价候选
        if pat == last and pat not in STRUCT and pat in EQUIV:
            for alt in EQUIV[pat]:
                if alt != last:
                    cand = alt
                    break

        # 2) 全局高频 → 换等价候选（选频次未达上限者）
        if cand not in STRUCT and cand in EQUIV and freq[cand] >= max_repeat:
            for alt in EQUIV[cand]:
                if freq[alt] < max_repeat:
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

    before = Counter(p["pattern"] for p in data["pages"])
    data["pages"] = optimize(data["pages"], a.max_repeat)
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

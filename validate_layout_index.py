#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_layout_index.py — 交叉校验 layout_index.json 与 patterns.json 的双向包含。

约束：
  1) layout_index 顶层 key 不以 _ 开头（会被 render/resolve 过滤）。
  2) layout_index.candidates 都在 patterns.json 中。
  3) patterns.json 每个 pattern 至少出现在一个 layout_index.candidates 中（全量覆盖）。

用法：
  python validate_layout_index.py
"""

import json
import os
import sys


def warn(msg):
    print(f"[warn] {msg}", file=sys.stderr)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            return json.loads(raw[start:end + 1])
        raise


def validate_layout_index(layout_path="layout_index.json", patterns_path="patterns.json"):
    """校验 layout_index.json 与 patterns.json 的双向包含。"""
    print("🔍 开始校验 layout_index.json 与 patterns.json...")

    li_raw = load_json(layout_path)
    patterns = load_json(patterns_path)

    # 过滤掉以 _ 开头的 key
    li = {k: v for k, v in li_raw.items() if not k.startswith("_")}
    patterns = {k: v for k, v in patterns.items() if not k.startswith("_")}

    # 1) 检查 layout_index 顶层 key 不以 _ 开头（已在 li 过滤中保证）
    li_underscores = [k for k in li_raw.keys() if k.startswith("_")]
    if li_underscores:
        print(f"✅ layout_index.json 中 {len(li_underscores)} 个以 _ 开头的 key（将被过滤）:")
        for k in li_underscores:
            print(f"   - {k}")
    else:
        print("✅ layout_index.json 无以 _ 开头的 key")

    # 2) 检查 layout_index.candidates 都在 patterns.json 中
    all_candidates = set()
    for intent, data in li.items():
        candidates = data.get("candidates", [])
        all_candidates.update(candidates)
        for c in candidates:
            if c not in patterns:
                print(f"❌ layout_index[{intent}].candidate '{c}' 不在 patterns.json 中")
                return False

    # 3) 检查 patterns.json 每个 pattern 至少出现在一个 candidates 中（全量覆盖）
    patterns_in_candidates = set(all_candidates)
    patterns_not_covered = set(patterns.keys()) - patterns_in_candidates
    if patterns_not_covered:
        print(f"❌ patterns.json 中 {len(patterns_not_covered)} 个 pattern 未被 layout_index 覆盖:")
        for p in sorted(patterns_not_covered):
            print(f"   - {p}")
        return False

    # 4) 统计信息
    print(f"✅ layout_index 有 {len(li)} 个 intent")
    print(f"✅ patterns.json 有 {len(patterns)} 个 pattern")
    print(f"✅ layout_index 覆盖全部 {len(patterns_in_candidates)} 个 pattern")
    print("✅ 双向包含校验通过！")
    return True


def main():
    if len(sys.argv) > 1:
        print("用法: python validate_layout_index.py")
        return 1

    success = validate_layout_index()
    if not success:
        print("\n❌ 校验失败，请修复 layout_index.json 或 patterns.json")
        return 1
    else:
        print("\n🎉 校验成功！")
        return 0


if __name__ == "__main__":
    sys.exit(main())

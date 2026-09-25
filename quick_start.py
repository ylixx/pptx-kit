#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quick_start.py — 辅助生成 AI 提示词的工具

正确用法：
1. 把你的论文文件（如 paper.txt）放在当前目录
2. 运行：python3 quick_start.py
3. 脚本会自动生成完整的 AI 提示词
4. 你复制提示词给 AI，AI 直接生成 storyboard.json
5. AI 返回的 JSON 粘贴给脚本，自动保存
6. 最后运行：python3 render_pptx.py storyboard.json -o 答辩.pptx

支持论文格式：.txt, .md, .docx（需先转为文本）
"""

import os
import sys
from pathlib import Path


def find_paper_file():
    """查找论文文件，支持多种格式"""
    extensions = ['.txt', '.md', '.docx']
    for ext in extensions:
        files = list(Path('.').glob(f'*{ext}'))
        if files:
            # 取第一个匹配的文件
            paper_file = files[0]
            print(f"📄 找到论文文件：{paper_file}")
            return str(paper_file)
    
    print("❌ 未找到论文文件，请确保当前目录有 .txt/.md/.docx 文件")
    return None


def read_paper_content(paper_file):
    """读取论文内容"""
    try:
        if paper_file.endswith('.txt') or paper_file.endswith('.md'):
            with open(paper_file, 'r', encoding='utf-8') as f:
                content = f.read()
        elif paper_file.endswith('.docx'):
            # 简单处理：需要 python-docx 库
            try:
                from docx import Document
                doc = Document(paper_file)
                content = '\n'.join([para.text for para in doc.paragraphs])
            except ImportError:
                print("❌ 需要 python-docx 库来读取 .docx 文件")
                print("请先安装：pip install python-docx")
                return None
        else:
            print("❌ 不支持的文件格式")
            return None
        
        print(f"📖 读取论文内容，共 {len(content)} 字符")
        return content
    except Exception as e:
        print(f"❌ 读取论文文件失败：{e}")
        return None


def read_prompt():
    """读取 PROMPT.md"""
    try:
        with open('PROMPT.md', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print("❌ 未找到 PROMPT.md 文件")
        return None


def generate_ai_prompt(paper_content):
    """生成给 AI 的提示词"""
    prompt = read_prompt()
    if not prompt:
        return None
    
    # 追加论文内容
    ai_instruction = f"""
请将以下论文重构成 storyboard.json，只输出 JSON，不要任何解释。

重要：pattern 字段只能使用提示词中"版式目录"里列出的具体版式名（如 text-3、timeline-4），
禁止使用目录之外的名称（如 points-3）。

论文内容：
---
{paper_content}
---

现在请输出完整的 storyboard JSON：
"""
    
    return prompt + ai_instruction


def main():
    print("🚀 Quick Start - AI 提示词生成器")
    print("=" * 50)
    
    # 1. 查找论文文件
    paper_file = find_paper_file()
    if not paper_file:
        return 1
    
    # 2. 读取论文内容
    paper_content = read_paper_content(paper_file)
    if not paper_content:
        return 1
    
    # 3. 生成 AI 提示词
    ai_prompt = generate_ai_prompt(paper_content)
    if not ai_prompt:
        return 1
    
    # 4. 显示提示词，供用户复制给 AI
    print("\n" + "=" * 50)
    print("🤖 请将以下内容复制给任意 AI（ChatGPT/Claude/Kimi/本地模型）：")
    print("=" * 50)
    print(ai_prompt)
    print("=" * 50)
    
    print("\n📋 使用说明：")
    print("1. 复制上面的完整提示词给 AI")
    print("2. AI 会直接生成 storyboard.json（包含完整的 JSON 内容）")
    print("3. 将 AI 返回的 JSON 粘贴到下面的输入框")
    print("4. 脚本会自动验证并保存为 storyboard.json 文件")
    print("-" * 30)
    
    # 5. 等待用户输入 AI 生成的 JSON
    print("🎯 请将 AI 生成的 storyboard.json 粘贴到下面（只粘贴 JSON 内容）：")
    
    # 读取用户粘贴的 JSON
    json_lines = []
    while True:
        line = input()
        if line.strip() == '':
            break
        json_lines.append(line)
    
    json_content = '\n'.join(json_lines)
    
    # 6. 验证并保存 JSON
    try:
        import json
        storyboard = json.loads(json_content)
        
        # 简单验证结构
        if 'title' in storyboard and 'pages' in storyboard:
            with open('storyboard.json', 'w', encoding='utf-8') as f:
                f.write(json.dumps(storyboard, ensure_ascii=False, indent=2))
            
            print(f"\n✅ storyboard.json 已保存，共 {len(storyboard['pages'])} 页")
            print("\n🎉 下一步运行：")
            print("python3 render_pptx.py storyboard.json -o 答辩.pptx")
            return 0
        else:
            print("❌ JSON 格式不正确，缺少 title 或 pages 字段")
            print("请确保 AI 返回的是完整的 storyboard.json 格式")
            return 1
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败：{e}")
        print("请检查 AI 返回的 JSON 格式是否正确")
        return 1


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_viewer.py — 生成纯静态自包含的 viewer.html，支持换版式、导出修改后的 JSON。

输入：
  * storyboard.json：内容源
  * layout_index.json：intent 分类表
  * patterns.json：版式槽位映射
  * deck_thumbs/：已生成的 deck 缩略图（slide001.png 等）
  * tpl_thumbs/：已生成的模板缩略图（tpl_001.png 等）

输出：
  * viewer.html：纯静态，无 CDN，无网络依赖，双击即用。

交互：
  * 左键 / 右键点击卡片 → 弹出版式切换菜单（按 intent 分组，候选带模板缩略图、
    desc、字段/图片/图表/表格兼容状态，当前版式高亮，不兼容灰色标注原因）。
  * 「📋 更多版式…」展开全部 intent；展开后顶部「← 返回」回到当前 intent。
  * 点选候选 → 实时更新卡片（页码、pattern 名、主图），toast 提示。
  * 卡片角标显示重复次数（同一版式第 2 次起 ×N）；工具栏实时统计
    「去重 M/N · 相邻重复 K 处」。
  * 导出前自动体检：逐页兼容性 + 重复/相邻重复汇总，有问题的页面列清单
    供确认后再下载。
  * 图片失败降级为灰块，不崩页面；JS 字符串注入已转义 </script>。
"""

import argparse
import json
import os
import sys

FALLBACK_B64 = ("PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIg"
                "ZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48"
                "cmVjdCB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIGZpbGw9IiNGM0Y0RjYiLz48L3N2Zz4=")


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


def js_str(obj):
    """JSON 内联进 <script> 的安全序列化：转义 </script> 与 U+2028/2029。"""
    s = json.dumps(obj, ensure_ascii=False)
    return (s.replace("</", "<\\/")
             .replace("\u2028", "\\u2028")
             .replace("\u2029", "\\u2029"))


def main():
    ap = argparse.ArgumentParser(description="生成 viewer.html")
    ap.add_argument("storyboard", help="storyboard.json 路径")
    ap.add_argument("-l", "--layout",
                    default="layout_index.json",
                    help="layout_index.json 路径（默认同目录）")
    ap.add_argument("-p", "--patterns",
                    default="patterns.json",
                    help="patterns.json 路径（默认同目录）")
    ap.add_argument("-t", "--thumbs", default="deck_thumbs",
                    help="deck 缩略图目录（默认 deck_thumbs/）")
    ap.add_argument("--tpl-thumbs", default="tpl_thumbs",
                    help="模板缩略图目录（默认 tpl_thumbs/）")
    ap.add_argument("-o", "--out", default="viewer.html",
                    help="输出 HTML 路径（默认 viewer.html）")
    args = ap.parse_args()

    sb = load_json(args.storyboard)
    li = load_json(args.layout)
    li = {k: v for k, v in li.items() if not k.startswith("_")}
    patterns = load_json(args.patterns)
    patterns = {k: v for k, v in patterns.items() if not k.startswith("_")}

    pattern_to_idx = {}
    for name, pat in patterns.items():
        if "slide" in pat:
            pattern_to_idx[name] = pat["slide"]

    pages = sb.get("pages", [])
    title = sb.get("title", "Storyboard Viewer")
    n_pages = len(pages)

    # intent 分组（含模板缩略图与描述）
    intent_groups = {}
    for intent, data in li.items():
        items = []
        for cand_name in data.get("candidates", []):
            cand_pat = patterns.get(cand_name)
            if not cand_pat:
                continue
            tpl_idx = pattern_to_idx.get(cand_name)
            items.append({
                "name": cand_name,
                "desc": cand_pat.get("desc", ""),
                "tpl_img": (f"{args.tpl_thumbs}/tpl_{tpl_idx:03d}.png"
                            if tpl_idx else ""),
            })
        intent_groups[intent] = {"desc": data.get("desc", ""), "items": items}

    # 槽位能力表：text 槽 / image 槽 / 是否需要图表 / 是否需要表格
    slot_sets = {}
    for name, pat in patterns.items():
        slot_sets[name] = {
            "text": list(pat.get("text_slots", {}).keys()),
            "image": list(pat.get("image_slots", {}).keys()),
            "chart": bool(pat.get("chart_slot") is not None
                          or pat.get("chart_slots")),
            "table": pat.get("table_slot") is not None,
        }

    # 服务端预统计：每个 pattern 出现次数、相邻重复处数
    usage = {}
    for p in pages:
        usage[p.get("pattern", "")] = usage.get(p.get("pattern", ""), 0) + 1
    adjacent = sum(1 for i in range(1, len(pages))
                   if pages[i].get("pattern") == pages[i - 1].get("pattern")
                   and pages[i].get("pattern") not in
                   ("cover", "toc", "section", "thanks", "refs"))

    def card(i, page):
        pattern = page.get("pattern", "unknown")
        dup = usage.get(pattern, 0)
        badge = ""
        if dup > 1 and pattern not in ("cover", "toc", "section", "thanks", "refs"):
            badge = f'<span class="dup-badge">×{dup}</span>'
        return (
            f'<div class="card" data-page="{i}" data-pattern="{pattern}" '
            f'oncontextmenu="openMenu(event,{i});return false;" '
            f'onclick="openMenu(event,{i})">'
            f'<div class="thumb-wrap"><img src="{args.thumbs}/slide{i:03d}.png" '
            f'alt="第{i}页" onerror="imgFail(this)">{badge}</div>'
            f'<div class="card-info">'
            f'<div class="card-page">第 {i} 页</div>'
            f'<div class="card-pattern">{pattern}</div>'
            f'</div></div>'
        )

    cards_html = "\n".join(card(i, p) for i, p in enumerate(pages, 1))

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - 版式切换器</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; background: #f5f5f5; }}
.toolbar {{ position: sticky; top: 0; background: white; padding: 10px 20px; box-shadow: 0 2px 4px rgba(0,0,0,.1); z-index: 100; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }}
.toolbar h1 {{ margin: 0; font-size: 18px; }}
.toolbar .stats {{ color: #666; font-size: 13px; }}
.toolbar .bad {{ color: #d32f2f; font-weight: 600; }}
.toolbar .ok {{ color: #2e7d32; font-weight: 600; }}
.toolbar button {{ background: #007bff; color: white; border: none; padding: 6px 14px; border-radius: 4px; cursor: pointer; }}
.toolbar button:hover {{ background: #0056b3; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; padding: 20px; }}
.card {{ background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,.1); cursor: pointer; transition: transform .15s, box-shadow .15s; user-select: none; }}
.card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 14px rgba(0,0,0,.16); }}
.thumb-wrap {{ position: relative; }}
.card img {{ width: 100%; height: 120px; object-fit: cover; display: block; background: #eee; }}
.dup-badge {{ position: absolute; top: 6px; right: 6px; background: #d32f2f; color: white; font-size: 12px; font-weight: 700; padding: 2px 7px; border-radius: 10px; }}
.card-info {{ padding: 10px 12px; }}
.card-page {{ font-size: 12px; color: #666; margin-bottom: 4px; }}
.card-pattern {{ font-weight: bold; font-size: 14px; word-break: break-all; }}
.context-menu {{ position: fixed; background: white; border: 1px solid #ddd; border-radius: 6px; box-shadow: 0 6px 20px rgba(0,0,0,.18); padding: 4px 0; z-index: 1000; max-height: 82vh; overflow-y: auto; display: none; min-width: 300px; }}
.menu-top {{ position: sticky; top: 0; background: white; padding: 6px 12px; font-size: 12px; color: #888; border-bottom: 1px solid #eee; display: flex; align-items: center; justify-content: space-between; }}
.menu-back {{ cursor: pointer; color: #007bff; font-weight: 600; }}
.menu-group-title {{ padding: 6px 12px; font-size: 12px; color: #888; font-weight: 700; background: #fafafa; border-bottom: 1px solid #eee; }}
.menu-item {{ padding: 8px 12px; cursor: pointer; display: flex; align-items: center; }}
.menu-item:hover {{ background: #f0f4ff; }}
.menu-item.current {{ background: #e3f2fd; }}
.menu-item.incompatible {{ opacity: .62; }}
.menu-item img {{ width: 44px; height: 44px; object-fit: cover; margin-right: 12px; border-radius: 4px; background: #f3f4f6; flex: none; }}
.menu-item-content {{ flex: 1; min-width: 0; }}
.menu-item-name {{ font-weight: bold; font-size: 13px; }}
.menu-item-desc {{ font-size: 12px; color: #666; margin-top: 1px; }}
.menu-item-compat {{ font-size: 11px; margin-top: 3px; }}
.compat-ok {{ color: #2e7d32; }}
.compat-warn {{ color: #b26a00; }}
.compat-bad {{ color: #d32f2f; }}
.menu-separator {{ border-top: 1px solid #eee; margin: 4px 0; }}
.menu-expander {{ padding: 8px 12px; font-style: italic; color: #666; cursor: pointer; }}
.menu-expander:hover {{ background: #f0f4ff; }}
.hidden {{ display: none; }}
.toast {{ position: fixed; left: 50%; bottom: 32px; transform: translateX(-50%); background: rgba(0,0,0,.82); color: white; padding: 10px 20px; border-radius: 20px; font-size: 14px; z-index: 2000; opacity: 0; transition: opacity .25s; pointer-events: none; }}
.modal-mask {{ position: fixed; inset: 0; background: rgba(0,0,0,.4); z-index: 1500; display: none; align-items: center; justify-content: center; }}
.modal {{ background: white; border-radius: 8px; max-width: 640px; width: 90%; max-height: 78vh; overflow-y: auto; padding: 20px; }}
.modal h3 {{ margin-top: 0; }}
.modal ul {{ margin: 8px 0 0; padding-left: 20px; }}
.modal .warn-item {{ color: #b26a00; }}
.modal .bad-item {{ color: #d32f2f; }}
.modal-actions {{ margin-top: 16px; text-align: right; }}
.modal button {{ margin-left: 8px; padding: 6px 14px; border-radius: 4px; cursor: pointer; border: 1px solid #ccc; background: white; }}
.modal button.primary {{ background: #007bff; color: white; border-color: #007bff; }}
</style>
</head>
<body>
<div class="toolbar">
    <h1>{title}</h1>
    <div class="stats" id="stats"></div>
    <button onclick="exportStoryboard()">导出 storyboard.json</button>
</div>
<div class="grid" id="grid">
{cards_html}
</div>
<div class="context-menu" id="contextMenu"></div>
<div class="toast" id="toast"></div>
<div class="modal-mask" id="modalMask" onclick="if(event.target===this)closeModal()">
    <div class="modal" id="modalBody"></div>
</div>
<script>
const FALLBACK = 'data:image/svg+xml;base64,{{FALLBACK_B64}}';
const storyboard = {{JS_STORYBOARD}};
const intentGroups = {{JS_GROUPS}};
const slotSets = {{JS_SLOTS}};
const ESC = (s) => String(s).replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
let currentPage = null;
let menuMode = 'intent';

function imgFail(img) {{
    if (img.dataset.failed) return;
    img.dataset.failed = '1';
    img.style.opacity = .3;
    img.src = FALLBACK;
}}

function findIntentForPattern(pattern) {{
    for (const intent in intentGroups) {{
        if (intentGroups[intent].items.some(it => it.name === pattern)) return intent;
    }}
    return null;
}}

/* 兼容性三路检查：文本槽 / 图片槽 / 图表与表格需求 */
function checkCompat(item, page) {{
    const slots = slotSets[item.name] || {{text: [], image: [], chart: false, table: false}};
    const fk = Object.keys(page.fields || {{}});
    const ik = Object.keys(page.images || {{}});
    const missingText = fk.filter(k => slots.text.indexOf(k) < 0);
    const missingImg = ik.filter(k => slots.image.indexOf(k) < 0);
    const warns = [], bads = [];
    if (missingText.length) bads.push('缺字段: ' + missingText.join(', '));
    if (missingImg.length) bads.push('缺图片槽: ' + missingImg.join(', '));
    if (slots.chart && !page.chart && !page.charts) warns.push('此版式需图表数据(chart)');
    if (slots.table && !page.table) warns.push('此版式需表格数据(table)');
    const needImg = slots.image.length && !ik.length;
    if (needImg) warns.push('此版式有图片槽，页面未配图');
    return {{bads, warns, ok: !bads.length && !warns.length}};
}}

function renderGroup(intent, group, page) {{
    let h = '<div class="menu-group-title">' + ESC(intent) + ' · ' + ESC(group.desc || '') + '</div>';
    for (const item of group.items) {{
        const c = checkCompat(item, page);
        const cls = ['menu-item'];
        if (item.name === page.pattern) cls.push('current');
        else if (c.bads.length) cls.push('incompatible');
        const compat = c.ok ? '<span class="compat-ok">✅ 兼容</span>'
            : (c.bads.length ? '<span class="compat-bad">❌ ' + ESC(c.bads.join('; ')) + '</span>'
                             : '<span class="compat-warn">⚠ ' + ESC(c.warns.join('; ')) + '</span>');
        h += '<div class="' + cls.join(' ') + '" data-pat="' + ESC(item.name) + '" onclick="selectPattern(this.dataset.pat)">'
            + '<img src="' + (item.tpl_img || FALLBACK) + '" alt="' + ESC(item.name) + '" onerror="imgFail(this)">'
            + '<div class="menu-item-content">'
            + '<div class="menu-item-name">' + ESC(item.name) + '</div>'
            + '<div class="menu-item-desc">' + ESC(item.desc) + '</div>'
            + '<div class="menu-item-compat">' + compat + '</div>'
            + '</div></div>';
    }}
    return h;
}}

function openMenu(event, pageIdx) {{
    event.preventDefault();
    event.stopPropagation();
    currentPage = pageIdx;
    menuMode = 'intent';
    const page = storyboard.pages[pageIdx - 1];
    const intent = page._intent || findIntentForPattern(page.pattern);
    const menu = document.getElementById('contextMenu');
    let html = '<div class="menu-top">第 ' + pageIdx + ' 页 · 切换版式'
        + '<span class="menu-back" onclick="event.stopPropagation();closeMenu()">✕</span></div>';
    if (intent && intentGroups[intent]) {{
        html += renderGroup(intent, intentGroups[intent], page);
        html += '<div class="menu-separator"></div>';
    }}
    html += '<div class="menu-expander" onclick="showAllIntents(event)">📋 更多版式…</div>';
    menu.innerHTML = html;
    positionMenu(menu, event);
}}

function showAllIntents(event) {{
    event.stopPropagation();
    menuMode = 'all';
    const page = storyboard.pages[currentPage - 1];
    const menu = document.getElementById('contextMenu');
    let html = '<div class="menu-top"><span class="menu-back" onclick="event.stopPropagation();backToIntent()">← 返回</span>'
        + '<span class="menu-back" onclick="event.stopPropagation();closeMenu()">✕</span></div>';
    for (const intent in intentGroups) {{
        html += renderGroup(intent, intentGroups[intent], page);
        html += '<div class="menu-separator"></div>';
    }}
    menu.innerHTML = html;
    positionMenu(menu, event);
}}

function backToIntent() {{
    const page = storyboard.pages[currentPage - 1];
    const intent = page._intent || findIntentForPattern(page.pattern);
    const menu = document.getElementById('contextMenu');
    let html = '<div class="menu-top">第 ' + currentPage + ' 页 · 切换版式'
        + '<span class="menu-back" onclick="event.stopPropagation();closeMenu()">✕</span></div>';
    if (intent && intentGroups[intent]) {{
        html += renderGroup(intent, intentGroups[intent], page);
        html += '<div class="menu-separator"></div>';
    }}
    html += '<div class="menu-expander" onclick="showAllIntents(event)">📋 更多版式…</div>';
    menu.innerHTML = html;
    menuMode = 'intent';
    positionMenu(menu, {{clientX: menu.style.left, clientY: menu.style.top}});
}}

function positionMenu(menu, event) {{
    menu.style.display = 'block';
    const x = (typeof event.clientX === 'number') ? event.clientX : parseFloat(menu.style.left) || 0;
    const y = (typeof event.clientY === 'number') ? event.clientY : parseFloat(menu.style.top) || 0;
    const mw = menu.offsetWidth, mh = menu.offsetHeight;
    let left = x, top = y;
    if (left + mw > window.innerWidth - 8) left = Math.max(8, window.innerWidth - mw - 8);
    if (top + mh > window.innerHeight - 8) top = Math.max(8, window.innerHeight - mh - 8);
    menu.style.left = left + 'px';
    menu.style.top = top + 'px';
}}

function selectPattern(patternName) {{
    if (currentPage) {{
        const page = storyboard.pages[currentPage - 1];
        page.pattern = patternName;
        const card = document.querySelector('.card[data-page="' + currentPage + '"]');
        if (card) {{
            card.dataset.pattern = patternName;
            const nameEl = card.querySelector('.card-pattern');
            if (nameEl) nameEl.textContent = patternName;
            const img = card.querySelector('img');
            const tpl = findTplImg(patternName);
            if (img && tpl) {{ img.dataset.failed = ''; img.style.opacity = 1; img.src = tpl; }}
        }}
        refreshStats();
        toast('已切换为 ' + patternName);
    }}
    closeMenu();
}}

function findTplImg(patternName) {{
    for (const intent in intentGroups) {{
        for (const item of intentGroups[intent].items) {{
            if (item.name === patternName && item.tpl_img) return item.tpl_img;
        }}
    }}
    return null;
}}

function closeMenu() {{
    const menu = document.getElementById('contextMenu');
    if (menu) menu.style.display = 'none';
    currentPage = null;
}}

function toast(msg) {{
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.style.opacity = 1;
    clearTimeout(t._timer);
    t._timer = setTimeout(() => {{ t.style.opacity = 0; }}, 1600);
}}

function refreshStats() {{
    const STRUCTURAL = ['cover','toc','section','thanks','refs'];
    const usage = {{}};
    let adjacent = 0;
    for (let i = 0; i < storyboard.pages.length; i++) {{
        const p = storyboard.pages[i].pattern;
        usage[p] = (usage[p] || 0) + 1;
        if (i > 0 && storyboard.pages[i - 1].pattern === p &&
            STRUCTURAL.indexOf(p) < 0) adjacent++;
    }}
    let dupPatterns = 0, dupPages = 0;
    for (const p in usage) {{
        if (usage[p] > 1 && STRUCTURAL.indexOf(p) < 0) {{
            dupPatterns++;
            dupPages += usage[p];
        }}
    }}
    const uniq = Object.keys(usage).length;
    const el = document.getElementById('stats');
    let txt = '共 ' + storyboard.pages.length + ' 页 · 版式 ' + uniq + ' 种';
    if (adjacent > 0) txt += ' <span class="bad">· 相邻重复 ' + adjacent + ' 处</span>';
    else txt += ' <span class="ok">· 无相邻重复</span>';
    if (dupPatterns > 0) txt += ' <span class="bad">· 重复使用 ' + dupPatterns + ' 种/占 ' + dupPages + ' 页</span>';
    el.innerHTML = txt;
    // 更新卡片角标
    document.querySelectorAll('.card').forEach(card => {{
        const p = storyboard.pages[parseInt(card.dataset.page, 10) - 1].pattern;
        const n = usage[p] || 0;
        let badge = card.querySelector('.dup-badge');
        if (n > 1 && STRUCTURAL.indexOf(p) < 0) {{
            if (!badge) {{
                badge = document.createElement('span');
                badge.className = 'dup-badge';
                card.querySelector('.thumb-wrap').appendChild(badge);
            }}
            badge.textContent = '×' + n;
        }} else if (badge) {{
            badge.remove();
        }}
    }});
}}

function collectIssues() {{
    const issues = [];
    for (let i = 0; i < storyboard.pages.length; i++) {{
        const page = storyboard.pages[i];
        const item = findPatternItem(page.pattern);
        if (item) {{
            const c = checkCompat(item, page);
            if (c.bads.length || c.warns.length) {{
                issues.push('第 ' + (i + 1) + ' 页 [' + page.pattern + ']: '
                    + c.bads.concat(c.warns).join('; '));
            }}
        }} else {{
            issues.push('第 ' + (i + 1) + ' 页: 版式 "' + page.pattern + '" 不在版式库中');
        }}
    }}
    return issues;
}}

function findPatternItem(name) {{
    for (const intent in intentGroups) {{
        for (const item of intentGroups[intent].items) {{
            if (item.name === name) return item;
        }}
    }}
    return null;
}}

function exportStoryboard() {{
    const issues = collectIssues();
    const modal = document.getElementById('modalMask');
    const body = document.getElementById('modalBody');
    let h = '<h3>导出前体检</h3>';
    if (issues.length) {{
        h += '<ul>';
        for (const it of issues) h += '<li class="bad-item">' + ESC(it) + '</li>';
        h += '</ul><p>以上页面建议修正后再导出（渲染器会兜底替换未知版式，但不兼容槽位会留空）。</p>';
    }} else {{
        h += '<p style="color:#2e7d32">✅ 全部 ' + storyboard.pages.length + ' 页版式兼容，无缺失。</p>';
    }}
    h += '<div class="modal-actions"><button onclick="closeModal()">取消</button>'
        + '<button class="primary" onclick="doDownload()">仍要导出</button></div>';
    body.innerHTML = h;
    modal.style.display = 'flex';
}}

function closeModal() {{
    document.getElementById('modalMask').style.display = 'none';
}}

function doDownload() {{
    closeModal();
    const blob = new Blob([JSON.stringify(storyboard, null, 2)], {{type: 'application/json'}});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'storyboard.json';
    a.click();
    URL.revokeObjectURL(url);
    toast('已导出 storyboard.json');
}}

document.addEventListener('click', (e) => {{
    if (!e.target.closest('.card') && !e.target.closest('.context-menu')) closeMenu();
}});
document.addEventListener('keydown', (e) => {{
    if (e.key === 'Escape') {{ closeMenu(); closeModal(); }}
}});
document.addEventListener('contextmenu', (e) => {{
    if (!e.target.closest('.card') && !e.target.closest('.context-menu')) e.preventDefault();
}});
refreshStats();
</script>
</body>
</html>
"""

    # 注入序列化数据（转义 </script>；占位符含花括号，整块替换避免多余括号）
    html = html.replace("{JS_STORYBOARD}", js_str(sb))
    html = html.replace("{JS_GROUPS}", js_str(intent_groups))
    html = html.replace("{JS_SLOTS}", js_str(slot_sets))
    html = html.replace("{FALLBACK_B64}", FALLBACK_B64)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 已生成 {args.out}")


if __name__ == "__main__":
    main()

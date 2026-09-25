# PPTX 渲染套件（含内容意图层）

本项目将 `storyboard.json` + `patterns.json` + `template.pptx` 渲染为 PPTX，新增「内容意图（intent）层」：生成模型只写 intent（如 `points-3`），由解析器自动映射为具体版式（如 `text-3`、`steps-3`、`mockup-3`）。

## 📁 文件结构

```
pptx-kit/
├── README.md                    # 本文件
├── render_pptx.py               # 主渲染器（已集成 intent 解析）
├── patterns.json                 # 版式槽位映射（49个pattern）
├── layout_index.json            # intent 分类表（39个intent）
├── resolve_intents.py           # intent → pattern 解析器
├── optimize_layout.py           # 版式多样性后处理（相邻不重复/频次上限）
├── export_thumbs.py             # PPTX 导出缩略图
├── make_viewer.py               # 生成 viewer.html
├── verify_pptx.py               # 渲染产物自动质检（页数/占位残留/字段对位/图表数据）
├── validate_layout_index.py     # layout_index 校验脚本
├── template.pptx                # 49种版式模板（assets/）
└── examples/
    └── storyboard.sample.json    # 示例 storyboard
```

## 目录结构

```
pptx-kit/
├── README.md               ← 本文件
├── 使用手册-Web大模型版.md  ← 保姆级教程：只用网页版大模型 + 一条命令出片
├── PROMPT.md               ← 发给任意通用大模型的提示词（含版式目录与字数上限）
├── storyboard.schema.json  ← storyboard 的 JSON Schema（结构约束）
├── patterns.json           ← 版式槽位映射（版式id → 模板页码 + 形状索引）
├── render_pptx.py          ← 渲染器（唯一需要跑的脚本）
├── assets/template.pptx    ← 版式库模板（70 页单页版式，49 种已接入）
└── examples/storyboard.sample.json  ← 示例分页脚本
```

## 🚀 使用流程

### 1. 生成 PPTX（含 intent 解析）

```bash
# 基础用法（自动探测 layout_index.json）
python render_pptx.py storyboard.json -o output.pptx

# 指定 layout_index（如不在同目录）
python render_pptx.py storyboard.json -l custom_layout.json -p custom_patterns.json -o output.pptx

# 列出所有可用版式
python render_pptx.py --list-patterns
```

### 2. 导出缩略图

```bash
# 导出 deck 缩略图
python export_thumbs.py output.pptx -o thumbs/

# 导出模板 pattern 缩略图（tpl_前缀）
python export_thumbs.py template.pptx --pattern-only -o tpl_thumbs/

# 自定义尺寸和前缀
python export_thumbs.py output.pptx -o thumbs/ -w 1920 -h 1080 --prefix slide
```

### 3. 生成可视化版式切换器

```bash
# 生成 viewer.html（需先导出缩略图）
python make_viewer.py storyboard.json -o viewer.html

# 指定缩略图目录
python make_viewer.py storyboard.json -t thumbs/ --tpl-thumbs tpl_thumbs/ -o viewer.html
```

### 4. 校验 layout_index

```bash
# 检查 layout_index.json 与 patterns.json 双向包含
python validate_layout_index.py
```

## 📋 新增版式三步法

如需添加新版式，只需修改以下三个文件，**无需改动任何 Python 代码**：

### 步骤 1：修改 `patterns.json`
- 添加新版式定义，包含 `slide`（模板页码）、`desc`、`text_slots`、`image_slots` 等。
- 示例：
  ```json
  "my-new-layout": {
    "slide": 50,
    "desc": "我的新版式",
    "text_slots": { "title": 0, "content": 1 }
  }
  ```

### 步骤 2：修改 `layout_index.json`
- 在对应 intent 的 `candidates` 中添加新版式名。
- 示例：
  ```json
  "points-2": {
    "desc": "两列布局",
    "candidates": ["text-2", "my-new-layout"]
  }
  ```

### 步骤 3：更新 `template.pptx`
- 在模板 PPTX 中添加新版式页面，确保页码与 `patterns.json` 中的 `slide` 一致。

## 🔧 技术细节

### Intent 解析规则

解析器按以下规则为 intent 选择具体 pattern：

1. **字段兼容（硬条件）**：候选 `text_slots` 必须包含本页 `fields` 的所有 key。
2. **图片匹配**：本页有 `images` → 候选有 `image_slots` 得 1 分；否则无得 1 分。
3. **槽位贴近**：候选槽位数与字段数之差越小越好（`-extra_slots`）。
4. **视觉节奏**：最近 2 页用过的 pattern 扣 1 分。

**确定性**：同分按 pattern 名升序排序，保证每次结果一致。

### 向后兼容

- 旧 `storyboard.json`（`pattern` 写具体名）继续可用，无需修改。
- `layout_index.json` 不存在时，`render_pptx.py` 行为与原来完全一致。

### 缩略图导出策略

按优先级自动选择导出方式：

1. **win32com.client**（Windows + PowerPoint）：最快最保真。
2. **LibreOffice + PyMuPDF**：跨平台。
3. **Pillow 离线兜底**：最慢但始终可用。

### viewer.html 特性

- 纯静态，无 CDN，无网络依赖，双击即用。
- 右键菜单显示同类候选，支持字段兼容性提示。
- 点击候选实时更新，导出完整 JSON。
- 图片失败自动降级显示灰块。

## 📝 示例

### Intent 版 storyboard.json

```json
{
  "title": "我的论文",
  "pages": [
    {
      "pattern": "cover",
      "fields": {
        "title": "基于深度学习的文本分类",
        "en": "Deep Learning for Text Classification",
        "advisor": "指导老师：张三",
        "presenter": "答辩人：李四"
      }
    },
    {
      "pattern": "points-3",
      "fields": {
        "title": "三个创新点",
        "s1": "创新点1",
        "b1": "详细描述...",
        "s2": "创新点2",
        "b2": "详细描述...",
        "s3": "创新点3",
        "b3": "详细描述..."
      }
    }
  ]
}
```

解析后自动映射为具体 pattern（如 `text-3`、`steps-3` 等）。

### 现有 pattern 版 storyboard.json

```json
{
  "title": "我的论文",
  "pages": [
    {
      "pattern": "text-3",
      "fields": {
        "title": "三个创新点",
        "s1": "创新点1",
        "b1": "详细描述...",
        "s2": "创新点2",
        "b2": "详细描述...",
        "s3": "创新点3",
        "b3": "详细描述..."
      }
    }
  ]
}
```

继续正常工作，无变化。

## 🔍 故障排查

### 常见问题

1. **解析失败**：检查 `layout_index.json` 中 candidates 是否都在 `patterns.json` 中。
2. **字段不兼容**：候选 pattern 的 `text_slots` 必须包含本页所有 `fields`。
3. **缩略图导出失败**：确保安装了 PowerPoint/LibreOffice 或 Pillow 可用。
4. **viewer.html 无法打开**：确保缩略图目录存在且图片路径正确。

### 调试模式

- `render_pptx.py` 会输出 `_unresolved_intents` 列表。
- `validate_layout_index.py` 详细报告双向包含情况。

## 许可与致谢

模板来自《最全按模式选单页模板001》（作者：陈伟佳/千阳，广东财经大学），
模板内含字体/图片/素材版权说明页，商用前请自行确认授权。

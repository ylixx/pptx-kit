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
├── checks.py                    # 共享校验（render 告警 / verify 判 FAIL）
├── export_thumbs.py             # PPTX 导出缩略图
├── make_viewer.py               # 生成 viewer.html
├── verify_pptx.py               # 渲染产物自动质检（页数/占位残留/字段对位/图表数据）
├── validate_layout_index.py     # layout_index 校验脚本
├── scan_layouts.py              # 模板新版式 → patterns.json 槽位映射自动生成（含 --check 漂移校验 / --inventory 全模板盘点）
├── tests/run_tests.py           # 自动化回归测试（39 intent 全链路）
├── tests/test_scan_layouts.py   # scan_layouts.py 专项测试
├── tests/test_make_viewer.py    # make_viewer.py 专项测试
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

### 5. 质检渲染产物

```bash
# 页数/zip/占位残留/字段对位/图表数据/notes 全覆盖检查
python verify_pptx.py storyboard.json output.pptx
```

### 6. 版式多样性后处理（可选，渲染前）

```bash
# 消除相邻重复、压制高频版式（自动保证字段兼容、无图不选 mockup-3）
python optimize_layout.py storyboard.json -o storyboard.opt.json
python render_pptx.py storyboard.opt.json -o output.pptx
```

### 7. 自动化回归测试

```bash
python tests/run_tests.py   # 纯标准库；39 intent 全链路 + 错误处理回归
```

## 📋 新增版式三步法（含自动生成工具）

添加新版式**无需改动任何 Python 代码**；`scan_layouts.py` 可把"手工写 JSON"这一步自动化。

### 步骤 1：在模板中加页 + 运行扫描工具（替代手工写 `patterns.json`）

在 `assets/template.pptx` 末尾追加新版式页，并给页面上每个**槽位形状重命名**为槽位 key
（PowerPoint「选择窗格」中双击形状名）：`title`/`s1`/`b1`/`img1` 等；图片/图表/表格形状
直接命名即可，工具会自动识别类型。然后运行：

```bash
# 命名扫描（推荐）：自动按形状命名识别 text/image/chart/table 槽位并写回
python scan_layouts.py --page 71 --id text-3icon --desc "三卡片带图标" --intent points-3

# 快速映射（不重命名时）：直接给"形状索引=槽位key"
python scan_layouts.py --page 71 --id text-3icon --map "title=0,s1=1,b1=2,img1=3" --intent points-3

# 交互映射：逐个形状分配槽位
python scan_layouts.py --page 71 --id text-3icon --interactive
```

`--intent points-3` 会同时更新 `layout_index.json`（加入候选）和
`storyboard.schema.json`（enum 追加）。`--dry-run` 只预览不写文件；写回前自动备份 `.bak`。

也可完全手工修改 `patterns.json`（条目格式见下）：

```json
"my-new-layout": {
  "slide": 50,
  "desc": "我的新版式",
  "text_slots": { "title": 0, "content": 1 }
}
```

### 步骤 2：把新版式挂到 intent 候选（`--intent` 已自动完成）

在 `layout_index.json` 对应 intent 的 `candidates` 中添加新版式名：

```json
"points-2": {
  "desc": "两列布局",
  "candidates": ["text-2", "my-new-layout"]
}
```

### 步骤 3：模板页就位

确认 `template.pptx` 中新增页页码与 `patterns.json` 中 `slide` 一致（步骤 1 已指定 `--page`）。

### 全模板版式盘点（找"藏着的"版式）

模板里往往有比 `patterns.json` 更多的可用版式页。一键盘点（借鉴
`pptx-from-layouts-skill` 的 profile 思路：结构指纹 + 启发式用途推断）：

```bash
python scan_layouts.py --inventory
```

输出：①**版式族聚类**——结构指纹相同的页归为一族，直接显示"已接入 N 页，
未接入 M 页"（如 `指纹(文本4 图0 图表0 表0) → 页[3,4,5,6,7,8] · 已接入1页，
未接入5页`，即 6 个章节页变体只用了 1 个）；②逐页明细含**文本预览**（用于
区分真正的版式页与使用说明页）；③未接入候选页清单。

发现可用版式后，按上文步骤 1 用 `--page N --map` 或命名扫描录入即可。

### 校验既有映射是否漂移

模板页被改动（增删形状）后，既有 `patterns.json` 的索引可能失效，运行：

```bash
python scan_layouts.py --check
```

零漂移时输出 `✅`；任何索引越界或类型不匹配都会逐条报告。

### 专项测试

```bash
python tests/test_scan_layouts.py   # scan_layouts.py：索引/同步/盘点/冲突
python tests/test_make_viewer.py    # make_viewer.py：生成/结构/JS 语法/统计
```

## 🔧 技术细节

### Intent 解析规则

解析器按以下规则为 intent 选择具体 pattern：

1. **字段兼容（硬条件）**：候选 `text_slots` 必须包含本页 `fields` 的所有 key。
2. **图片匹配**：本页有 `images` → 候选有 `image_slots` 得 1 分；否则无得 1 分。
3. **槽位贴近**：候选槽位数与字段数之差越小越好（`-extra_slots`）。
4. **视觉节奏**：最近 2 页用过的 pattern 扣 1 分。

**确定性**：同分按 pattern 名升序排序，保证每次结果一致。

**失败兜底**：若某 intent 的全部候选都不满足字段兼容（如模型多写了字段），解析器保留原
intent 名并记入 `_unresolved_intents`；渲染器遇到未知 pattern 时会自动兜底替换为
字段兼容版式（或跳过并汇总告警），**不再中断整份渲染**。图表数据长度不一致时渲染器
告警并截断到较短者，质检判 FAIL。

### 向后兼容

- 旧 `storyboard.json`（`pattern` 写具体名）继续可用，无需修改。
- `layout_index.json` 不存在时，`render_pptx.py` 行为与原来完全一致。

### 缩略图导出策略

按优先级自动选择导出方式：

1. **win32com.client**（Windows + PowerPoint）：最快最保真。需先装 pywin32：
   `python -m pip install pywin32`（务必用 `python -m pip`，与当前解释器同环境）。
   新版 Office 禁止隐藏窗口，工具已自动改为可见模式并跳过该限制；
   COM 导出要求目标为绝对路径（工具已处理）。
2. **LibreOffice + PyMuPDF**：跨平台。
3. **Pillow 离线兜底**：最慢但始终可用（无 Office 时仅渲染图片/白底占位，建议装 PowerPoint 获得真实缩略图）。

### viewer.html 特性

- 纯静态，无 CDN，无网络依赖，双击即用。
- **左键 / 右键**点卡片弹出版式菜单（按 intent 分组，候选带模板缩略图与描述）。
- **兼容性三路检查**：文本槽 / 图片槽 / 图表表格需求逐项判定，缺字段标红、缺图与缺数据标黄。
- 「更多版式…」展开全部 intent，顶部可返回；点选候选实时更新卡片并 toast 提示。
- **版式体检**：重复版式自动标角标（×N），工具栏实时统计「版式 N 种 · 相邻重复 K 处 · 重复使用 X 种/占 Y 页」；导出前弹窗逐页列出不兼容项供确认。
- 图片失败自动降级显示灰块，不崩页面；JS 数据注入已转义 `</script>`。

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

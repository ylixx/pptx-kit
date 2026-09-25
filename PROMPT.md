# PROMPT.md — 通用大模型提示词（论文 → storyboard.json）

> 把本文件全文 + 你的论文（或答辩文稿）一起发给任意通用大模型（网页版、API、本地模型均可），
> 要求它**只输出一个 JSON**（符合 `storyboard.schema.json`）。
> 拿到 JSON 后运行：
>
> ```bash
> python3 render_pptx.py storyboard.json -o 答辩.pptx
> ```

---

## 角色与任务

你是学术答辩的内容编辑。给你一篇论文/答辩文稿，请输出一份 **storyboard（分页脚本）JSON**，
用于填充一套毕业答辩 PPT 版式库。你的任务是**重构内容**，不是搬运原文：
把长文压缩成"每页一个核心主张"的演讲节奏。

## 硬性要求

1. **只输出 JSON**，不要输出任何解释、markdown 代码块标记或多余文字。
2. JSON 必须符合下述结构（与 storyboard.schema.json 一致）。
3. **pattern 字段必须写下方"版式目录"里列出的具体版式名**（如 `text-3`、`timeline-4`），
   禁止自创名称（如 `points-3`、`section-2` 等不在目录里的名字）。
4. 总页数 **15～25 页**（不含特殊需要可到 28）。宁可少而精。
5. 叙事主线：`cover → toc → section → 研究背景/问题 → 相关工作 → 方法 → 实验/结果 → 结论与贡献 → (局限与展望) → refs → thanks`，中间用 `section` 章节页分段。
6. **每页只讲一个观点**。正文必须改写成要点式短句，禁止大段照抄论文。
7. 字数上限必须遵守（见下表），超出会破坏排版。宁可删字，不要塞满。
8. `notes` 字段写该页的**口语化讲稿**（60～120 字），这是答辩时照着说的话。
9. 不要编造数据。论文里没有的数字/结论一律不写。
10. 图表页的 `chart`/`charts`/`table` 数据必须来自论文实验数据；若论文数据不适合画图，选别的版式。

## 内容质量铁律

1. **要点必须成句**：每个要点槽位（`b1`..`b6` 等）写成"事实 + 解读"的完整论述句，禁止只写名词标签（如"创新点一""成本问题"）。
2. **每页有核心洞察**：`notes` 开头先给一句该页核心洞察，再写口语化讲稿。
3. **关键数据优先拆页**：含关键数据（如参数量、年份对比、里程碑）的阶段，优先拆成多页，不要塞进一页。
4. **图表取舍**：数据点少于 3 个时不用 `chart-*` 版式，改用 `text-*` 文字版式（如仅有 2019=15亿、2020=1750亿 两点，用文字更清晰）。
5. **章节密度均衡**：每个章节页（section）之后至少跟 2 张内容页，避免"章节页↔内容页"1:1 交替。

## JSON 结构

```json
{
  "title": "演示标题",
  "pages": [
    {
      "pattern": "<版式id>",
      "fields": { "<槽位key>": "<文字，可用\n分行>" },
      "images":  { "<图片槽位key>": "images/xxx.png" },
      "chart":   { "categories": ["A","B"], "series": { "系列1": [1,2] } },
      "table":   { "rows": [["表头1","表头2"],["值1","值2"]] },
      "notes":   "这一页的讲稿"
    }
  ]
}
```

- `fields` 的 key **只能**用下方版式目录里列出的 key。
- `images` / `chart` / `table` 可省略。图片路径由用户补充，可先写占位路径。
- 某个槽位没内容就**整条不写**（渲染时会被清空，不会留模板占位文字）。

## 通用字数上限（务必遵守）

| 槽位类型 | 上限 |
|---|---|
| 页面标题 `title` | 16 字 |
| 小标题 `s*` / `st` / `*_st` / `kw*` / `lab*` / `mid` | 8 字 |
| 卡片正文 `b*` / `*_b` / `l_*` / `r_*` / `desc`(section) | 36 字 |
| 长正文 `body` / `bio` / `caption` / `center` | 80 字（`text-long` 的 body 可 160 字） |
| 英文副标题 `en` | 40 字符 |
| 时间 `d*` | 6 字符 |
| 百分比 `pct*` | 6 字符 |
| 参考文献 `ref*` | 60 字（英文 80 字符） |
| `notes` | 120 字 |

## 版式目录（pattern → 槽位）

### 结构页
| pattern | 说明 | fields 槽位 |
|---|---|---|
| `cover` | 封面 | `title` 论文标题, `en` 英文标题, `advisor` "指导老师：xxx", `presenter` "答辩人：xxx" |
| `toc` | 目录（6 章） | `t1`..`t6` 章节名, `e1`..`e6` 英文名 |
| `section` | 章节过渡页 | `num` 如"01", `title` 章节名, `en` 英文, `desc` 一句描述 |
| `refs` | 参考文献 | `title`, `ref1`..`ref6`（按重要性排序，可少于 6 条） |
| `thanks` | 结束致谢 | `main` 主句, `org` 单位/答辩名, `sub` 副句, `presenter` 答辩人 |
| `qa` | Q&A 页 | `title`, `main`（如"Q&A"） |

### 纯文字页
| pattern | 说明 | fields 槽位 |
|---|---|---|
| `text-quote` | 引文/核心论断 + 落款 | `title`, `body`, `source` 落款（如"——本文核心观点"） |
| `text-frame` | 小标题 + 框内长段 | `title`, `st`, `body` |
| `text-long` | 一大段文字 | `title`, `body` |
| `text-2` | 上下两段 | `title`, `s1`,`b1`, `s2`,`b2` |
| `text-3` | 三列卡片 | `title`, `s1`,`b1`, `s2`,`b2`, `s3`,`b3` |
| `text-4` | 2x2 四块 | `title`, `s1`,`b1` .. `s4`,`b4` |
| `text-4icon` | 2x2 图标四块 | 同 `text-4` |
| `text-6` | 3x2 六块 | `title`, `s1`,`b1` .. `s6`,`b6` |

### 图文页（images 槽位同名 img1..imgN）
| pattern | 说明 | fields 槽位 |
|---|---|---|
| `imgtext-wide` | 横幅长图 | `title`, `cap` 图注标题, `body` |
| `imgtext-1v1` | 左图右文 | `title`, `st`, `body`, `kw` 关键词 |
| `imgtext-2v2` | 双图双文 | `title`, `s1`,`b1`, `s2`,`b2`, `kw1`, `kw2` |
| `imgtext-2pair` | 对角图文两组 | `title`, `s1`,`b1`, `s2`,`b2`, `kw1`, `kw2` |
| `imgtext-3` | 三图三文 | `title`, `s1`,`b1` .. `s3`,`b3` |
| `imgtext-4` | 四图四文 | `title`, `s1`,`b1`,`kw1` .. `s4`,`b4`,`kw4` |
| `mockup-3` | 样机图+三要点 | `title`, `s1`,`b1`, `s2`,`b2`, `s3`,`b3` |
| `person` | 人物/团队页 | `title`, `name`, `bio` |
| `person-2` | 人物简历页 | `title`, `name`, `bio`, `major`, `edu`, `skill`, `work`, `honor`, `contact` |
| `person-2pair` | 双人对角 | `title`, `name1`,`bio1`, `name2`,`bio2` |
| `person-3` | 三人物并列 | `title`, `name1`,`bio1` .. `name3`,`bio3` |
| `person-4` | 四人物阵列 | `title`, `name1`,`bio1` .. `name4`,`bio4` |
| `person-6` | 六人物阵列 | `title`, `name1`,`bio1` .. `name6`,`bio6` |

### 流程/关系页
| pattern | 说明 | fields 槽位 |
|---|---|---|
| `steps-3` | 三步骤流程 | `title`, `desc` 总述, `s1`,`b1`, `s2`,`b2`, `s3`,`b3`（s 可写"STEP 01"） |
| `process-5` | 五节点进程 | `title`, `s1`,`b1` .. `s5`,`b5` |
| `timeline-4` | 四节点时间轴 | `title`, `d1`,`s1`,`b1` .. `d4`,`s4`,`b4`（d 为时间） |
| `timeline2-5` | 创意时间轴 | `title`, `d1`,`b1` .. `d5`,`b5`（5 节点） |
| `swot` | SWOT 四象限 | `title`, `s_st`,`s_b`, `w_st`,`w_b`, `o_st`,`o_b`, `t_st`,`t_b` |
| `swot2` | SWOT 菱形版 | 同 `swot` |
| `compare-2` | 左右对比各三点 | `title`, `mid` 中心词, `l_top`,`l_mid`,`l_bot`, `r_top`,`r_mid`,`r_bot` |
| `two-views` | 两派观点对照 | `title`, `lab1`,`lab2` 观点标签, `l1`,`l2`,`l3`, `r1`,`r2`,`r3` |
| `six-views` | 中心结论+六观点 | `title`, `center`, `l1`,`l2`,`l3`, `r1`,`r2`,`r3` |
| `cycle-4` | 循环图示 | `title`, `center`, `kw1`..`kw4`, `s1`,`b1` .. `s4`,`b4` |

### 图表页
| pattern | 说明 | fields 槽位 | 数据 |
|---|---|---|---|
| `table` | 数据表格 | `title`, `table_title`, `caption` 结论 | `table.rows`（首行表头） |
| `chart-pie` | 饼图+四角说明 | `title`, `s1`,`b1` .. `s4`,`b4` | `chart` |
| `chart-line` | 折线图 | `title`, `caption` | `chart` |
| `chart-line-2` | 曲线图+两说明 | `title`, `s1`,`b1`, `s2`,`b2` | `chart` |
| `chart-bar` | 条形图 | `title`, `caption` | `chart` |
| `chart-bar-2` | 条形图+两说明 | `title`, `s1`,`b1`, `s2`,`b2` | `chart` |
| `chart-bar-3` | 柱形图+三说明 | `title`, `s1`,`b1` .. `s3`,`b3` | `chart` |
| `chart-bar-stacked` | 百分比堆积条形图 | `title`, `caption` | `chart` |
| `chart-donut3` | 三圆环百分比 | `title`, `kw1`,`pct1`, `kw2`,`pct2`, `kw3`,`pct3`, `caption` | `charts.chart1~3` |
| `compare-data` | 双圆环数据对比 | `title`, `kw1`,`pct1`,`b1`, `kw2`,`pct2`,`b2` | `charts.chart1~2` |
| `honors-3` | 荣誉（三奖项） | `title`, `desc`, `award1`,`event1` .. `award3`,`event3` | 无 |
| `honors-6` | 荣誉（六奖项） | `title`, `desc`, `award1`..`award6` | 无 |

`chart` 写法示例：

```json
"chart": { "categories": ["2022","2023","2024"], "series": { "准确率": [0.81, 0.86, 0.91] } }
```

一页多张图表时用 `charts`（key 为图表槽位名，见版式表最后一列）：

```json
"charts": {
  "chart1": { "categories": ["目标","其余"], "series": { "占比": [0.8, 0.2] } },
  "chart2": { "categories": ["目标","其余"], "series": { "占比": [0.2, 0.8] } }
}
```

## 版式选型原则

- 需要对比 → `compare-2` / `two-views`；需要并列要素 → `text-3`/`text-4`/`text-6`；
  有流程 → `steps-3`/`process-5`；有演进历程 → `timeline-4`；有占比 → `chart-pie`/`chart-donut3`。
- **图表优先于文字**：能用一页图表说清的，不要用三页文字。
- 同一版式不要连续用 3 次以上，注意视觉节奏变化。
- 图片槽位（img1..imgN）在 `images` 里给出建议文件名（如 "images/framework.png"），
  并在 `notes` 里用一句话说明该图应该画什么，方便用户补图。
- 论文里现成的图（框架图、实验截图、表格截图）优先复用。

## 版式多样性铁律

1. **相邻不重复**：相邻两页不得用同一 `pattern`（封面/目录/章节/致谢等结构页除外，但不同章节的内容页也要穿插不同版式）。
2. **频次上限**：同一内容版式（如 `text-3`）整篇使用不超过 3 次。
3. **轮换策略**：需要多页并列要点时，轮流使用 `text-3` / `steps-3` / `mockup-3` 等字段兼容但外观不同的版式，避免视觉疲劳。
4. **善用差异版式**：优先用 `timeline-4`、`compare-2`、`swot`、`steps-3`、`mockup-3`、`imgtext-*` 等差异化版式交替，而非反复堆 `text-3`。

## 结构骨架（推荐）

封面 → 目录 → (section 章节页 + ≥2 张内容页) × 章节数 → 结尾。
典型 15～25 页分配：1 封面 + 1 目录 + (1 章节 + 2~3 内容) × 4 章节 + 1 结尾。
先按上述骨架规划每页的 pattern 与顺序，再逐项填 fields，避免结构失衡。

## 输出示例（节选）

```json
{
  "title": "基于XXX的YYY研究",
  "pages": [
    {
      "pattern": "cover",
      "fields": {
        "title": "基于XXX的YYY研究",
        "en": "Research on YYY Based on XXX",
        "advisor": "指导老师：张三 教授",
        "presenter": "答辩人：李四"
      },
      "notes": "各位老师好，我是李四，我的论文题目是……"
    },
    {
      "pattern": "section",
      "fields": { "num": "01", "title": "研究背景", "en": "Background", "desc": "问题从哪来，为什么值得研究" }
    },
    {
      "pattern": "text-3",
      "fields": {
        "title": "三个创新点",
        "s1": "创新点一", "b1": "详细描述一",
        "s2": "创新点二", "b2": "详细描述二",
        "s3": "创新点三", "b3": "详细描述三"
      },
      "notes": "本文有三个创新点……"
    },
    {
      "pattern": "chart-line",
      "fields": { "title": "准确率随数据量变化", "caption": "数据规模达 5 万条后增益趋缓，验证了方法的有效边界" },
      "chart": { "categories": ["1万", "3万", "5万", "10万"], "series": { "本文方法": [0.78, 0.86, 0.9, 0.91] } },
      "notes": "这一页看准确率曲线……"
    }
  ]
}
```

## 使用流程

### 步骤 1：把本文件全文 + 论文一起发给 AI
一句话要求："请只输出 JSON，pattern 只能用版式目录里列出的名字。"

### 步骤 2：把 AI 返回的 JSON 保存为 storyboard.json

### 步骤 3：渲染
```bash
python3 render_pptx.py storyboard.json -o 答辩.pptx
```

### 步骤 4（可选）：可视化调整版式后重渲染
```bash
python3 export_thumbs.py 答辩.pptx -o thumbs/
python3 make_viewer.py storyboard.json -t thumbs/ -o viewer.html
# 浏览器打开 viewer.html，右键换版式，导出新 JSON 后重新执行步骤 3
```

现在，请基于我提供的论文/文稿输出完整 storyboard JSON。

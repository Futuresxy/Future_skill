# 图描述格式与导出

`scripts/render_diagram.py` 使用 Python 3 标准库读取 UTF-8 JSON，写出自包含 SVG，无须 PyTorch、模型权重或网络。它按显式坐标绘图，只对简单 `from/to` 边提供正交转折；不是自动图布局引擎。优先查看 `assets/example.architecture.json`、对应示例源码和分析文件，再按目标结构改写。

在技能根目录执行：

```bash
python3 scripts/render_diagram.py assets/example.architecture.json --output example.svg
```

也可从任意目录使用脚本和输入文件的绝对路径。`evidence` 是作为 SVG `<title>` 保存的来源文本，不会加载或执行对应文件。

## 顶层字段

| 字段 | 说明 |
| --- | --- |
| `title` | 必填，模型名、变体，必要时标注模式；固定置于 y=46 |
| `source_note` | 必填，一行简短来源/版本；置于 y=76，长链接放分析文件 |
| `width`, `height` | 必填，正的逻辑像素尺寸；正文布局从 y≈120 开始 |
| `panels` | 分组容器，按数组顺序绘制 |
| `nodes` | 必填且非空，计算节点 |
| `edges` | 数据流、残差、路由、状态、展开引线 |
| `labels` | 自由放置的形状、参数、图例和说明 |

所有对象必须有唯一 `id`，符合 `[A-Za-z_][A-Za-z0-9_.-]*`。`arrow`、`diagram-title` 为保留 ID。`role` 取 `backbone/attention/ffn/moe/vision/detail/cache/neutral` 或六位十六进制色值。默认色表见风格参考；自定义颜色可配 `text_color` 保证对比度。

## 面板与节点

面板：`id, x, y, w, h, label, role`。左上角为 `(x,y)`，宽高为 `(w,h)`，虚线边框不表示执行条件；标题在面板左上角。嵌套面板需手动设置坐标与留白。

节点：`id, x, y, w, h, label, role, evidence`；可选 `shape, font_size, text_color`。

| shape | 含义 |
| --- | --- |
| `box` | 默认实心圆角操作框 |
| `outline` | 空心虚线抽象模块框；不自动生成展开关系 |
| `add`, `multiply` | 加法/逐元素乘法节点，自带 + / ×；建议 w=h |
| `up`, `down` | 自下而上读取时的升/降维梯形；维度相等用 box |

`label` 可含 `\n` 手动换行；脚本不自动换行或测量字体。`evidence` 填来源路径与行号/报告页，例如 `src/model.py:140-153; config.json:10-22`，或 `report.pdf p.12 eq.(3)`。精确状态和解释写在分析文件；SVG 提示文本只是快捷索引。

## 边

可用显式折线路径，或从节点端口连接：

```json
{
  "id": "norm_to_attn",
  "from": "norm1",
  "to": "attention",
  "from_port": "top",
  "to_port": "bottom",
  "kind": "data",
  "evidence": "src/model.py:152"
}
```

端口取 `top/bottom/left/right`，默认 `top → bottom`，适合自下而上。不同 x 时默认通过中间高度折线。残差、分叉、cache 等复杂路径推荐手写 `points: [[x1,y1],[x2,y2],...]`；有 points 时优先使用它，不会自动吸附节点。手动校验端点位于正确框边，分叉来源确实连接，避免把经过但不相接的线当成连接点。

`kind` 默认为 `data`：

- `data/residual/state`：实线箭头。
- `route/optional`：虚线箭头，配明确文字解释 top-k 或条件。
- `callout`：无箭头虚线，仅表示展开关系，允许没有 evidence。

边的 `role` 决定线色。所有计算边需要 `evidence`。可加 `label`，同时给出 `label_x, label_y`；可选 `font_size`（默认 15）及 `anchor`（`start/middle/end`）。不支持双向箭头：cache read 与 write 分成两条边分别标注。无向的面板引线不要代替数据流。

## 标签

`id, x, y, text`；可选 `font_size`（默认 16）、`role`、`anchor`、`bold`。`y` 是首行基线，不是文字框顶部，多行向下延伸。脚本按“面板 → 边 → 节点 → 标签”绘制；标签不自动避让连线。

## PNG 导出与复核

使用环境已有工具。例如 CairoSVG 已可用时：

```bash
python3 -c "import cairosvg; cairosvg.svg2png(url='example.svg', write_to='example.png', output_width=3200)"
```

或已有 Node.js + sharp 时：

```bash
node -e "require('sharp')('example.svg', {density:144}).png().toFile('example.png').catch(e=>{console.error(e);process.exit(1)})"
```

二者均为可选依赖，不随技能捆绑；SVG 生成本身无第三方依赖。如确实需要安装，优先在工作目录隔离环境中安装所选工具，不修改用户全局运行环境。缺少光栅化工具时保留 SVG 并如实说明尚缺 PNG，不把未生成的文件写成已交付。

字体需包含所用语言的字形，中文可选择环境提供的 Noto Sans CJK SC、PingFang SC、Microsoft YaHei。缺字应换字体并重新渲染；不要用截图替换错误字形。

脚本检查 ID、证据非空、端口、坐标边界、尺寸和线型，但不会检查证据是否真实、字号实际宽度、连线相交、模型数学或层数。这些必须回读源码、渲染图片并人工检查。导出宽度增加只提高像素数，不能修复逻辑布局。

## 可运行的验证

从技能目录执行：

```bash
python3 -m unittest discover -s tests -v
```

示例 `assets/example_model.py` 是教学用 PyTorch 源码；不需要执行它就能检查绘图链路。它不是用于测量模型性能的基准，也不能当作其他模型结构的依据。

## 原生 draw.io 导出

```bash
python3 scripts/export_drawio.py model.json --output model.drawio
python3 scripts/export_drawio.py overview.json attention.json --output model.drawio
```

多输入依次对应多页。导出未压缩 mxfile/mxGraphModel XML，节点、文字、容器和连线均为原生对象；节点的 evidence 保存在 Edit Data 元数据中。位于面板内的节点随容器移动；边端点与节点边界相符时自动挂接，移动节点会带动连接线端点。浮空线端点作为可编辑坐标保留。

可以在 draw.io Desktop 或 diagrams.net 中使用 File → Open From → Device 打开。SVG 与 draw.io 使用不同字体/形状引擎，导出后检查换行、梯形方向、路由和端点；XML 通过校验不等于已完成编辑器视觉验收。不要把 PNG/SVG 作为单张图片嵌入后声称所有模块可编辑。

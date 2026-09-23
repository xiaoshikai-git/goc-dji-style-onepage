# 可编辑绘图脚本

`scripts/canvas.py` 是可选的基础图元工具。需要 Python 3.10+ 与 Pillow；优先用 `load_workspace_dependencies` 返回的 Python，避免假设系统 Python 已安装 Pillow。

## 快速验证

以技能目录的实际绝对路径代替 `SKILL_DIR`，使用可用 Python 执行：

```sh
python3 "$SKILL_DIR/scripts/canvas.py" --demo --output-dir /tmp/wireframe-example
```

这会在本地生成一个示例页面、一个视频展开状态、原生 `.drawio`、几何 JSON 及逐页 PNG。它不访问飞书、不导入、不修改线上数据。示例是脚本用法演示，不是完整建站交付。

## 项目脚本用法

把项目专用文案、布局和构建代码放在项目输出目录，不要修改已安装的技能来保存某客户内容。

```python
from pathlib import Path
import sys

# skill_dir 由当前技能位置确定，不硬编码某客户目录。
skill_dir = Path(sys.argv[1])
output_dir = Path(sys.argv[2])
sys.path.insert(0, str(skill_dir / 'scripts'))
from canvas import Board

board = Board('Project WEBSITE WIREFRAMES/PROTOTYPE')
page = board.frame('01 Home', x=0, y=0, width=1200)
page.rect(0, 0, 1200, 76, fill='#171717', stroke='#171717')
page.text('01 / Home', 24, 16, 1152, size=30, bold=True, color='#FFFFFF')

# 在 y=120 开始页面本体；示例仅展示 API。
page.rect(0, 120, 1200, 104)
page.text('PROJECT', 64, 154, 240, size=25, bold=True)
page.text('Products     About     Support', 600, 160, 536, size=18)
page.rect(0, 224, 1200, 600, fill='#FAFAFA')
title_height = page.text('A useful headline for the project.', 64, 300, 480, size=44, bold=True)
page.text('Draft customer-facing copy based on the brief.', 64, 324 + title_height, 480, size=20)
page.media('Product in use / context photograph', 632, 280, 504, 460)
page.button('Explore the product', 64, 690, w=220)
# 接着按 manifest 绘制完整模块、Footer 和状态。
page.finish(824)
board.write(output_dir / 'project-wireframes.drawio')
```

## API

| 方法 | 用途 |
| --- | --- |
| `Board(name, font_path=None, bold_font_path=None, font_family='Arial')` | 建板；可显式指定预览字体与导入字体名称 |
| `board.frame(name, x=0, y=0, width=1200)` | 新页面或组件区域，原点是全板坐标 |
| `frame.rect(x,y,w,h,fill,stroke)` | 矩形；颜色 `none` 表示无填充/描边 |
| `frame.line(x1,y1,x2,y2,color)` | 原生线条，支持水平/垂直/斜线 |
| `frame.text(value,x,y,w,size,bold,color,align,height)` | 自动测宽换行，返回实际文本高度；高度不足直接报错 |
| `frame.button(label,x,y,w=200,h=48,primary=True)` | 独立按钮形状与文字；文字放不下会报错 |
| `frame.media(label,x,y,w,h,video=False)` | 灰媒体框；视频增加原生播放图形 |
| `frame.finish(height=None)` | 冻结该区域并校验内容不越界；省略高度则按内容决定 |
| `board.write(path,preview=True,scale=0.6)` | 写 `.drawio`、同名 `.geometry.json`、逐区域 PNG |

页面内的图元使用相对坐标，脚本导出时转成全板坐标。所有图元按添加顺序叠放，先画背景，再画内容。默认生成一个 diagram 和独立原生对象，便于飞书导入；导入后再按实际 UI 组合或分区。

英文可用系统 Arial / DejaVu Sans。中文应指定覆盖中文的字体和相应 `font_family`；例如 macOS 上实际存在时可以用 `/System/Library/Fonts/STHeiti Light.ttc`、粗体 `/System/Library/Fonts/STHeiti Medium.ttc` 和 `Heiti SC`。不要把只有拉丁字符的字体测宽结果当成中文字形已验证。其他机器应查找当地可用字体，不打包未经授权的字体文件。

## 代码检查能力和边界

脚本校验数字有限、坐标非负、内容不超出区域右边和底部、文字测量高度、按钮与媒体文字可容纳，并重新解析生成 XML。英文长单词或 URL 会拆行，CJK 按字换行。

背景与内容本来就会重叠，因此脚本不自动判定所有重叠错误；页面之间的布局、模块遮挡、链接去向、文案事实与来源需由设计者检查。PNG 使用本地字体，飞书可能替换字体或行高，所以本地通过不代表线上显示必然正确。

真实图片可在飞书中加入并与原生线框组合。不要为了支持图片而把整页栅格化。该脚本不自动创建超链接或实现播放/提交，也不自动验证 manifest 的语义。

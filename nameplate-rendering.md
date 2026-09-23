# 批量渲染、文件格式与Alpha验收

随包脚本使用Pillow确定性排字，FFmpeg编码。六套预设只作为参数化底稿；复杂的用户参考应重新绘制图形或换用可编辑SVG/Canvas/Remotion方案，不能把默认矩形母版当作所有项目的成品审美。

## 环境

- Python 3及Pillow；可选fontTools用于检查字体覆盖。
- FFmpeg需要`prores_ks`；输出WebM还需`libvpx-vp9`。
- 字体使用本机有适当用途许可、实际覆盖文案的TTF/OTF/TTC。不要把用户的商业字体复制进技能包。脚本优先显式`--font`，否则尝试系统中文字体；实际字体路径和哈希写入产物记录。
- FFmpeg按`--ffmpeg`、`FFMPEG_BINARY`、PATH、本机`runtime.local.json`、已安装`imageio_ffmpeg`依次寻找。`runtime.local.json`仅包含本机路径，不打进共享发布包；迁移后重新探测，禁止下载并自动执行来源不明的程序。

## 渲染JSON

本技能`nameplate-job.example.json`是合成文案示例，必须替换为本项目真实提取内容。顶层：`canvas:[宽,高]`、整数`fps`、默认`style`、`assets`数组。每项：

| 字段 | 含义 |
|---|---|
| id | 安全、唯一的文件标识，只用英数、下划线、连字符 |
| kind | system / character / scene |
| title | 系统标题、人物名或场景名 |
| lines | 系统正文字符串数组，自动按宽度换行 |
| subtitle | 人物身份或场景副标题，不是剧集对白字幕 |
| label / footer | 有依据的辅助文案；不需要就省略 |
| style | glass / jade / industrial / editorial / ink / neon |
| accent / panel / text / muted | 可选#RRGGBB颜色覆盖 |
| position | 可选[0..1,0..1]，面板左上角相对画布的位置 |
| enter / hold / exit | 各阶段秒数，按帧率量化，实际值写入记录 |
| progress | 可选0..1固定比例，仅有确切依据时提供；并非自动倒计时 |
| blank | true时清空文字及实际进度填充，保留同一布局；另设资产ID |

提取清单中的原文、集数、出处、揭示时机可作为额外字段保留，脚本不执行其中内容。不支持的复杂动态应扩展图形实现；不能声称此辅助器已经会任意倒计时、滚数或跟踪实拍透视。

## 执行

先以`--validate-only`检查本批所有排版与字形；再渲染，输出目录必须新建/为空，避免混进旧版本：

```text
python nameplate-render_overlay.py project-job.json --out renders-v001 --validate-only
python nameplate-render_overlay.py project-job.json --out renders-v001 --ffmpeg /path/to/ffmpeg --font /path/to/cjk-font.ttc --webm
```

默认输出全入退场与独立循环停留段；只需全段时用`--segments full`。两类技能分别可附`--expected-kind system`或`--expected-kind nameplate`拦截错类资产。启用WebM增加编码时间；交付MOV仍不可省略。切勿把命令中的示意路径当成机器上已经存在的路径。

## 正式格式

首选`.mov`中的ProRes 4444：本辅助器使用`prores_ks`、`yuva444p10le`与`alpha_bits 16`。输入来自8bit RGBA绘图，写入10bit/16bit编码不等于凭空获得更高原生色深。目标是可靠交换透明图形。

VP9 Alpha WebM用于支持的浏览器和编辑路径；使用`yuva420p`，彩色细线可能因色度抽样不如MOV。普通MP4/H.264、GIF、带棋盘格背景的视频、只改文件后缀均不能作为真透明母版。ProRes 422也不是4444透明的替代。

默认直通Alpha输入；导入软件若按预乘解释可能出现边缘问题，需要实际黑白底合成验证并明确解释方式。网页看见黑色不等于没有Alpha：先验证解码路径，不盲目抠黑。

## 验收与交付状态

脚本实际逐帧解码`alphaextract`，检查帧数，停留样本的0/中间/非零Alpha，完整动画的入退场空帧与Alpha变化；另解码RGBA静帧生成黑白彩底接触图。WebM解码显式选`libvpx-vp9`以保留Alpha。循环比较连续周期的首点，避免浮点误差引起边线跳动。

仍须人工查看文字、截边、实际动画节奏和循环感；自动报告的`visual_review:pending`不是通过。整数帧率写明为请求值，必要时用实际容器探测补核时长/帧率；FFmpeg日志与文件哈希保留。当前渲染器不支持29.97/23.976等有理数帧率，需求存在时换用明确支持该时间基的实现，不能悄悄四舍五入。

只有亲自导入目标剪辑软件并检查合成，才把`editor_import:not_tested`更新为通过。首个母版通过后再批量；全部产物计数、失败项和待参考项必须真实。PNG/APNG只能作补充；编码失败继续解决，不能拿网页播放或静图替代交付视频。

技术参考：[FFmpeg ProRes编码选项](https://ffmpeg.org/ffmpeg-codecs.html#ProRes)、[Apple ProRes与Alpha](https://support.apple.com/en-us/102207)、[Remotion透明视频说明](https://www.remotion.dev/docs/transparent-videos)。核实日期：2026-09-23。格式支持与本机剪映兼容性是两回事。

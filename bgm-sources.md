# 音乐发现入口、技术依据与核实范围

## 选曲来源偏好与入口

2026-09-23最新偏好：BGM尽量从Incompetech选择。这覆盖旧的“抖音热门优先”；Apple Music/iTunes仍排除。默认站内现成优先、原创按需补缺，已确认的项目路径仍沿用。执行方法见[Incompetech检索](bgm-incompetech-discovery.md)；用户提供的某首歌只作入口或参考，不自动指定为全剧配乐。

以下为本次维护核实到的官方入口，逐曲选用时仍要读取当前页面：

| 来源 | 核实范围与使用边界 |
|---|---|
| [Incompetech曲库](https://incompetech.com/music/royalty-free/music.html) | 可见标题/乐器/描述搜索及Genre、Feel筛选；筛选标签不是已试听证据 |
| [用户提供的曲目入口](https://incompetech.com/music/royalty-free/index.html?isrc=USUAN1100208) | 静态读取为加载中外壳，不能据此编造曲名、音频和段落秒点 |
| [官方ISRC索引](https://incompetech.com/music/royalty-free/isrc_to_name.php) | 可读取录音编号与曲名映射，可辅助动态页身份核对 |
| [Music FAQ](https://incompetech.com/music/royalty-free/faq.html) | 说明署名、曲名替换及ISRC用途；曲目与当前许可仍需逐项核实 |
| [官方许可页](https://incompetech.com/music/royalty-free/licenses/) | 提供需署名的免费Creative Commons路径及Standard License路径；记录实际采用许可，不把免费写成无版权或已购买 |

抖音、汽水音乐和剪映曲库作为按需补充入口，热度证据按[抖音检索](bgm-douyin-discovery.md)逐次核实，不维护永久热门歌单。不能用站外榜单或抓取日期冒充抖音当期热度。

## 音频技术

核对日期：2026-09-23。下面是音频单位、测量工具与公开功能的参考；不把国际版CapCut宣传页等同于所有版本中文剪映的实测说明。

| 来源 | 支持内容 | 使用边界 |
|---|---|---|
| [EBU R128官方推荐](https://tech.ebu.ch/publications/r128) | 以−23 LUFS节目响度为基准，并使用响度范围与真峰值描述 | 广播推荐，不是对红果/抖音成片的统一强制要求 |
| [CapCut公开归一说明](https://www.capcut.com/resource/audio-normalization-spotify) | 页面剪辑部分描述−23 LUFS归一，并可继续调音量、淡入淡出 | 不能证明用户中文剪映的归一/增益顺序或最终实际响度 |
| [CapCut对白音乐避让说明](https://www.capcut.com/create/audio-ducking-for-clear-dialogue-in-video) | 介绍对白出现时降低音乐及关键帧方式 | 公开建议不是本机界面已验证功能；技能中的时序是待试听起点 |
| [FFmpeg ebur128](https://ffmpeg.org/ffmpeg-filters.html#ebur128) | 响度扫描与真峰值测量选项 | 必须实际运行并读取测量；单声道/双单声道处理需一致 |
| [FFmpeg loudnorm](https://ffmpeg.org/ffmpeg-filters.html#loudnorm) | 归一可使用线性或动态模式，目标/测量/峰值条件会影响处理 | 不能把动态归一后的结果当成简单加减公式；本技能测量例用ebur128 |
| [Suno官方Custom Mode](https://help.suno.com/en/articles/3726721) | 可选Instrumental并输入风格等配置 | 只说明公开工作流，不证明本机有可调用API或已生成音乐 |
| [Suno排除元素说明](https://help.suno.com/en/articles/3161921) | 描述Exclude用途 | 模型生成结果仍需试听；具体界面与套餐在执行时重新确认 |

本用户的−23 LUFS/+10 dB设置来自用户本轮明确确认，不是从网上猜测；版权候选开放来自用户明确偏好。滑块起点、音乐响度差、总线余量、编配策略是本技能的工作建议，分别标注条件，不冒充平台规则。

本次查询未取得中文剪映官方对用户具体版本处理链的完整技术说明，也未验证红果的专用混音交付规范。后续有平台后台规范或实际导出文件时，以其更新项目参数。音乐曲名、版本、链接与获取状态需在每次具体推荐时查证。

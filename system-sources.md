# 技术来源与融合取舍

2026-09-23核实：[Apple ProRes](https://support.apple.com/en-us/102207)说明4444系列具备Alpha；[FFmpeg ProRes编码选项](https://ffmpeg.org/ffmpeg-codecs.html#ProRes)给出profile和alpha_bits；[Remotion透明视频说明](https://www.remotion.dev/docs/transparent-videos)作为其他可编辑渲染路线参考；[Pillow图像接口](https://pillow.readthedocs.io/en/stable/reference/Image.html)用于确定性RGBA绘图。来源描述格式能力，不证明任意剪映版本实际导入成功。

从本机23-asset-factory吸收了全剧提取、文案来源、参考风格、可编辑文字、黑白彩底与解码Alpha检查的思路；本技能重新编写独立流程和渲染器，不依赖它的安装路径。正式母版改为用户这次要求的透明视频，PNG/APNG只是补充。

确认流程遵从本轮意图：需要用户参考就等待实际参考；用户要求先确认样片就先展示；用户已授权自主设计与批量制作时正常执行，不把旧技能的每轮确认流程强加给新任务。没有明确回复不冒充已确认参考图。

所有示例姓名、任务和数字均是合成测试文案，不是当前剧本的事实。素材默认本地；创建技能并不自动授予公开上传剧本、字体、第三方图像或商业成片的权限。

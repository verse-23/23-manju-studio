# 导出工具与内部数据

这份约定用于确定性导出；内容仍要先完成全剧阅读、审美设计与预检。工具不自动判断剧本事实、审美优劣、用户批准或平台过审。内部JSON留工作目录，不当作额外用户交付，也不上传公共仓库。

## 页面与PDF

环境需要Python 3.10+与`reportlab`、`Pillow`，以及有使用权、覆盖实际中文字符的本地TrueType字体。优先使用当前环境已有依赖；字体文件不随技能上传。无字体时查找本地可用字体或合法安装，不能输出方块字后假装成功。

```text
python asset-render_delivery.py work/project-assets.json --out outputs/project-v004 --name asset-design-v004 --font /path/to/local-cjk.ttf
```

同一个JSON生成HTML与完整PDF，存在同名输出时拒绝覆盖，改用新版本路径。HTML完全离线，PDF使用嵌入字体、可选文字和每项书签；脚本成功后仍须实际打开网页、逐页渲染PDF检查。

数据结构（以下只是字段示例，不是可交付剧本内容）：

```json
{
  "title": "作品名称 · 全剧资产设计",
  "version": "v004",
  "scope": "已实际读完的集场范围与来源版本",
  "model": "本轮确认的目标模型",
  "spec": "16:9 / 2560×1440目标 / 高质量",
  "art_direction": "具体世界观色材方向与主角设计逻辑",
  "issues": ["仍待确认的事项，全部完成时为空数组"],
  "assets": [{
    "id": "CHR-001", "kind": "CHR", "name": "人物与状态",
    "source": "实际集场与短来源定位",
    "status": "设计提示词已交付",
    "design": "具体美术设定；剧本依据与艺术补全分清",
    "anchors": ["可见识别锚点"],
    "notes": ["必要制作说明"],
    "prompt": "完整独立提示词，不用同上",
    "text_layers": []
  }]
}
```

只有实际完成动态素材的UI条目才增加`media`对象：`preview`为APNG相对路径，`poster`为静态PNG，`download`为ZIP相对路径，`spec`写实际尺寸/fps/片段时长/检查结果。将这些真实文件放在交付目录内部，禁止远程URL、越目录路径或空占位。页面支持暂停到静态关键帧、恢复播放、深浅底和下载；PDF显示关键帧与素材包文件名。准确文字层可换行，但不能改写原文。

## 旧空框实验工具（非正式视频管线）

合并版系统框正式制作使用模块2的render_overlay.py；下文只说明保留的旧辅助器。不选择模块2不会触发这些工具。

### 透明动态空框基础渲染

`render_system_ui.py`需要Pillow，制作参数化矢量几何与透明动画，不调用生图。不同参考需要修改组件设计，不能用同一基础框假装满足所有审美方向。人物/场景提示词不调用这个脚本。

```text
python asset-render_system_ui.py work/ui-motion.json --out outputs/project-v004/ui-motion-v001
```

配置：

```json
{
  "approval": {"confirmed": false, "reference": "实际已确认参考的名称/版本", "scope": ["UI-001"]},
  "size": [2560, 1440], "fps": 30,
  "seconds": {"in": 0.4, "loop": 2.6, "out": 0.3},
  "panels": [{"id": "UI-001", "rect": [0.55, 0.10, 0.38, 0.34], "accent": "#8CBFB0", "fill": "#102B30", "opacity": 0.24}]
}
```

`rect`是归一化x/y/宽/高。`confirmed`只能依据真实用户确认更新，不能为通过程序检查自行设置。未确认时可用`--draft`渲染一个母版样片供审阅；该模式仅接受一个面板且明确标为draft，不可批量冒充正式交付。单纯升级技能只使用虚构测试配置验证脚本，不代表任何实际项目UI已获批准。

每个UI包含可编辑SVG静态母版、三个原生尺寸RGBA PNG片段（入场/循环/退场）、缩小APNG预览、PNG关键帧、配置和可重现源脚本；总包是ZIP。有效帧已检查真实Alpha和动态变化，APNG时长/透明读取验证；仍要在黑白和彩色底目视检查边缘与循环。不会宣称自动导出未实现的MOV/WebM。

需要单文件剪辑母版时先确认本地FFmpeg含所需编码器，再把PNG序列转为ProRes 4444 MOV并解码复验。例如使用`prores_ks`、`4444` profile、支持Alpha的像素格式和非零`alpha_bits`，以实际工具帮助与[官方文档](https://ffmpeg.org/ffmpeg-codecs.html#ProRes)为准；不得只改后缀或输出普通MP4。若最终方案明确需要该格式，继续完成转换，不能把APNG预览当作已完成MOV。

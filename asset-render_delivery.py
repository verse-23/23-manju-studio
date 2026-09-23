"""Render one reviewed asset dataset to a self-contained HTML page and full PDF."""
import argparse
import html
import json
import re
from pathlib import Path


def validate(data):
    for key in ('title', 'version', 'scope', 'model', 'spec', 'art_direction'):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError('Missing project field: ' + key)
    assets = data.get('assets')
    if not isinstance(assets, list) or not assets:
        raise ValueError('assets must be a nonempty list')
    seen = set()
    for a in assets:
        for key in ('id', 'kind', 'name', 'source', 'design', 'prompt', 'status'):
            if not isinstance(a.get(key), str) or not a[key].strip():
                raise ValueError('Missing asset field: ' + key)
        if not re.fullmatch(r'[A-Za-z0-9_-]+', a['id']) or a['id'] in seen:
            raise ValueError('Invalid or duplicate ID: ' + a['id'])
        seen.add(a['id'])
        if a['kind'] not in ('CHR', 'SCN', 'PRP', 'FX', 'UI'):
            raise ValueError('Unknown asset kind')
        for key in ('anchors', 'notes', 'text_layers'):
            if not isinstance(a.get(key, []), list) or not all(isinstance(x, str) for x in a.get(key, [])):
                raise ValueError(key + ' must be a list of strings')
    if not isinstance(data.get('issues', []), list) or not all(isinstance(x, str) for x in data.get('issues', [])):
        raise ValueError('issues must be a list of strings')


def safe_media(path, output_dir):
    if not isinstance(path, str) or re.match(r'^[a-z]+:', path, re.I):
        raise ValueError('Media must use a local relative path')
    target = (output_dir / path).resolve()
    if not target.is_relative_to(output_dir.resolve()) or not target.is_file():
        raise ValueError('Missing media inside delivery folder: ' + path)
    return target


def make_pdf(data, path, font_path, media_root):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image

    pdfmetrics.registerFont(TTFont('AssetCJK', str(font_path)))
    base = dict(fontName='AssetCJK', wordWrap='CJK', alignment=TA_LEFT)
    styles = {
        'title': ParagraphStyle('title', fontSize=27, leading=36, textColor=colors.HexColor('#122C35'), spaceAfter=20, **base),
        'h': ParagraphStyle('h', fontSize=16, leading=23, spaceBefore=16, spaceAfter=10, keepWithNext=True, **base),
        'label': ParagraphStyle('label', fontSize=10, leading=16, textColor=colors.HexColor('#197A73'), spaceBefore=9, spaceAfter=4, keepWithNext=True, **base),
        'body': ParagraphStyle('body', fontSize=10.5, leading=17, spaceAfter=8, **base),
        'meta': ParagraphStyle('meta', fontSize=9, leading=14, textColor=colors.HexColor('#52606C'), spaceAfter=6, **base),
        'prompt': ParagraphStyle('prompt', fontSize=10.5, leading=18, backColor=colors.HexColor('#F1F5F3'), borderPadding=10, spaceBefore=6, spaceAfter=12, **base),
    }

    def para(s, style='body'):
        return Paragraph(html.escape(s).replace('\n', '<br/>'), styles[style])

    class AssetDoc(SimpleDocTemplate):
        def afterFlowable(self, flowable):
            if hasattr(flowable, 'asset_bookmark'):
                key, title = flowable.asset_bookmark
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(title, key, 0, False)

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#D4DDDA'))
        canvas.line(42, 39, A4[0]-42, 39)
        canvas.setFont('AssetCJK', 8)
        canvas.setFillColor(colors.HexColor('#52606C'))
        canvas.drawString(42, 26, '23-ASSET-FACTORY / ' + data['version'])
        canvas.drawRightString(A4[0]-42, 26, str(doc.page))
        canvas.restoreState()

    story = [para('ASSET DESIGN / ' + data['version'], 'label'), para(data['title'], 'title')]
    for k, label in (('scope','范围'), ('model','模型目标'), ('spec','规格意图')):
        story.append(para(label + '：' + data[k], 'meta'))
    story += [para('美术方向', 'h'), para(data['art_direction']), para(f"共{len(data['assets'])}条资产设计；实际交付状态逐项标注。", 'meta')]
    if data.get('issues'):
        story.append(para('待确认与未交付项', 'h'))
        story.extend(para(x) for x in data['issues'])
    story += [para('目录', 'h')]
    for a in data['assets']:
        story.append(Paragraph('<link href="#' + a['id'] + '">' + html.escape(a['id']+' / '+a['name']) + '</link>', styles['meta']))
    for a in data['assets']:
        story.append(PageBreak())
        heading = para(a['id'] + ' / ' + a['name'], 'h')
        heading.asset_bookmark = (a['id'], a['id']+' '+a['name'])
        story += [heading, para(a['kind']+' · '+a['status'], 'meta'), para('来源与使用范围：'+a['source'], 'meta'), para('美术设定', 'label'), para(a['design'])]
        for label, key in (('识别锚点','anchors'), ('制作说明','notes')):
            if a.get(key):
                story.append(para(label, 'label'))
                story.extend(para(s) for s in a[key])
        story.append(para('完整提示词', 'label'))
        # Split at paragraphs, never truncate to fit a card/page.
        story.extend(para(s, 'prompt') for s in a['prompt'].split('\n\n') if s)
        if a.get('text_layers'):
            story.append(para('准确文字层（另行排版）', 'label'))
            story.extend(para(s, 'prompt') for s in a['text_layers'])
        if a.get('media'):
            m=a['media']
            story.append(para('动态素材：'+m['spec'], 'label'))
            poster=safe_media(m['poster'],media_root)
            im=Image(str(poster)); im.drawHeight=im.imageHeight*min(470/im.imageWidth,240/im.imageHeight); im.drawWidth=im.imageWidth*min(470/im.imageWidth,240/im.imageHeight)
            story += [im, Spacer(1,12), para('动态文件见同目录素材包：'+m['download'], 'meta')]
    doc=AssetDoc(str(path), pagesize=A4, rightMargin=48, leftMargin=48, topMargin=42, bottomMargin=54, title=data['title'], author='23-asset-factory')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('data',type=Path)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--font',type=Path,required=True,help='Locally installed CJK TrueType font; not bundled or uploaded')
    ap.add_argument('--name',default='asset-design')
    args=ap.parse_args()
    if not re.fullmatch(r'[\w-]+',args.name): raise ValueError('name must be a filename stem')
    data=json.loads(args.data.read_text(encoding='utf-8-sig')); validate(data)
    args.out.mkdir(parents=True,exist_ok=True)
    pdf=args.out/(args.name+'.pdf'); page=args.out/(args.name+'.html')
    if pdf.exists() or page.exists(): raise FileExistsError('Choose a new output version; existing files are preserved')
    if not args.font.is_file(): raise FileNotFoundError(args.font)
    for a in data['assets']:
        if a.get('media'):
            for key in ('preview','poster','download'): safe_media(a['media'][key],args.out)
            if not a['media'].get('spec'): raise ValueError('Missing actual media specification')
    make_pdf(data,pdf,args.font,args.out)
    template=(Path(__file__).resolve().parent/'asset-delivery.html').read_text(encoding='utf-8')
    payload=json.dumps(data,ensure_ascii=False).replace('<','\\u003c').replace('&','\\u0026')
    page.write_text(template.replace('@@TITLE@@',html.escape(data['title'])).replace('@@PDF@@',html.escape(pdf.name,quote=True)).replace('@@DATA@@',payload),encoding='utf-8')
    print(json.dumps({'html':str(page.resolve()),'pdf':str(pdf.resolve()),'assets':len(data['assets'])},ensure_ascii=False))


if __name__=='__main__': main()

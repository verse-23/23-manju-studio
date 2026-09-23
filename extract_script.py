"""Extract DOCX/TXT/MD paragraphs in source order. Candidate tags are recall aids only."""
import argparse, hashlib, json, re, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

def episode_number(text):
    m=re.match(r'^第\s*([0-9零〇一二两三四五六七八九十百]+)\s*集(?:\s|[：:、.．]|$)',text)
    if not m:return None
    s=m[1]
    if s.isdigit():return int(s)
    units={'十':10,'百':100};digits={c:i for i,c in enumerate('零一二三四五六七八九')};digits.update({'两':2,'〇':0})
    total=0;n=0
    for c in s:
        if c in units:total+=(n or 1)*units[c];n=0
        else:n=digits[c]
    return total+n

def extract(path):
    path=Path(path);suffix=path.suffix.lower()
    if suffix=='.docx':
        with zipfile.ZipFile(path) as z:
            info=z.getinfo('word/document.xml')
            if info.file_size>50_000_000:raise ValueError('文档XML过大；改用分批读取，不解压可执行文件')
            root=ET.fromstring(z.read(info))
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        body=root.find('w:body',ns)
        rows=[''.join(n.text or '' for n in p.findall('.//w:t',ns)) for p in body.findall('.//w:p',ns)]
        basis='Word正文段落（含表格内段落及空段，序号从1开始；不含页眉页脚）'
    elif suffix in ('.txt','.md'):
        rows=path.read_text(encoding='utf-8-sig').splitlines();basis='源文件行号，从1开始'
    else:raise ValueError('仅支持DOCX、UTF-8 TXT/MD；PDF需另行可靠提取后保留页码')
    result=[];episode=None
    for i,text in enumerate(rows,1):
        text=text.strip()
        if not text:continue
        number=episode_number(text)
        if number is not None:episode=number
        tags=[]
        if re.search(r'系统|面板|提示框|任务|奖励|冷却|属性|倒计时|解锁|弹窗',text):tags.append('system_candidate')
        if re.search(r'日[/／]|夜[/／]|场景|地点|室内|室外|内景|外景',text):tags.append('scene_candidate')
        if re.match(r'[^：:\s]{1,12}(?:[（(].{0,40}[）)])?[：:]',text):tags.append('speaker_candidate')
        result.append({'paragraph':i,'episode':episode,'text':text,'candidate_tags':tags})
    return {'source':str(path.resolve()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'anchor_basis':basis,'paragraphs':result,'notice':'标签仅用于召回候选；必须通读上下文。旁白、脑内声音或一次提及不等于可见UI，也不能据台词标签自动认定人物身份。'}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('输出已存在；使用新的版本文件名')
    data=extract(a.source);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'paragraphs':len(data['paragraphs']),'episodes':sorted({r['episode'] for r in data['paragraphs'] if r['episode'] is not None}),'out':str(a.out)},ensure_ascii=False))
if __name__=='__main__':main()

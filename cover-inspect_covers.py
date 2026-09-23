"""Read-only cover inspection; create equal-size review previews, never repair art."""
import argparse,hashlib,html,json
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw

def inspect(manifest_path,out):
    path=Path(manifest_path);data=json.loads(path.read_text(encoding='utf-8-sig'));variants=data.get('variants',[])
    expected=data.get('expected_count',5)
    if expected!=5 or len(variants)!=5:raise ValueError('新整套封面必须有5个版本；单张修改不使用此整套验收命令')
    ids=[v.get('id') for v in variants]
    if len(set(ids))!=5 or any(not isinstance(i,str) or not i.strip() for i in ids):raise ValueError('五版ID必须唯一且非空')
    records=[];pixel_hashes=[]
    for v in variants:
        rec={'id':v['id'],'concept':v.get('concept',''),'exact_title':v.get('exact_title',''),'files':[],'visual_qa':'pending','text_qa':'pending','plot_qa':'pending'}
        for role in ('master','upload'):
            if role not in v:continue
            file=(path.parent/v[role]).resolve()
            with Image.open(file) as im:
                im.load();fmt=im.format;w,h=im.size
                if w*4!=h*3:raise ValueError(f"{v['id']} {role} 不是3:4：{w}x{h}")
                if role=='master' and fmt!='PNG':raise ValueError('PNG母版缺失或实际编码不是PNG')
                if role=='upload' and fmt!='JPEG':raise ValueError('JPEG上传版实际编码不符')
                if im.getexif().get(274,1)!=1:raise ValueError('存在旋转EXIF；先明确真实展示方向再验收')
                digest=hashlib.sha256(im.convert('RGBA').tobytes()+str(im.size).encode()).hexdigest()
                if role=='master':pixel_hashes.append(digest)
                cap=data.get('max_upload_bytes') if role=='upload' else None
                if cap and file.stat().st_size>cap:raise ValueError(v['id']+'超出用户给定上传大小限制')
                rec['files'].append({'role':role,'path':str(file),'format':fmt,'size':[w,h],'bytes':file.stat().st_size,'pixel_sha256':digest})
        if not any(f['role']=='master' for f in rec['files']):raise ValueError('每版都需要真实母版')
        records.append(rec)
    if len(set(pixel_hashes))!=5:raise ValueError('检测到像素相同的母版；改文件名或编码不算新设计')
    out=Path(out)
    if out.exists() and any(out.iterdir()):raise ValueError('检查输出目录必须是新的空目录')
    out.mkdir(parents=True,exist_ok=True);sheet=Image.new('RGB',(1532,460),'#19252a');draw=ImageDraw.Draw(sheet);cards=[]
    for i,rec in enumerate(records):
        master=next(f for f in rec['files'] if f['role']=='master')
        im=Image.open(master['path']).convert('RGB')
        # Exact 3:4 images are downsampled only for comparative review.
        thumb=im.resize((300,400),Image.Resampling.LANCZOS);name=f'preview-{i+1:02d}.jpg';thumb.save(out/name,quality=93)
        sheet.paste(thumb,(6+i*305,5));draw.text((15+i*305,418),rec['id'],fill='#eef1e9')
        small=im.resize((150,200),Image.Resampling.LANCZOS);small.save(out/f'small-{i+1:02d}.jpg',quality=93)
        cards.append(f'<article><img src="{name}"><h2>{html.escape(rec["id"])}</h2><p>{html.escape(rec["concept"])}</p><p>标题待逐字核对：{html.escape(rec["exact_title"])}</p><p>{master["size"][0]}×{master["size"][1]} · PNG</p></article>')
    sheet.save(out/'contact-sheet.jpg',quality=94)
    report={'status':'file-check-pass','count':5,'ratio':'3:4','distinct_pixel_files':True,'distinct_designs':'manual_review_required','records':records}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>五版封面对比</title><style>body{font:15px/1.8 "Microsoft YaHei",sans-serif;background:#172328;color:#f3f1e8;margin:30px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:20px}article{background:#24353a;border-radius:8px;padding:15px}img{width:100%;display:block}h1{font-size:30px}p{font-size:13px;color:#d2ded6}</style><h1>五版3:4封面 · 同尺寸比较</h1><p>机械检查通过：五份不同像素的3:4 PNG母版。构图差异、身份、标题和剧情真实性须逐图人工审查，不能据此宣称点击率或视觉质量通过。</p><main>'+''.join(cards)+'</main></html>',encoding='utf-8')
    return report
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=inspect(a.manifest,a.out);print(json.dumps({k:v for k,v in r.items() if k!='records'},ensure_ascii=False))
if __name__=='__main__':main()

"""Deterministic blank UI motion: editable SVG, RGBA PNG clips and APNG previews.

This is a starter renderer, not a replacement for approved art direction.
Requires Pillow. Batch mode requires a recorded real user approval.
"""
import argparse
import hashlib
import json
import math
import re
import shutil
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw


def color(value):
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
        raise ValueError('Colors must be #RRGGBB')
    return tuple(int(value[i:i+2],16) for i in (1,3,5))


def validate(cfg,draft):
    approval=cfg.get('approval',{})
    if not draft and not (approval.get('confirmed') is True and approval.get('reference') and approval.get('scope')):
        raise ValueError('Batch export requires real user confirmation of the reference and scope; do not invent approval')
    w,h=cfg['size']; fps=cfg['fps']
    if not all(isinstance(x,int) and not isinstance(x,bool) for x in (w,h,fps)) or not (128<=w<=4096 and 128<=h<=4096 and 1<=fps<=60):
        raise ValueError('Invalid size/fps')
    for phase in ('in','loop','out'):
        if not isinstance(cfg['seconds'][phase],(int,float)) or not 0<cfg['seconds'][phase]<=10:
            raise ValueError('Each clip must be 0-10 seconds')
    panels=cfg['panels']
    if not panels or (draft and len(panels)!=1): raise ValueError('Draft permits exactly one reference panel')
    ids=set()
    for p in panels:
        if not re.fullmatch(r'[A-Za-z0-9_-]+',p['id']) or p['id'] in ids: raise ValueError('Invalid/duplicate panel ID')
        ids.add(p['id'])
        if not draft and p['id'] not in approval['scope']: raise ValueError('Panel outside approved batch scope')
        x,y,pw,ph=p['rect']
        if not (0.02<=x<1 and 0.02<=y<1 and pw>=0.1 and ph>=0.1 and x+pw<=.98 and y+ph<=.95):
            raise ValueError('Panel must fit inside transparent margins and motion bounds')
        color(p['accent']);color(p['fill'])
        if not 0<p['opacity']<1: raise ValueError('Panel opacity must be between zero and one')


def draw(cfg,p,phase,index,count):
    w,h=cfg['size']; scale=2
    image=Image.new('RGBA',(w*scale,h*scale),(0,0,0,0)); d=ImageDraw.Draw(image)
    t=index/max(1,count-1)
    opacity=1.0
    offset=0
    if phase=='in': opacity=1-(1-t)**3;offset=(1-opacity)*h*.014
    if phase=='out': opacity=(1-t)**2;offset=(1-opacity)*h*.008
    x,y,pw,ph=p['rect'];x*=w;y=y*h+offset;pw*=w;ph*=h
    box=tuple(round(v*scale) for v in (x,y,x+pw,y+ph))
    accent=color(p['accent']);fill=color(p['fill'])
    line=max(1,round(w/1280*scale));radius=round(min(pw,ph)*.055*scale)
    pulse=.88+.12*math.cos(2*math.pi*index/max(1,count)) if phase=='loop' else 1
    d.rounded_rectangle(box,radius,fill=fill+(round(255*p['opacity']*opacity),),outline=accent+(round(210*opacity*pulse),),width=line)
    # Blank header separator and restrained corner accents; no invented glyphs.
    inset=pw*.06
    d.line(tuple(round(v*scale) for v in (x+inset,y+ph*.29,x+pw-inset,y+ph*.29)),fill=accent+(round(95*opacity),),width=line)
    for xx,yy,sx,sy in ((x,y,1,1),(x+pw,y,-1,1),(x,y+ph,1,-1),(x+pw,y+ph,-1,-1)):
        q=min(pw,ph)*.065
        pts=[(round((xx+sx*q)*scale),round(yy*scale)),(round(xx*scale),round(yy*scale)),(round(xx*scale),round((yy+sy*q)*scale))]
        d.line(pts,fill=accent+(round(240*opacity*pulse),),width=line)
    return image.resize((w,h),Image.Resampling.LANCZOS)


def svg(cfg,p):
    w,h=cfg['size'];x,y,pw,ph=p['rect'];x*=w;y*=h;pw*=w;ph*=h
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<g id="panel"><rect x="{x}" y="{y}" width="{pw}" height="{ph}" rx="{min(pw,ph)*.055}" fill="{p['fill']}" fill-opacity="{p['opacity']}" stroke="{p['accent']}" stroke-opacity=".82" stroke-width="{w/1280}"/>
<path d="M{x+pw*.06} {y+ph*.29} H{x+pw*.94}" stroke="{p['accent']}" stroke-opacity=".37" stroke-width="{w/1280}"/>
''' + '\n'.join(f'<path d="M{xx+sx*min(pw,ph)*.065} {yy} L{xx} {yy} L{xx} {yy+sy*min(pw,ph)*.065}" fill="none" stroke="{p["accent"]}" stroke-opacity=".94" stroke-width="{w/1280}"/>' for xx,yy,sx,sy in ((x,y,1,1),(x+pw,y,-1,1),(x,y+ph,1,-1),(x+pw,y+ph,-1,-1)))+'\n</g></svg>'


def render(cfg,out,draft):
    validate(cfg,draft)
    if out.exists() or out.with_suffix('.zip').exists(): raise FileExistsError('Use a new version/output directory')
    out.mkdir(parents=True)
    (out/'motion-source.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
    shutil.copy2(Path(__file__),out/'render_system_ui.py')
    report={'mode':'draft' if draft else 'approved-batch','size':cfg['size'],'fps':cfg['fps'],'alpha':'straight RGBA','panels':[]}
    for p in cfg['panels']:
        folder=out/p['id'];folder.mkdir()
        (folder/'base.svg').write_text(svg(cfg,p),encoding='utf-8')
        poster=draw(cfg,p,'loop',0,30);poster.save(folder/'poster.png')
        item={'id':p['id'],'clips':{}}
        for phase in ('in','loop','out'):
            frames=folder/phase;frames.mkdir()
            count=max(2,round(cfg['fps']*cfg['seconds'][phase]))
            previews=[];hashes=set();visible=0;has_translucent=False
            for i in range(count):
                frame=draw(cfg,p,phase,i,count)
                target=frames/f'{i:05d}.png';frame.save(target)
                # Read back actual saved alpha, not just the drawing buffer.
                with Image.open(target) as saved:
                    alpha=saved.getchannel('A');lo,hi=alpha.getextrema()
                    if lo!=0:raise ValueError('Opaque exterior')
                    if hi:visible+=1
                    if any(alpha.histogram()[1:255]):has_translucent=True
                    if alpha.getpixel((0,0)) or alpha.getpixel((saved.width-1,saved.height-1)):raise ValueError('Nontransparent corner')
                    hashes.add(hashlib.sha256(saved.tobytes()).hexdigest())
                preview=frame.copy();preview.thumbnail((960,540),Image.Resampling.LANCZOS);previews.append(preview)
            if visible==0 or len(hashes)<2 or not has_translucent:raise ValueError('Empty/static/no-translucency clip')
            preview_path=folder/(phase+'.apng')
            previews[0].save(preview_path,format='PNG',save_all=True,append_images=previews[1:],duration=1000/cfg['fps'],loop=0 if phase=='loop' else 1,disposal=0,blend=0)
            with Image.open(preview_path) as apng:
                duration=0
                for i in range(apng.n_frames):
                    apng.seek(i);duration+=apng.info.get('duration',0)
                    if apng.convert('RGBA').getchannel('A').getextrema()[0]!=0:raise ValueError('APNG lost transparency')
                if abs(duration-count*1000/cfg['fps'])>max(5,count*.1):raise ValueError('APNG duration mismatch')
            item['clips'][phase]={'frames':count,'seconds':count/cfg['fps'],'visible_frames':visible,'different_frames':len(hashes),'alpha_checked':True}
        report['panels'].append(item)
    (out/'export.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'READ-ME.txt').write_text('RGBA PNG sequences are the full-resolution masters. Import each numbered clip at the fps in export.json. APNG is a smaller preview; use loop.apng for repeat playback. SVG is the editable static base; motion-source.json and render_system_ui.py reproduce the animation. No MOV/WebM is claimed. Draft files are review samples, not approved production assets.\n',encoding='utf-8')
    archive=out.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for f in sorted(out.rglob('*')):
            if f.is_file():z.write(f,f.relative_to(out.parent))
    return {'directory':str(out.resolve()),'archive':str(archive.resolve()),'panels':len(cfg['panels']),'mode':report['mode']}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('config',type=Path);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--draft',action='store_true')
    args=ap.parse_args();cfg=json.loads(args.config.read_text(encoding='utf-8-sig'))
    print(json.dumps(render(cfg,args.out,args.draft),ensure_ascii=False))


if __name__=='__main__':main()

"""Deterministic RGBA motion graphics, ProRes 4444 and decoded-alpha verification.

Requires Pillow. FFmpeg: --ffmpeg, FFMPEG_BINARY, PATH, or imageio_ffmpeg.
All paths are local. No shell commands, downloads, source deletion or model calls.
"""
from __future__ import annotations
import argparse, hashlib, html, io, json, math, os, re, shutil, subprocess, sys
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter

SKINS = {
 'glass': {'panel':'#102c3b','accent':'#92e6e4','text':'#eff9f5','muted':'#b0c5cc','opacity':210,'radius':22},
 'jade': {'panel':'#112e2b','accent':'#dac493','text':'#f4eed9','muted':'#b5c6b4','opacity':231,'radius':12},
 'industrial': {'panel':'#1d2328','accent':'#ecc080','text':'#f7f0df','muted':'#bac1ba','opacity':234,'radius':3},
 'editorial': {'panel':'#eee9da','accent':'#9d663d','text':'#202c32','muted':'#526268','opacity':242,'radius':4},
 'ink': {'panel':'#202b31','accent':'#c8d3cb','text':'#f6f2e5','muted':'#bbc0b7','opacity':235,'radius':4},
 'neon': {'panel':'#201d34','accent':'#c6b5f3','text':'#f5edf9','muted':'#b8b6d0','opacity':220,'radius':18},
}
def rgba(s, alpha=255):
    if not re.fullmatch(r'#[0-9a-fA-F]{6}',s): raise ValueError('颜色必须为 #RRGGBB')
    return tuple(int(s[i:i+2],16) for i in (1,3,5))+(alpha,)
def number(v, name, lo, hi):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not lo<=v<=hi:
        raise ValueError(f'{name} 应在 {lo}..{hi} 内')
    return v
def executable(given=None):
    local_file=Path(__file__).resolve().parent/'runtime.local.json'
    local=json.loads(local_file.read_text(encoding='utf-8')).get('ffmpeg') if local_file.is_file() else None
    candidate=given or os.environ.get('FFMPEG_BINARY') or shutil.which('ffmpeg') or local
    if not candidate:
        try:
            import imageio_ffmpeg
            candidate=imageio_ffmpeg.get_ffmpeg_exe()
        except (ImportError,AttributeError): pass
    if not candidate or not Path(candidate).is_file():
        raise ValueError('未找到FFmpeg；用 --ffmpeg 指定已安装路径，或安装 imageio-ffmpeg。不能用PNG宣称视频已交付。')
    return str(Path(candidate).resolve())
def font_file(given):
    options=[given] if given else []
    options += ['C:/Windows/Fonts/msyh.ttc','C:/Windows/Fonts/simhei.ttf',
        '/System/Library/Fonts/PingFang.ttc','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
    for p in options:
        if p and Path(p).is_file(): return str(Path(p).resolve())
    raise ValueError('请用 --font 指定含中文的 TTF/OTF/TTC；不使用缺字的默认字体。')
def glyph_check(font, texts):
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return {'status':'unverified','reason':'fontTools unavailable；必须人工逐字检查'}
    f=TTFont(font,fontNumber=0,lazy=True); cmap=f.getBestCmap();f.close()
    missing=sorted({c for t in texts for c in t if not c.isspace() and ord(c) not in cmap})
    if missing: raise ValueError('字体缺字：'+''.join(missing))
    return {'status':'glyphs_present','note':'字形存在不等于文字内容已校对'}
def validate(job, expected_kind=None):
    if not isinstance(job,dict): raise ValueError('Job必须是JSON对象')
    canvas=job.get('canvas',[2560,1440])
    if len(canvas)!=2: raise ValueError('canvas需要宽、高')
    w,h=[number(x,'canvas',320,7680) for x in canvas]
    if any(int(v)!=v or int(v)%2 for v in (w,h)): raise ValueError('宽高应为偶数整数')
    fps=number(job.get('fps',30),'fps',1,60)
    if int(fps)!=fps: raise ValueError('本辅助器支持整数帧率；29.97等请使用明确的有理数渲染方案')
    if not isinstance(job.get('assets'),list) or not job['assets']: raise ValueError('assets不能为空')
    seen=set()
    for a in job['assets']:
        ident=a.get('id','')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}',ident) or ident in seen: raise ValueError('资产ID非法或重复：'+str(ident))
        seen.add(ident)
        if a.get('kind') not in ('system','character','scene'): raise ValueError('kind必须是system、character或scene')
        if expected_kind=='system' and a['kind']!='system': raise ValueError('系统框任务不能混入名牌')
        if expected_kind=='nameplate' and a['kind']=='system': raise ValueError('名牌任务不能混入系统框')
        if not isinstance(a.get('title'),str) or not a['title'].strip(): raise ValueError(ident+' 缺title')
        if 'blank' in a and not isinstance(a['blank'],bool): raise ValueError('blank必须为布尔值')
        lines=a.get('lines',[])
        if not isinstance(lines,list) or any(not isinstance(t,str) for t in lines): raise ValueError('lines必须是字符串列表')
        for key in ('label','footer','subtitle'):
            if key in a and not isinstance(a[key],str): raise ValueError(key+'应为字符串')
        skin=a.get('style',job.get('style','glass'))
        if skin not in SKINS: raise ValueError('未知style：'+str(skin))
        for key in ('accent','panel','text','muted'):
            if key in a: rgba(a[key])
        for key,default in [('enter',.4),('hold',3.2),('exit',.3)]:
            number(a.get(key,default),key,0.1,120)
        if 'progress' in a: number(a['progress'],'progress',0,1)
        if 'position' in a and (len(a['position'])!=2 or any(not isinstance(v,(int,float)) or not 0<=v<=1 for v in a['position'])):
            raise ValueError('position需要0..1归一化坐标[x,y]，表示面板左上角')
    return int(w),int(h),int(fps)

def wrap(text,font,max_width):
    lines=[]
    for paragraph in text.split('\n'):
        line=''
        for c in paragraph:
            if line and font.getlength(line+c)>max_width:
                lines.append(line);line=c
            else: line+=c
        lines.append(line)
    return lines

def draw_panel(a,w,h,font_path,style):
    """Render a supersampled static plate. Animation never regenerates glyphs."""
    unit=min(w/2560,h/1440); ss=2
    p={**SKINS[style],**{k:a[k] for k in ('accent','panel','text','muted') if k in a}}
    system=a['kind']=='system'; scene=a['kind']=='scene'
    pw=int((1500 if system else 1090 if scene else 930)*unit)
    margin=int(62*unit); gap=int(18*unit)
    title_size=max(18,round((66 if system else 72 if scene else 82)*unit))
    body_size=max(13,round((46 if system else 39)*unit))
    small_size=max(11,round(28*unit))
    tf=ImageFont.truetype(font_path,title_size*ss)
    bf=ImageFont.truetype(font_path,body_size*ss)
    sf=ImageFont.truetype(font_path,small_size*ss)
    if tf.getlength(a['title'])>(pw-2*margin)*ss:
        raise ValueError(a['id']+' 标题过长。请扩大版式或合理换行/分页，不截字或盲目缩小字体。')
    texts=a.get('lines',[]) if system else ([a['subtitle']] if a.get('subtitle') else [])
    body_lines=[line for text in texts for line in wrap(text,bf,(pw-2*margin)*ss)]
    header_h=round((154 if a.get('label') else 113)*unit)
    line_h=round(body_size*1.55)
    ph=max(round((280 if system else 218)*unit),header_h+len(body_lines)*line_h+margin+gap)
    if a.get('footer'): ph+=round(47*unit)
    if 'progress' in a:ph+=round(35*unit)
    if ph>h*.77: raise ValueError(a['id']+' 文案超出单屏容量；应按语义拆页并延长阅读，禁止裁切。')
    image=Image.new('RGBA',(pw*ss,ph*ss),(0,0,0,0));d=ImageDraw.Draw(image)
    def rect(box,**kw): d.rectangle(tuple(round(x*ss) for x in box),**kw)
    border=max(2,round(2*unit))*ss;rad=max(2,round(p['radius']*unit))*ss
    d.rounded_rectangle((0,0,pw*ss-1,ph*ss-1),radius=rad,fill=rgba(p['panel'],p['opacity']),outline=rgba(p['accent'],178),width=border)
    inset=round(12*unit)*ss
    if style=='jade':
        d.rounded_rectangle((inset,inset,pw*ss-inset,ph*ss-inset),radius=rad//2,outline=rgba(p['accent'],85),width=max(1,border//2))
        for x in (margin,pw-margin):
            y=round(31*unit);r=round(7*unit)
            d.polygon([(int(x*ss),int((y-r)*ss)),(int((x+r)*ss),int(y*ss)),(int(x*ss),int((y+r)*ss)),(int((x-r)*ss),int(y*ss))],fill=rgba(p['accent'],215))
    if style=='industrial':
        for x in range(round(30*unit),pw-round(30*unit),max(8,round(44*unit))):
            rect((x,13*unit,x+16*unit,16*unit),fill=rgba(p['accent'],110))
    if not system: rect((0,0,max(5,9*unit),ph),fill=rgba(p['accent'],255))
    y=round(36*unit)
    if a.get('label'):
        if sf.getlength(a['label'])>(pw-2*margin)*ss: raise ValueError(a['id']+' label过长')
        if not a.get('blank'):d.text((margin*ss,y*ss),a['label'],font=sf,fill=rgba(p['muted']),anchor='lt')
        y+=round(47*unit)
    if not a.get('blank'):d.text((margin*ss,y*ss),a['title'],font=tf,fill=rgba(p['text']),anchor='lt')
    y+=round(title_size*1.25)
    if body_lines:
        y+=gap
        if system:
            rect((margin,y-8*unit,pw-margin,y-7*unit),fill=rgba(p['accent'],85));y+=round(18*unit)
        for line in body_lines:
            if not a.get('blank'):d.text((margin*ss,y*ss),line,font=bf,fill=rgba(p['text']),anchor='lt')
            y+=line_h
    if a.get('footer'):
        footer=a['footer']
        if sf.getlength(footer)>(pw-2*margin)*ss:raise ValueError(a['id']+' footer过长，应拆到正文')
        y+=round(12*unit)
        if not a.get('blank'):d.text((margin*ss,y*ss),footer,font=sf,fill=rgba(p['muted']),anchor='lt')
        y+=small_size
    if 'progress' in a:
        y+=round(22*unit);height=max(3,round(7*unit))
        rect((margin,y,pw-margin,y+height),fill=rgba(p['accent'],50))
        if a['progress']>0 and not a.get('blank'):rect((margin,y,margin+(pw-2*margin)*a['progress'],y+height),fill=rgba(p['accent'],240))
        y+=height
    if y>ph-round(20*unit): raise ValueError(a['id']+' 文字靠近底边，请减少文案或调整版式')
    image=image.resize((pw,ph),Image.Resampling.LANCZOS)
    pos=a.get('position',[.065,.65] if not system else [(1-pw/w)/2,.13])
    x,y=round(pos[0]*w),round(pos[1]*h)
    if x+pw>w or y+ph>h: raise ValueError(a['id']+' 面板超出画布，请调整position或拆页')
    return image,(x,y),p

def smooth(x): return max(0,min(1,x))**2*(3-2*max(0,min(1,x)))
def frame_at(base,pos,p,w,h,index,count,fps,enter,hold,exit_s,segment):
    t=index/fps;offset=0;opacity=1.;phase=0
    if segment=='full':
        if t<enter:
            opacity=smooth(t/enter);offset=round((1-opacity)*28*w/2560)
        elif t>=enter+hold:
            # Last decoded frame is exactly empty, without adding duplicate duration.
            remaining=max(1/fps,exit_s-1/fps)
            opacity=1-smooth((t-enter-hold)/remaining)
        phase=max(0,min(1,(t-enter)/hold))
    else: phase=(index%count)/count
    panel=base.copy()
    glow=Image.new('RGBA',panel.size,(0,0,0,0));d=ImageDraw.Draw(glow)
    pulse=int(52+20*math.sin(2*math.pi*phase))
    pw,ph=panel.size
    d.line((round(pw*.07),1,round(pw*.31),1),fill=rgba(p['accent'],pulse),width=max(2,round(3*w/2560)))
    panel=Image.alpha_composite(panel,glow)
    if opacity<1:panel.putalpha(panel.getchannel('A').point(lambda a:round(a*opacity)))
    out=Image.new('RGBA',(w,h),(0,0,0,0));out.alpha_composite(panel,(pos[0],pos[1]+offset));return out

def encode(ffmpeg,path,frames,w,h,fps,webm=False):
    opts=['-c:v','libvpx-vp9','-pix_fmt','yuva420p','-b:v','0','-crf','20','-auto-alt-ref','0'] if webm else ['-c:v','prores_ks','-profile:v','4444','-pix_fmt','yuva444p10le','-alpha_bits','16','-qscale:v','4']
    cmd=[ffmpeg,'-hide_banner','-loglevel','error','-n','-f','rawvideo','-pixel_format','rgba','-video_size',f'{w}x{h}','-framerate',str(fps),'-i','pipe:0','-an',*opts,'-threads','2',str(path)]
    log=path.with_suffix(path.suffix+'.encode.log')
    with log.open('wb') as err:
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=err)
        try:
            for frame in frames:proc.stdin.write(frame.tobytes())
            proc.stdin.close();code=proc.wait(timeout=120)
        except Exception:
            proc.kill();proc.wait();raise
    if code: raise RuntimeError('编码失败：'+log.read_text(encoding='utf-8',errors='replace')[-2000:])
    return cmd

def decode_check(ffmpeg,path,w,h,fps,expected_count,hold_index):
    # Decode EVERY alpha frame; do not trust a file extension, pixel-format tag or source PNG.
    decoder=['-c:v','libvpx-vp9'] if path.suffix=='.webm' else []
    cmd=[ffmpeg,'-hide_banner','-loglevel','error',*decoder,'-i',str(path),'-map','0:v:0','-vf','alphaextract','-pix_fmt','gray','-f','rawvideo','pipe:1']
    log=path.with_suffix(path.suffix+'.alpha.log')
    checks=[];frame_size=w*h
    with log.open('wb') as err:
        p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=err)
        n=0;tail=b'';first_hash=None;varied=False
        while True:
            buf=bytearray()
            while len(buf)<frame_size:
                part=p.stdout.read(frame_size-len(buf))
                if not part:break
                buf.extend(part)
            if not buf:break
            if len(buf)!=frame_size:tail=bytes(buf);break
            digest=hashlib.sha256(buf).hexdigest()
            if first_hash is None:first_hash=digest
            elif digest!=first_hash:varied=True
            if n in {0,hold_index,expected_count-1}:
                hist=Image.frombytes('L',(w,h),bytes(buf)).histogram()
                checks.append({'frame':n,'zero_pixels':hist[0],'visible_pixels':sum(hist[1:]),'partial_pixels':sum(hist[1:255]),'opaque_pixels':hist[255]})
            n+=1
        code=p.wait(timeout=120)
    if code or tail or n!=expected_count:raise RuntimeError(f'{path.name} Alpha解码/帧数不合格：code={code} frames={n}/{expected_count}')
    effective=next(x for x in checks if x['frame']==hold_index)
    if not effective['zero_pixels'] or not effective['visible_pixels'] or not effective['partial_pixels']:
        raise RuntimeError(path.name+'停留帧不是有效的透明叠加素材')
    # Round-trip a decoded RGBA image for composite edge inspection.
    png=subprocess.run([ffmpeg,'-hide_banner','-loglevel','error',*decoder,'-i',str(path),'-vf',f'select=eq(n\\,{hold_index})','-frames:v','1','-f','image2pipe','-c:v','png','-pix_fmt','rgba','pipe:1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
    im=Image.open(io.BytesIO(png)).convert('RGBA')
    if im.size!=(w,h):raise RuntimeError('视频解码尺寸不符')
    report={'frames':n,'fps_requested':fps,'duration_by_frame_count':n/fps,'alpha_decoded_all_frames':True,'alpha_samples':checks,'alpha_changes_over_time':varied,'decoded_dimensions':[w,h],'status':'decoded-alpha-pass','visual_review':'pending','editor_import':'not_tested'}
    return report,im

def composites(im,path):
    thumbs=[]
    for name,color in [('black','#101318'),('white','#f5f4ef'),('color','#477080')]:
        bg=Image.new('RGBA',im.size,rgba(color));view=Image.alpha_composite(bg,im).convert('RGB')
        view.thumbnail((768,432),Image.Resampling.LANCZOS);view.save(path.with_name(path.stem+'_'+name+'.jpg'),quality=93);thumbs.append(view)
    sheet=Image.new('RGB',(thumbs[0].width,len(thumbs)*thumbs[0].height),'#111111')
    for i,t in enumerate(thumbs):sheet.paste(t,(0,i*t.height))
    sheet.save(path)

def gallery(out,results):
    cards=[]
    for r in results:
        a=r['asset'];ident=a['id'];webm=next((v['file'] for v in r['videos'] if v['file'].endswith('_full.webm')),None)
        media=f'<video controls loop playsinline src="{html.escape(webm)}"></video>' if webm else f'<img src="{ident}_hold.png" alt="透明静帧预览；视频请下载MOV">'
        links=' · '.join(f'<a href="{html.escape(v["file"])}" download>{html.escape(v["file"])}</a>' for v in r['videos'])
        cards.append(f'<article><h2>{html.escape(ident)} · {html.escape(a["title"])}</h2><div class="plate">{media}</div><p>{links}</p><details><summary>原文字段和验收记录</summary><pre>{html.escape(json.dumps(r,ensure_ascii=False,indent=2))}</pre></details></article>')
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>透明动态素材交付</title><style>body{margin:0;background:#111b21;color:#e8eee9;font:15px/1.8 "Microsoft YaHei",sans-serif}main{max-width:1150px;margin:35px auto;padding:20px}h1{font-size:35px}article{background:#202e35;border:1px solid #41505a;border-radius:12px;margin:25px 0;padding:25px}button{padding:8px 16px;margin:8px;border:1px solid #869d97;border-radius:4px;cursor:pointer}a{color:#b1e1cf}.plate{background:#3b5260;border-radius:8px}img,video{display:block;width:100%}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}p{color:#c3d1cc}</style><main><h1>透明动态素材</h1><p>正式视频为带Alpha的MOV；WebM如有则用于可解码浏览器预览。下方背景只用于检查，未烘焙进素材。没有WebM时展示的是透明PNG静帧，不能把它当作视频播放。</p><div><button data-bg="#101318">深底</button><button data-bg="#f5f4ef">浅底</button><button data-bg="#477080">彩底</button></div>'''+''.join(cards)+'''</main><script>document.querySelectorAll('[data-bg]').forEach(b=>b.onclick=()=>document.querySelectorAll('.plate').forEach(x=>x.style.background=b.dataset.bg))</script></html>'''
    (out/'index.html').write_text(page,encoding='utf-8')

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('job',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--font');p.add_argument('--ffmpeg');p.add_argument('--webm',action='store_true');p.add_argument('--segments',default='full,hold',choices=['full','full,hold']);p.add_argument('--expected-kind',choices=['system','nameplate']);p.add_argument('--validate-only',action='store_true')
    args=p.parse_args(argv);job=json.loads(args.job.read_text(encoding='utf-8-sig'));w,h,fps=validate(job,args.expected_kind);font=font_file(args.font or job.get('font'))
    all_text=[a.get(k,'') for a in job['assets'] for k in ('title','label','subtitle','footer')]+[t for a in job['assets'] for t in a.get('lines',[])]
    glyphs=glyph_check(font,all_text)
    # Preflight every plate before writing any output, so overflow does not half-render a batch.
    plates=[draw_panel(a,w,h,font,a.get('style',job.get('style','glass'))) for a in job['assets']]
    if args.validate_only:
        print(json.dumps({'status':'layout-preflight-pass','assets':len(plates),'glyphs':glyphs},ensure_ascii=False));return
    ffmpeg=executable(args.ffmpeg)
    encoders=subprocess.run([ffmpeg,'-hide_banner','-encoders'],capture_output=True,text=True,check=True).stdout
    if 'prores_ks' not in encoders or (args.webm and 'libvpx-vp9' not in encoders):raise ValueError('缺少所需编码器')
    out=args.out.resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('输出目录必须为空或不存在；新版本不要覆盖旧素材')
    out.mkdir(parents=True,exist_ok=True)
    manifest={'version':'1.0.0','canvas':[w,h],'fps':fps,'font':font,'font_sha256':hashlib.sha256(Path(font).read_bytes()).hexdigest(),'glyphs':glyphs,'ffmpeg_version':subprocess.run([ffmpeg,'-version'],capture_output=True,text=True,check=True).stdout.splitlines()[0],'alpha':'RGBA straight input；decoded alpha verified, editor interpretation requires import test','results':[]}
    (out/'source.json').write_text(json.dumps(job,ensure_ascii=False,indent=2),encoding='utf-8')
    for a,(base,pos,palette) in zip(job['assets'],plates):
        en,ho,ex=[a.get(k,d) for k,d in [('enter',.4),('hold',3.2),('exit',.3)]]
        # Quantize each phase separately so clip durations and frame boundaries agree.
        en_n,ho_n,ex_n=[max(2,round(v*fps)) for v in (en,ho,ex)];en,ho,ex=en_n/fps,ho_n/fps,ex_n/fps
        result={'asset':a,'font':font,'videos':[],'effective_timing':{'enter':en,'hold':ho,'exit':ex},'panel_box':[pos[0],pos[1],base.width,base.height]}
        for segment in args.segments.split(','):
            count=en_n+ho_n+ex_n if segment=='full' else ho_n
            hold_index=en_n+ho_n//2 if segment=='full' else ho_n//2
            def frames():
                for i in range(count):yield frame_at(base,pos,palette,w,h,i,count,fps,en,ho,ex,segment)
            for ext in (['mov','webm'] if args.webm else ['mov']):
                path=out/f"{a['id']}_{segment}.{ext}"
                encode(ffmpeg,path,frames(),w,h,fps,ext=='webm')
                report,decoded=decode_check(ffmpeg,path,w,h,fps,count,hold_index)
                if segment=='full' and not report['alpha_changes_over_time']:raise ValueError('动画没有变化')
                if segment=='full' and (report['alpha_samples'][0]['visible_pixels'] or report['alpha_samples'][-1]['visible_pixels']):raise ValueError('入退场边界帧没有按设计全透明')
                result['videos'].append({'file':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),**report})
                if segment=='full' and ext=='mov':
                    decoded.save(out/f"{a['id']}_hold.png");composites(decoded,out/f"{a['id']}_composites.jpg")
            if segment=='hold':
                first=frame_at(base,pos,palette,w,h,0,count,fps,en,ho,ex,segment)
                # t=1 is mathematically the same phase as t=0; the video samples t in [0,1).
                next_cycle=frame_at(base,pos,palette,w,h,count,count,fps,en,ho,ex,segment)
                if ImageChops.difference(first,next_cycle).getbbox(): raise ValueError('循环边界不一致')
                result['loop_boundary']='连续周期首点相同；视觉无跳变仍需实看'
        manifest['results'].append(result)
        (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        print(a['id']+' encoded + decoded alpha verified',flush=True)
    gallery(out,manifest['results'])
    print(json.dumps({'status':'rendered-alpha-verified','out':str(out),'assets':len(plates),'visual_review':'pending','editor_import':'not_tested'},ensure_ascii=False))
if __name__=='__main__':
    try:main()
    except (ValueError,RuntimeError,OSError,subprocess.SubprocessError) as e:print('ERROR: '+str(e),file=sys.stderr);sys.exit(1)

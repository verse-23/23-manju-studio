"""Validate a shot plan and emit a copyable prompt. Does not judge or generate video."""
import argparse,json,math
from pathlib import Path

def validate(data):
    p=data['project'];shots=data['shots'];refs=data.get('references',[])
    if not shots:raise ValueError('shots不能为空')
    def finite(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
    duration=p['duration_s']
    if not finite(duration) or duration<=0:raise ValueError('duration_s须为有限正数')
    cap=p.get('verified_max_duration_s')
    if cap is not None and (not finite(cap) or cap<=0 or duration>cap):raise ValueError('时长超过本次核实的入口上限或上限非法')
    if p.get('dialogue_route') not in ('post','model','silent'):raise ValueError('dialogue_route为post/model/silent')
    refids=[r['id'] for r in refs]
    if len(refids)!=len(set(refids)):raise ValueError('参考ID重复')
    for r in refs:
        if not r.get('purpose') or not r.get('source'):raise ValueError('参考素材需要来源与用途')
        if r.get('token') and r.get('status')!='uploaded':raise ValueError('未上传参考不得填写实际引用token')
    current=0;ids=set();actual=[]
    for s in shots:
        if s['id'] in ids:raise ValueError('镜号重复')
        ids.add(s['id']);start,end=s['start'],s['end']
        if not finite(start) or not finite(end) or end<=start or abs(start-current)>1e-6:raise ValueError(s['id']+'时间段有缺口、重叠或非法数值')
        current=end
        for field in ('subject_and_position','action','camera','focus','lighting','continuity_out'):
            if not isinstance(s.get(field),str) or not s[field].strip():raise ValueError(s['id']+'缺少'+field)
        if set(s.get('reference_ids',[]))-set(refids):raise ValueError(s['id']+'引用未知素材')
        for d in s.get('dialogue',[]):
            if not d.get('speaker') or not d.get('text') or not d.get('delivery'):raise ValueError('对白缺说话者、原文或语气')
            if d.get('mode') not in ('on_camera','offscreen','voiceover'):raise ValueError('对白mode非法')
            actual.append({'speaker':d['speaker'],'text':d['text'],'mode':d['mode']})
    if abs(current-duration)>1e-6:raise ValueError('最后一镜结束时间不等于总时长')
    if 'locked_dialogue' not in data:raise ValueError('必须显式记录locked_dialogue，纯动作镜头可为[]')
    if actual!=data['locked_dialogue']:raise ValueError('对白出现遗漏、改字、顺序变化、说话者或画内外状态变化')
    if p['dialogue_route']=='silent' and actual:raise ValueError('静默任务存在锁定对白；先明确是否要删除对白，不自动忽略')
    return {'status':'structural-preflight-pass','shots':len(shots),'duration_s':duration,'dialogue_lines':len(actual),'model_called':False,'aesthetic_review':'manual','actual_speech_timing':'not_measured'}
def build(data):
    p=data['project'];lines=[f"# {p.get('title','镜头提示词优化')}\n",'## 可复制主稿\n',f"目标：{p.get('model_target','Seedance 2.5')}；画幅：{p.get('ratio','16:9')}；时长计划：{p['duration_s']}秒。",p.get('style',''),p.get('scene','')]
    if data.get('references'):
        lines.append('\n参考映射：')
        for r in data['references']:
            label=r.get('token') or f"待绑定本地参考：{r['source']}"
            lines.append(f"- {label}：{r['purpose']}")
    for s in data['shots']:
        lines.append(f"\n{s['start']:g}–{s['end']:g}秒 / {s['id']}：{s['subject_and_position']}。{s['action']}。镜头：{s['camera']}。焦点：{s['focus']}。光线：{s['lighting']}。")
        if s.get('continuity_in'):lines.append('接入状态：'+s['continuity_in'])
        for d in s.get('dialogue',[]):
            modes={'on_camera':'画内','offscreen':'画外','voiceover':'旁白/内心，不张嘴'}
            lines.append(f"{modes[d['mode']]}台词，{d['speaker']}（{d['delivery']}）：\"{d['text']}\"")
        if s.get('sound'):lines.append('环境/动作声：'+s['sound'])
        lines.append('结束状态：'+s['continuity_out'])
    audio={'post':'对白使用后期配音；上列台词用于表演和口型节奏，不要求模型另生成一套对白音频。','model':'生成指定说话者和语气的原句对白，不添加新台词。','silent':'整段无声。'}[p['dialogue_route']]
    lines += ['\n'+audio,p.get('audio_policy','无BGM；不额外添加对白字幕。'),'\n## 预检范围\n\n仅检查时轴、字段、参考映射与锁定对白；尚未调用视频模型、测量口播或验收成片。']
    return '\n'.join(x for x in lines if x)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();data=json.loads(a.plan.read_text(encoding='utf-8-sig'));report=validate(data)
    if a.out:
        if a.out.exists():raise ValueError('输出存在；请改用新版本文件名')
        a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(build(data),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()

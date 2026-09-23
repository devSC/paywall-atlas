#!/usr/bin/env python3
"""HEAD-check one representative image and all video links per collected app."""
import argparse,concurrent.futures,datetime as dt,json,pathlib,subprocess,collections

def check(url):
    cmd=['curl','--silent','--show-error','--location','--head','--max-time','18','--retry','1','--retry-all-errors','--output','/dev/null','--write-out','%{http_code}\t%{content_type}',url]
    r=subprocess.run(cmd,capture_output=True,text=True);parts=r.stdout.strip().split('\t',1)
    status=int(parts[0]) if parts and parts[0].isdigit() else 0;mime=parts[1] if len(parts)>1 else ''
    expected='video/' if url.split('?')[0].lower().endswith(('.mp4','.webm','.mov')) else 'image/'
    return {'url':url,'checked_at':dt.datetime.now(dt.timezone.utc).isoformat(),'status':status,'content_type':mime,'ok':r.returncode==0 and 200<=status<300 and mime.startswith(expected),'error':r.stderr.strip() if r.returncode else None}

def main():
    p=argparse.ArgumentParser();p.add_argument('--resume',action='store_true');p.add_argument('--start-app',type=int,default=0);p.add_argument('--cache',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
    rows=[]
    for file in sorted(a.cache.glob('page-*.json')):
        x=json.loads(file.read_text());rows.extend(r for r in (x.get('data') or {}).get('rows',[]) if str(r.get('recent_capture_update','')).startswith('2026-'))
    rows=rows[a.start_app:]
    wanted=[]
    for row in rows:
        images=[u for u in row.get('captures',[]) if u.split('?')[0].lower().endswith(('.jpg','.jpeg','.png','.webp','.gif'))]
        if images:wanted.append(images[0])
        wanted.extend(u for u in [row.get('onboarding_url')]+row.get('captures',[]) if u and u.split('?')[0].lower().endswith(('.mp4','.webm','.mov')))
    wanted=list(dict.fromkeys(wanted));old=json.loads(a.output.read_text()) if a.resume and a.output.exists() else {};results={r['url']:r for r in old.get('checks',[]) if r.get('ok')};todo=[u for u in wanted if u not in results]
    print(json.dumps({'apps':len(rows),'links':len(wanted),'to_check':len(todo)}),flush=True)
    def save():
        report={'checked_at':dt.datetime.now(dt.timezone.utc).isoformat(),'scope':'first screenshot and all video links per app; not every screenshot','apps':len(rows),'links':len(wanted),'checked':len([u for u in wanted if u in results]),'passed':sum(results[u]['ok'] for u in wanted if u in results),'checks':[results[u] for u in wanted if u in results]}
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');return report
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for i,result in enumerate(pool.map(check,todo),1):
            results[result['url']]=result
            if i%50==0:save();print(f'Checked {i}/{len(todo)} new links',flush=True)
    report=save();print(json.dumps({k:v for k,v in report.items() if k!='checks'}),flush=True)
if __name__=='__main__':main()

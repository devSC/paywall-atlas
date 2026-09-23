#!/usr/bin/env python3
"""Read public PaywallPro list pages through curl; stop on access restrictions."""
import argparse, datetime as dt, json, pathlib, subprocess, time

def request(page, resolve):
    payload={'mode':'fall','page':page,'limit':12,'region_code':1102,'sort':{'type':'recent_update_date','order':'desc'}}
    cmd=['curl','--silent','--show-error','--fail','--max-time','40','--retry','3','--retry-all-errors','--retry-delay','3','--noproxy','*']
    if resolve: cmd += ['--resolve',f'www.paywallpro.app:443:{resolve}']
    cmd+=['https://www.paywallpro.app/api/app-list','-H','Content-Type: application/json','--data-binary','@-']
    result=subprocess.run(cmd,input=json.dumps(payload),text=True,capture_output=True)
    if result.returncode: raise RuntimeError(result.stderr.strip())
    return json.loads(result.stdout)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cache',required=True);ap.add_argument('--resolve');ap.add_argument('--year',type=int,default=2026);args=ap.parse_args()
    cache=pathlib.Path(args.cache);cache.mkdir(parents=True,exist_ok=True)
    report={'year':args.year,'date_field':'recent_capture_update','region_code':1102,'started_at':dt.datetime.now(dt.timezone.utc).isoformat(),'pages':0,'status':'partial','stop_reason':None,'reported_count':None}
    rows=[];seen=set();page=1
    try:
        while True:
            file=cache/f'page-{page:04}.json'
            if file.exists(): result=json.loads(file.read_text())
            else:
                result=request(page,args.resolve);file.write_text(json.dumps(result,ensure_ascii=False,indent=2));time.sleep(.35)
            if str(result.get('code'))!='200':
                report.update(stop_reason=f"API {result.get('code')}: {result.get('msg')}",blocked_page=page);break
            body=result.get('data') or {};batch=body.get('rows');count=body.get('count')
            if not isinstance(batch,list): raise RuntimeError('Invalid rows shape')
            if report['reported_count'] is None:report['reported_count']=count
            elif count!=report['reported_count']:report['count_changed']=True
            novel=0
            for r in batch:
                key=str(r.get('info_id') or r.get('app_id'))
                if key not in seen:seen.add(key);rows.append(r);novel+=1
            report['pages']=page
            dates=[r.get('recent_capture_update') for r in batch if r.get('recent_capture_update')]
            print(json.dumps({'page':page,'rows':len(batch),'unique_total':len(rows),'oldest':min(dates) if dates else None}),flush=True)
            if not batch or (isinstance(count,int) and page*12>=count):
                report['status']='complete' if len(rows)==count and not report.get('count_changed') else 'partial'
                report['stop_reason']='Public list exhausted';break
            if novel==0:report['stop_reason']='Repeated page; pagination did not advance';break
            page+=1
    except (RuntimeError,ValueError,OSError) as e:report['stop_reason']=str(e)
    report['finished_at']=dt.datetime.now(dt.timezone.utc).isoformat();report['unique_rows']=len(rows)
    selected=[r for r in rows if str(r.get('recent_capture_update','')).startswith(str(args.year)+'-')]
    report['selected_rows']=len(selected);report['unknown_dates']=sum(not r.get('recent_capture_update') for r in rows)
    (cache/'rows.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));(cache/'selected.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2));(cache/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False),flush=True)
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Build portable gallery data from a completed or explicitly partial collection."""
import argparse,collections,json,pathlib

def build(cache,root):
    report=json.loads((cache/'report.json').read_text());rows=json.loads((cache/'selected.json').read_text())
    previous=json.loads((root/'manifest.json').read_text()) if (root/'manifest.json').exists() else {}
    curated=json.loads((root/'curated-covers.json').read_text()) if (root/'curated-covers.json').exists() else {str(r['app_id']):r['cover'] for r in previous.get('apps',[]) if r.get('cover') and r.get('coverIndex',-1)>=0}
    view=[]
    for r in rows:
        links=list(dict.fromkeys(r.get('captures') or []))
        images=[u for u in links if u.split('?')[0].lower().endswith(('.jpg','.jpeg','.png','.webp','.gif'))]
        videos=list(dict.fromkeys([u for u in [r.get('onboarding_url')]+links if u and u.split('?')[0].lower().endswith(('.mp4','.webm','.mov','.m3u8'))]))
        cover=curated.get(str(r['app_id']))
        chosen=cover in images
        if not chosen:cover=images[0] if images else r.get('icon','')
        app={k:r.get(k) for k in ['app_id','info_id','app_name','category_name','create_time','recent_capture_update','icon']}
        app.update(captures=images,onboarding_url=videos[0] if videos else '',videos=videos,cover=cover,coverIndex=images.index(cover) if chosen else -1)
        view.append(app)
    meta={'status':report['status'],'year':report['year'],'date_field':report['date_field'],'collected_at':report['finished_at'],'total_apps':len(view),'note':'美国区公开列表；按截图更新时间筛选，展示列表当前提供的流程。'}
    if report.get('unknown_dates'):meta['note']+=f" {report['unknown_dates']} 条无截图日期的来源记录单独保留。"
    if report['status']!='complete':meta['note']+=' 未完成原因：'+report['stop_reason']
    counts={'apps':len(view),'images':sum(len(a['captures']) for a in view),'videos':sum(len(a['videos']) for a in view),'categories':dict(collections.Counter(a['category_name'] for a in view)),'distinct_app_ids':len({str(a['app_id']) for a in view})}
    if counts['distinct_app_ids']!=len(view):raise RuntimeError('Duplicate App IDs need explicit UI identity handling')
    report['selected_counts']=counts
    all_rows=json.loads((cache/'rows.json').read_text())
    (root/'reports'/'undated-records.json').write_text(json.dumps([r for r in all_rows if not r.get('recent_capture_update')],ensure_ascii=False,indent=2)+'\n')
    manifest={'schema_version':2,'source':'https://www.paywallpro.app/zh/paywalls','collection':report,'media_storage':'remote URLs only','apps':rows}
    (root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    (root/'data.js').write_text('window.PAYWALL_META = '+json.dumps(meta,ensure_ascii=False)+';\nwindow.PAYWALL_DATA = '+json.dumps(view,ensure_ascii=False)+';\n')
    (root/'reports'/'collection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(counts,ensure_ascii=False))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',type=pathlib.Path,required=True);p.add_argument('--root',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[1]);a=p.parse_args();build(a.cache,a.root)

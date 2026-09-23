#!/usr/bin/env python3
"""Reconcile cached page counts, IDs, date order and the exported 2026 selection."""
import argparse,collections,hashlib,json,pathlib

def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=pathlib.Path,required=True);p.add_argument('--root',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[1]);a=p.parse_args()
    report=json.loads((a.cache/'report.json').read_text());pages=[];rows=[]
    for n in range(1,report['pages']+1):
        file=a.cache/f'page-{n:04}.json';content=file.read_bytes();body=json.loads(content);assert str(body['code'])=='200'
        batch=body['data']['rows'];pages.append({'page':n,'rows':len(batch),'sha256':hashlib.sha256(content).hexdigest()});rows.extend(batch)
        assert body['data']['count']==report['reported_count'],'Source count changed'
    ids=[r['info_id'] for r in rows];dates=[r['recent_capture_update'] for r in rows if r.get('recent_capture_update')]
    assert len(ids)==len(set(ids)),'Duplicate info IDs'
    assert len(rows)==report['reported_count'],'Incomplete source list'
    assert dates==sorted(dates,reverse=True),'Source ordering changed'
    selected=[r for r in rows if str(r.get('recent_capture_update','')).startswith(str(report['year'])+'-')]
    manifest=json.loads((a.root/'manifest.json').read_text());assert selected==manifest['apps'],'Export differs from year selection'
    year_dates=[r['recent_capture_update'] for r in selected]
    result={'passed':True,'pages':len(pages),'source_rows':len(rows),'source_reported_count':report['reported_count'],'duplicate_info_ids':0,'unknown_dates':len(rows)-len(dates),'selected_rows':len(selected),'date_field':report['date_field'],'earliest':min(year_dates),'latest':max(year_dates),'year_counts':dict(collections.Counter(d[:4] for d in dates)),'page_fingerprints':pages}
    (a.root/'reports'/'integrity.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='page_fingerprints'},ensure_ascii=False))
if __name__=='__main__':main()

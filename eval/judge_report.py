"""Recompute judge validation from frozen verdicts and independently supplied labels.

python -m eval.judge_report             # inspect
python -m eval.judge_report --write     # update only judge section and referral list
"""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import yaml
from harness import ROOT
from eval.judge import rates, correct, bootstrap, configuration_digest


def read_verdicts(path, expected, versions=False):
    rows=[json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    keyed={}
    for row in rows:
        key=(row['id'],row['version']) if versions else row['id']
        if key in keyed or row['answer'] not in ('pass','fail'):
            raise ValueError(f'duplicate or invalid verdict in {path.name}')
        keyed[key]=row
    if set(keyed)!=set(expected):
        raise ValueError(f'{path.name}: IDs do not match expected coverage')
    return keyed


def summarize():
    split=yaml.safe_load((ROOT/'eval/labels/split.yaml').read_text())
    with (ROOT/'eval/labels/labels.csv').open(newline='') as f:
        rows=list(csv.DictReader(f))
    labels={r['id']:r['label'] for r in rows}
    outputs={p.stem:json.loads(p.read_text()) for p in (ROOT/'fixtures/judge/outputs').glob('*.json')}
    if len(rows)!=60 or len(labels)!=60 or set(labels)!=set(outputs) or any(r['label'] not in ('pass','fail') or not r['reason'].strip() for r in rows):
        raise ValueError('60 independent labels with reasons are required')
    all_ids=[i for group in split.values() for i in group]
    if len(all_ids)!=60 or set(all_ids)!=set(labels):
        raise ValueError('split must cover all IDs exactly once')
    if not 6<=len(split['examples'])<=12 or not all(24<=len(split[k])<=27 for k in ('tuning','test')):
        raise ValueError('split sizes are outside assignment ranges')
    frozen=json.loads((ROOT/'eval/judge/frozen.json').read_text())
    if frozen['digest']!=configuration_digest():
        raise ValueError('judge changed after freeze')
    test=split['test']; held={i:labels[i] for i in test}; base=ROOT/'eval/judge/verdicts'
    files=[read_verdicts(base/f'test_{n}.jsonl',test) for n in (1,2,3)]
    versions=read_verdicts(base/'versions.jsonl',[(i,v) for i in test for v in ('list','long')],True)
    recorded_ids=[]
    for p in (ROOT/'fixtures/traces7').glob('agent-*.jsonl'):
        lines=[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
        if any(x.get('type')=='tool_call' and x.get('name') in ('issues_comment','post_comment') for x in lines):recorded_ids.append(p.stem)
    recorded=read_verdicts(base/'recorded.jsonl',recorded_ids)
    if not recorded:raise ValueError('no recorded outputs')
    served={x['model'] for f in files+[versions,recorded] for x in f.values()}
    if len(served)!=1:raise ValueError('judge verdicts came from different models')
    verdicts=[{i:f[i]['answer'] for i in test} for f in files]
    first=verdicts[0]; tpr,tnr=rates(first,held)
    p=sum(x['answer']=='pass' for x in recorded.values())/len(recorded)
    corrected=correct(p,tpr,tnr)
    bounds=bootstrap(first,held,p,2000,7)
    majority={i:Counter(v[i] for v in verdicts).most_common(1)[0][0] for i in test}
    mtpr,mtnr=rates(majority,held)
    accuracy=lambda v:sum(v[i]==held[i] for i in test)/len(test)
    flips=[i for i in test if len({v[i] for v in verdicts})>1]
    moved=[i for i in test if any(versions[(i,v)]['answer']!=first[i] for v in ('list','long'))]
    systems={}
    for system in sorted({outputs[i]['system'] for i in test}):
        local={i:held[i] for i in test if outputs[i]['system']==system}
        stpr,stnr=rates(first,local)
        systems[system]={'tpr':stpr,'tnr':stnr,'items':len(local)}
    result={'split':{k:len(v) for k,v in split.items()},'model':next(iter(served)),
            'tpr':tpr,'tnr':tnr,'p':p,'corrected':corrected,'interval':list(bounds),'coin':False,
            'flip_rate':len(flips)/len(test),'majority':{'tpr':mtpr,'tnr':mtnr,'kept':accuracy(majority)>accuracy(first)},
            'moved_share':len(moved)/len(test),'by_system':systems}
    return result,flips


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true');args=parser.parse_args()
    result,flips=summarize()
    if args.write:
        path=ROOT/'reports/LAB_07.json';report=json.loads(path.read_text());report['judge']=result
        path.write_text(json.dumps(report,indent=2)+'\n')
        (ROOT/'eval/judge/for_a_person.txt').write_text(''.join(i+'\n' for i in flips))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()

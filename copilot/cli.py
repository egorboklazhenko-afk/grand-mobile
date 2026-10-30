import argparse
import gzip
import json
import os
import sys
from pathlib import Path
from .engine import Engine

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--rules',default=os.getenv('RULES_PATH','data/rules.json'))
    args=parser.parse_args()
    engine=Engine(args.rules)
    opener=gzip.open if args.input.endswith('.gz') else open
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    with opener(args.input,'rt',encoding='utf-8-sig') as source, open(args.output,'w',encoding='utf-8') as target:
        for n,line in enumerate(source,1):
            if not line.strip(): continue
            try:
                row=json.loads(line)
                result=engine.triage(row)
                if row.get('ticket_id'): result['ticket_id']=row['ticket_id']
                target.write(json.dumps(result,ensure_ascii=False)+'\n')
            except Exception as exc:
                print(f'Input line {n}: {type(exc).__name__}: {exc}',file=sys.stderr)
                raise SystemExit(2)

if __name__=='__main__': main()

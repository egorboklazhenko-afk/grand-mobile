"""Extract only known case files locally. Never package data/ with the submission."""
import argparse
import shutil
import tarfile
from pathlib import Path

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--archive',required=True)
    parser.add_argument('--with-tickets',action='store_true')
    args=parser.parse_args()
    target=Path(__file__).resolve().parent/'data'
    target.mkdir(exist_ok=True)
    files=['rules.json','taxonomy.json']
    if args.with_tickets: files+=['tickets_train.jsonl.gz','tickets_valid.jsonl']
    with tarfile.open(args.archive,'r:gz') as archive:
        for name in files:
            member=archive.getmember('handout/'+name)
            if not member.isfile() or member.size>512*1024*1024:
                raise ValueError('Unexpected archive member')
            with archive.extractfile(member) as source, (target/name).open('wb') as out:
                shutil.copyfileobj(source,out)
    print('Local case files ready in data/. Do not publish this directory.')

if __name__=='__main__':main()

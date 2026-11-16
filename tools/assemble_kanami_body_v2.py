"""Assemble reviewed symbol groups, rejecting missing or multiply-owned frames."""
import json
from pathlib import Path

ART=Path(__file__).resolve().parents[1]/'art/klbq_kanami/body-v2'

def main():
    frames={}
    for group in ('upper','hands','legs','head'):
        part=json.loads((ART/f'registration-{group}.json').read_text(encoding='utf8'))['frames']
        overlap=frames.keys() & part.keys()
        if overlap:raise ValueError(f'Duplicate group ownership: {overlap}')
        frames.update(part)
    native=json.loads((ART/'native-contract.json').read_text(encoding='utf8'))['frames']
    if set(native)-set(frames):raise ValueError('Missing frames: '+str(set(native)-set(frames)))
    (ART/'registration.json').write_text(json.dumps({'frames':frames},ensure_ascii=False,indent=2),encoding='utf8')
    print(f'Assembled {len(frames)} registered original frames')

if __name__=='__main__':main()

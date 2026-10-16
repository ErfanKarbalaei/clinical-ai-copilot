"""Print only requested repository files/ranges, never runtime secrets."""
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')
root=Path(__file__).resolve().parents[2]
for arg in sys.argv[1:]:
    parts=arg.split('::');p=root/parts[0]
    if p.name=='.env':raise ValueError('Runtime environment is private')
    print('\nFILE:',parts[0])
    lines=p.read_text(encoding='utf-8-sig').splitlines()
    lo,hi=(map(int,parts[1].split('-')) if len(parts)>1 else (1,len(lines)))
    print('\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines) if lo<=i+1<=hi))

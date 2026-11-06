import json,glob,re,sys,subprocess
sys.path.insert(0,'tools')
import batches
es=batches.index()
need=[e for e in es.values() if batches.needs_english(e)]
print('entries left',len(need),'by',{p:sum(1 for e in need if e['id'].startswith(p)) for p in ('s','ov1','ov4','exe','ov2','t')})
print('batches done',len(glob.glob('work/tl/b*.out.tsv')),'of',len(glob.glob('work/tl/b[0-9][0-9][0-9].tsv')))

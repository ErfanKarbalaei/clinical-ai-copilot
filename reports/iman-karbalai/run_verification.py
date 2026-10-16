import subprocess,os,json,time,sys
from pathlib import Path
a=Path(sys.argv[1]);n=sys.argv[2];r={}
for key,args in [('typescript',[n,'node_modules/typescript/bin/tsc','--noEmit','--incremental','false']),('lint',[n,'node_modules/eslint/bin/eslint.js','.']),('build',[n,'node_modules/next/dist/bin/next','build'])]:
 t=time.time();env=os.environ.copy();env['NEXT_TELEMETRY_DISABLED']='1'
 try:
  p=subprocess.run(args,cwd=r'F:\clinical-ai-copilot\frontend',capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180,env=env)
  (a/(key+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8');r[key]={'exit_code':p.returncode,'seconds':round(time.time()-t,2),'command':args}
 except subprocess.TimeoutExpired as e:r[key]={'timeout':180,'seconds':round(time.time()-t,2)}
 (a/'verification-results.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')

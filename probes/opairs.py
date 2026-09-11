import frida,sys,time,pathlib
pid=int(sys.argv[1]); secs=int(sys.argv[2]) if len(sys.argv)>2 else 30
out=pathlib.Path(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\opairs'); out.mkdir(exist_ok=True)
for f in out.glob('*.bin'): f.unlink()
s=frida.attach(pid); j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\opairs.js',encoding='utf-8').read())
def on(m,d):
    p=m.get('payload',m)
    if p.get('kind')=='wire' and d: (out/('w_%08d_%d.bin'%(p['t'],p['len']))).write_bytes(d)
    elif p.get('kind')=='buf' and d: (out/('b_%08d_%d_%d.bin'%(p['t'],p['from'],p['to']))).write_bytes(d)
    else: print(p,flush=True)
j.on('message',on); j.load(); time.sleep(secs)
try: s.detach()
except: pass
print("wire:",len(list(out.glob('w_*.bin'))),"buf:",len(list(out.glob('b_*.bin'))))

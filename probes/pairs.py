import frida,sys,time,pathlib,collections
pid=int(sys.argv[1]); secs=int(sys.argv[2]) if len(sys.argv)>2 else 40
out=pathlib.Path(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\pairs'); out.mkdir(exist_ok=True)
s=frida.attach(pid); j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\pairs.js',encoding='utf-8').read())
cmds=collections.Counter()
def on(m,d):
    p=m.get('payload',m)
    if p.get('kind')=='wire' and d:
        cmds[p['cmd']]+=1
        (out/('w_%08d_%04x_%d.bin'%(p['t'],p['cmd'],p['len']))).write_bytes(d)
    elif p.get('kind')=='buf' and d:
        (out/('b_%08d_%d_%d.bin'%(p['t'],p['from'],p['to']))).write_bytes(d)
    else: print(p,flush=True)
j.on('message',on); j.load(); time.sleep(secs); s.detach()
print("cmds:",{hex(k):v for k,v in cmds.items()})
print("wire:",len(list(out.glob('w_*.bin'))),"buf:",len(list(out.glob('b_*.bin'))))

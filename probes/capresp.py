import frida,sys,time,pathlib
pid=int(sys.argv[1]); out=pathlib.Path(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\netcap'); out.mkdir(exist_ok=True)
s=frida.attach(pid); j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\capresp.js',encoding='utf-8').read())
def on(m,d):
    p=m.get('payload',m)
    if p.get('kind')=='resp' and d:
        (out/('%05d_%d.bin'%(p['n'],len(d)))).write_bytes(d)
j.on('message',on); j.load(); time.sleep(20); s.detach()
print("saved", len(list(out.glob('*.bin'))))

import frida,sys,time,struct,pathlib
pid=int(sys.argv[1]); code=sys.argv[2]
out=pathlib.Path(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\oinject2'); out.mkdir(exist_ok=True)
for f in out.glob('*'): f.unlink()
def frame(code,seq): return (bytes.fromhex('0c0308020a01100010005e050100')+code.encode()+struct.pack('<I',seq)+bytes.fromhex('dc05')).hex()
s=frida.attach(pid); j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\oinject2.js',encoding='utf-8').read())
n=0
def on(m,d):
    global n
    p=m.get('payload',m); k=p.get('kind')
    if k=='dump' and d:
        (out/('display_%s_%d.bin'%(p['code'],p['count']))).write_bytes(d); print('display',p['code'],p['count'])
    elif k=='resp' and d:
        (out/('resp_%05d_%d.bin'%(n,p['len']))).write_bytes(d); n+=1
    else: print(p,flush=True)
j.on('message',on); j.load(); time.sleep(4)
print("inject rc=",j.exports_sync.inject(frame(code,0)))
time.sleep(6)
try: s.detach()
except: pass
print("responses",n)

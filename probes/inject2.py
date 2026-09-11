import frida,sys,time,json,struct,zlib,pathlib
pid=int(sys.argv[1]); code=sys.argv[2]; seq=int(sys.argv[3]) if len(sys.argv)>3 else 0
out=pathlib.Path(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\oinject'); out.mkdir(exist_ok=True)
for f in out.glob('*.bin'): f.unlink()
def frame(code,seq):
    return (bytes.fromhex('0c0308020a01100010005e050100')+code.encode()+struct.pack('<I',seq)+bytes.fromhex('dc05')).hex()
s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\inject.js',encoding='utf-8').read())
n=0
def on(m,d):
    global n
    p=m.get('payload',m)
    if p.get('kind')=='resp55e' and d:
        (out/('r_%05d_%d.bin'%(n,p['len']))).write_bytes(d); n+=1
    else: print(json.dumps(p,ensure_ascii=False)[:200],flush=True)
j.on('message',on); j.load(); time.sleep(2)
r=j.exports_sync.inject(frame(code,seq)); print("inject rc=",r)
time.sleep(5)
try: s.detach()
except: pass
print("responses:",n)

import frida,sys,time,json,binascii
pid=int(sys.argv[1]); secs=int(sys.argv[2]) if len(sys.argv)>2 else 12
s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\sendcap.js',encoding='utf-8').read())
def on(m,d):
    p=m.get('payload',m)
    if p.get('kind')=='send': print(f"  cmd=0x{p['cmd']} len={p['len']}  {binascii.hexlify(d).decode()}",flush=True)
    else: print(p,flush=True)
j.on('message',on); j.load(); time.sleep(secs)
try: s.detach()
except: pass

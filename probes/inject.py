import frida,sys,time,json,binascii,struct
pid=int(sys.argv[1]); code=sys.argv[2]; seq=int(sys.argv[3]) if len(sys.argv)>3 else 0
def frame(code,seq):
    b=bytes.fromhex('0c0308020a01100010005e050100')+code.encode()+struct.pack('<I',seq)+bytes.fromhex('dc05')
    return b.hex()
s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\inject.js',encoding='utf-8').read())
got=[]
def on(m,d):
    p=m.get('payload',m); k=p.get('kind')
    if k=='resp55e' and d:
        pt=bytes(x^0x49 for x in d)
        got.append((code,pt))
        print(f"[RESP 0x55e] len={p['len']} code_target={code}")
        print("  PT:",pt.hex(' '))
    else: print(json.dumps(p,ensure_ascii=False)[:200],flush=True)
j.on('message',on); j.load(); time.sleep(2)
f=frame(code,seq); print("inject frame:",f)
r=j.exports_sync.inject(f); print("WSASend rc=",r)
time.sleep(4)
print("responses:",len(got))
try: s.detach()
except: pass

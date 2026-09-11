import frida,sys,time,json,binascii
pid=int(sys.argv[1]); s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\netreq.js',encoding='utf-8').read())
def on(m,d):
    p=m.get('payload',m)
    if p.get('kind')=='send':
        print("SEND sock=%s ep=%s len=%d caller=%s\n   %s"%(p['sock'],p['ep'],p['len'],p['caller'],binascii.hexlify(d).decode() if d else ''),flush=True)
    else: print(json.dumps(p,ensure_ascii=False),flush=True)
j.on('message',on); j.load(); time.sleep(12); s.detach()

import frida,sys,time,json
pid=int(sys.argv[1]); s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\correl.js',encoding='utf-8').read())
def on(m,d):
    p=m.get('payload',m)
    if p.get('kind') in ('rx','tick'): print(json.dumps(p),flush=True)
    else: print(json.dumps(p,ensure_ascii=False),flush=True)
j.on('message',on); j.load(); time.sleep(15); s.detach()

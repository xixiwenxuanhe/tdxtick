import frida,sys,time,json
pid=int(sys.argv[1]); s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\vtable.js',encoding='utf-8').read())
def on(m,d):
    p=m.get('payload',m)
    if p.get('kind')=='vtable':
        print("code",p['code'])
        for i,e in enumerate(p['entries']): print("  ",i,e)
    else: print(json.dumps(p,ensure_ascii=False)[:600],flush=True)
j.on('message',on); j.load(); time.sleep(16); s.detach()

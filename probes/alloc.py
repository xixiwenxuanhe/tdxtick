import frida,sys,time,json
pid=int(sys.argv[1]); s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\alloc.js',encoding='utf-8').read())
seen=set()
def on(m,d):
    p=m.get('payload',m)
    if p.get('kind') in ('alloc','realloc'):
        k=(p.get('bt',[None])[0],p.get('size'))
        if k in seen: return
        seen.add(k)
    print(json.dumps(p,ensure_ascii=False)[:600],flush=True)
j.on('message',on); j.load(); time.sleep(15); s.detach()

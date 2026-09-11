import frida,sys,time,json
pid=int(sys.argv[1]); s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\caps2.js',encoding='utf-8').read())
seen=set()
def on(m,d):
    p=m.get('payload',m)
    if p.get('kind')=='deepcall':
        k=(p['fn'],tuple(p.get('bt',[])[:3]))
        if k in seen: return
        seen.add(k)
    print(json.dumps(p,ensure_ascii=False)[:500],flush=True)
j.on('message',on); j.load(); time.sleep(12); s.detach()

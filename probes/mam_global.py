import frida,sys,time,json
pid=int(sys.argv[1]); s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\mam_global.js',encoding='utf-8').read())
seen=set()
def on(m,d):
    p=m.get('payload',m)
    if p.get('kind')=='acc':
        k=(p['op'],p['from'])
        if k in seen: return
        seen.add(k)
    print(json.dumps(p,ensure_ascii=False)[:400],flush=True)
j.on('message',on); j.load(); time.sleep(18); s.detach()

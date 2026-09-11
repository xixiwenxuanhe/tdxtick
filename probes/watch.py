import frida,sys,time,json,traceback
pid=int(sys.argv[1])
try:
    s=frida.attach(pid)
    j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\watch.js',encoding='utf-8').read())
    seen=set()
    def on(m,d):
        p=m.get('payload',m)
        k=(p.get('kind'),p.get('from'))
        if p.get('kind')=='access':
            if p['from'] in seen: return
            seen.add(p['from'])
        print(json.dumps(p,ensure_ascii=False),flush=True)
    j.on('message',on); j.load()
    time.sleep(12)
    s.detach()
except Exception as e: traceback.print_exc()

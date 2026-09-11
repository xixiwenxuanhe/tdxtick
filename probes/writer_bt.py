import frida,sys,time,json
pid=int(sys.argv[1]); seen=set()
s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\writer_bt.js',encoding='utf-8').read())
def on(m,d):
    p=m.get('payload',m)
    if p.get('kind')=='access':
        key=tuple(p.get('bt',[]))+ (p.get('op'),)
        if key in seen: return
        seen.add(key)
    print(json.dumps(p,ensure_ascii=False),flush=True)
j.on('message',on); j.load(); time.sleep(12); s.detach()

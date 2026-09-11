import frida,sys,time,json,traceback
pid=int(sys.argv[1]); seen=set()
s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\find_writer.js',encoding='utf-8').read())
def on(m,d):
    p=m.get('payload',m)
    if p.get('kind')=='copy':
        if p['retmod'] in seen: return
        seen.add(p['retmod'])
    print(json.dumps(p,ensure_ascii=False),flush=True)
j.on('message',on); j.load()
time.sleep(12); s.detach()

import frida,sys,time,json
pid=int(sys.argv[1]); s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\stalker.js',encoding='utf-8').read())
def on(m,d):
    p=m.get('payload',m)
    if p.get('kind')=='calls':
        print("total calls",p['n'])
        for x in p['uniq']: print("  ",x)
    else: print(json.dumps(p,ensure_ascii=False)[:300],flush=True)
j.on('message',on); j.load(); time.sleep(20); s.detach()

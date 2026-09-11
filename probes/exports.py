import frida,sys,time,json
pid=int(sys.argv[1]); s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\exports.js',encoding='utf-8').read())
def on(m,d):
    p=m.get('payload',m)
    if p.get('kind')=='exports':
        print("=== "+p['mod']+" ("+str(len(p['list']))+" exports) ===")
        for x in p['list']: print("   ",x)
    else: print(json.dumps(p,ensure_ascii=False))
j.on('message',on); j.load(); time.sleep(4); s.detach()

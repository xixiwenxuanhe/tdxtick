import frida,sys,time,json
pid=int(sys.argv[1]); s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\srcdump.js',encoding='utf-8').read())
def on(m,d): print(json.dumps(m.get('payload',m),ensure_ascii=False)[:500],flush=True)
j.on('message',on); j.load(); time.sleep(15); s.detach()

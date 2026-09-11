import frida,sys,time,json
pid=int(sys.argv[1]); s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\deep.js',encoding='utf-8').read())
j.on('message',lambda m,d: print(json.dumps(m.get('payload',m),ensure_ascii=False),flush=True))
j.load(); time.sleep(10); s.detach()

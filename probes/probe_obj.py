import frida,sys,time,json,binascii,traceback
pid=int(sys.argv[1])
try:
    s=frida.attach(pid)
    src=open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\probe_obj.js',encoding='utf-8').read()
    j=s.create_script(src)
    def on(m,d):
        p=m.get('payload',m)
        if d: p['data_hex']=binascii.hexlify(d).decode()
        print(json.dumps(p,ensure_ascii=False),flush=True)
    j.on('message',on); j.load()
    time.sleep(15)
    s.detach()
except Exception as e:
    traceback.print_exc()

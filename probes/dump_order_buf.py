import frida,sys,time,pathlib
pid=int(sys.argv[1])
s=frida.attach(pid); j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\dump_order_buf.js',encoding='utf-8').read())
def on(m,d):
    p=m.get('payload',m)
    if p.get('kind')=='dump' and d:
        pathlib.Path(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\orderbuf.bin').write_bytes(d)
        print('dumped',p['code'],p['count'],len(d))
    else: print(p)
j.on('message',on); j.load(); time.sleep(6)
try: s.detach()
except: pass

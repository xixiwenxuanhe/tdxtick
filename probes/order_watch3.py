import frida,sys,time,json
pid=int(sys.argv[1]); secs=int(sys.argv[2]) if len(sys.argv)>2 else 12
s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\order_watch.js',encoding='utf-8').read())
def on(m,d):
    p=m.get('payload',m); k=p.get('kind')
    if k=='rx': print(f"  t={p['t']:>7} RX cmd=0x{p['cmd']} len={p['len']}",flush=True)
    elif k=='ORDER': print(f"  t={p['t']:>7} ORDER {p['code']} count={p['count']}",flush=True)
j.on('message',on); j.load(); time.sleep(secs)
try: s.detach()
except: pass

import frida,sys,time,json,collections
pid=int(sys.argv[1]); secs=int(sys.argv[2]) if len(sys.argv)>2 else 20
s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\order_watch.js',encoding='utf-8').read())
ev=[]
def on(m,d):
    p=m.get('payload',m); k=p.get('kind')
    if k=='rx': ev.append((p['t'],'RX',p['cmd'],p['len']))
    elif k=='ORDER': ev.append((p['t'],'ORDER',p['code'],p['count']))
    elif k=='ready': print('ready',flush=True)
j.on('message',on); j.load(); time.sleep(secs); s.detach()
ev.sort()
for t,k,*rest in ev:
    print(f"  {t:>7} {k:6} {rest}")

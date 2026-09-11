import frida,sys,time,json,collections
pid=int(sys.argv[1]); secs=int(sys.argv[2]) if len(sys.argv)>2 else 60
s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\order_watch.js',encoding='utf-8').read())
cmds=collections.Counter(); orders=0
def on(m,d):
    p=m.get('payload',m); k=p.get('kind')
    if k=='rx': cmds[p['cmd']]+=1
    elif k=='ORDER':
        global orders; orders+=1
        print(f"[ORDER] t={p['t']} code={p['code']} count={p['count']} ptr={p['ptr']}",flush=True)
    else: print(json.dumps(p,ensure_ascii=False)[:200],flush=True)
j.on('message',on); j.load(); time.sleep(secs); s.detach()
print("wire cmds:",{hex(int(k,16)):v for k,v in cmds.items()})
print("order-hook fires:",orders)

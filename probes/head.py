import frida,sys,time,json,binascii,struct
pid=int(sys.argv[1]); s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\head.js',encoding='utf-8').read())
def clk(t):
    t+=21600; return f'{t//3600:02}:{t//60%60:02}:{t%60:02}'
def on(m,d):
    p=m.get('payload',m)
    if d and p.get('kind') in ('head','tail'):
        s2,price,lots,odd,dr,bid,ask=struct.unpack_from('<HIIbBII',d,0)
        p['decoded']=dict(time=clk(s2),price=price/10000,shares=lots*100+odd,dir=dr,bid=bid,ask=ask)
    print(json.dumps(p,ensure_ascii=False),flush=True)
j.on('message',on); j.load(); time.sleep(8); s.detach()

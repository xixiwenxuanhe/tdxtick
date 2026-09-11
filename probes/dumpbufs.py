import frida,sys,time,json,binascii,struct
pid=int(sys.argv[1]); s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\dumpbufs.js',encoding='utf-8').read())
def on(m,d):
    p=m.get('payload',m)
    if p.get('kind')=='buf' and d:
        print("=== buf %s @ %s ==="%(p['off'],p['ptr']))
        print("raw:",binascii.hexlify(d[:0x60]).decode())
        # try parse as 20-byte trades
        for i in range(0,0x40,20):
            if i+20<=len(d):
                s2,price,lots,odd,dr,bid,ask=struct.unpack_from('<HIIbBII',d,i)
                print("  trade[%d] t=%d px=%.4f lots=%d odd=%d dir=%d bid=%d ask=%d"%(i//20,s2,price/10000,lots,odd,dr,bid,ask))
    else:
        print(json.dumps(p,ensure_ascii=False)[:400],flush=True)
j.on('message',on); j.load(); time.sleep(8); s.detach()

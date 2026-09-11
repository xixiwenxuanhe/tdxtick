import frida,sys,time,json,binascii
pid=int(sys.argv[1]); s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\objdump.js',encoding='utf-8').read())
def on(m,d):
    p=m.get('payload',m)
    if d:
        p['hex']=binascii.hexlify(d).decode()
    if p.get('kind')=='cands':
        for c in p['cands']: print("cand +%s = %s"%(hex(c['off']),c['val']))
        return
    print(json.dumps({k:v for k,v in p.items() if k!='hex'},ensure_ascii=False),flush=True)
    if p.get('kind') in ('dump','state'):
        open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\%s_%s.bin'%(p['kind'],p.get('obj',p.get('st','x')).replace('0x','')),'wb').write(d)
j.on('message',on); j.load(); time.sleep(8); s.detach()

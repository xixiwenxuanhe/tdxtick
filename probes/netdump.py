import frida,sys,time,json,binascii,collections
pid=int(sys.argv[1]); s=frida.attach(pid)
j=s.create_script(open(r'C:\Users\xixiw\Downloads\tdx-interface-research\probe\netdump.js',encoding='utf-8').read())
sizes=collections.Counter(); callers=collections.Counter(); shown=0
def on(m,d):
    global shown
    p=m.get('payload',m)
    if p.get('kind')=='pkt':
        sizes[p['size']]+=1; callers[p['caller']]+=1
        if shown<12:
            hexs=binascii.hexlify(d).decode() if d else ''
            print("pkt size=%d caller=%s %s"%(p['size'],p['caller'],hexs),flush=True); shown+=1
    elif p.get('kind')=='ready':
        print("READY",p,flush=True)
    else: print(json.dumps(p,ensure_ascii=False),flush=True)
j.on('message',on); j.load(); time.sleep(10); s.detach()
print("=== sizes ==="); print(sizes.most_common(15))
print("=== callers ==="); print(callers.most_common(15))

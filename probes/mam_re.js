const MODS = Process.enumerateModules();
function modof(a){ try{ const x=ptr(a); for(const m of MODS){ if(x.compare(m.base)>=0 && x.compare(m.base.add(m.size))<0) return m.name+'+0x'+x.sub(m.base).toString(16); } }catch(e){} return String(a); }
const ws2 = Process.getModuleByName('WS2_32.dll');
const k32 = Process.getModuleByName('kernel32.dll');
const pending = new Map();
const seen = {};
let armed = false, cnt = 0;

function onAccess(page, d){
  try{
    const key = d.operation + '@' + modof(d.from);
    cnt++;
    if(!seen[key] && cnt < 300){ seen[key] = 1; send({kind:'acc', op:d.operation, from:modof(d.from), addr:d.address.toString()}); }
    try{ MemoryAccessMonitor.disable(); }catch(e){}
    try{ arm(page); }catch(e){}
  }catch(e){ send({kind:'innerr', e:String(e)}); }
}
function arm(page){
  MemoryAccessMonitor.enable({ base: page, size: 0x2000 }, { onAccess(d){ onAccess(page, d); } });
}

Interceptor.attach(ws2.findExportByName('WSARecv'), { onEnter(args){ try{ const ov=args[5]; if(!ov.isNull()) pending.set(ov.toString(), args[1].add(8).readPointer()); }catch(e){} } });
Interceptor.attach(k32.findExportByName('GetQueuedCompletionStatus'), {
  onEnter(args){ this.ovp = args[3]; },
  onLeave(ret){ try{
    if(armed || ret.toInt32()===0) return;
    const ov = this.ovp.readPointer(); if(ov.isNull()) return;
    const buf = pending.get(ov.toString()); if(!buf) return; pending.delete(ov.toString());
    if(buf.add(10).readU16() !== 0x554) return;
    const ln = buf.add(12).readU16(); if(ln<1 || ln>60000) return;
    const pa = buf.add(16); const t = parseInt(pa.toString());
    const page = ptr((t - (t % 0x1000)) >>> 0);
    armed = true; send({kind:'arm', page:page.toString(), len:ln}); arm(page);
  }catch(e){ send({kind:'err', e:String(e)}); } }
});
send({kind:'ready'});

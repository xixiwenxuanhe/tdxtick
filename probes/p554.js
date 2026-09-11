const MODS=Process.enumerateModules();
function modof(a){try{const x=ptr(a);for(const m of MODS){if(x.compare(m.base)>=0&&x.compare(m.base.add(m.size))<0)return m.name+'+0x'+x.sub(m.base).toString(16);}}catch(e){} return String(a);}
const ws2=Process.getModuleByName('WS2_32.dll'),k32=Process.getModuleByName('kernel32.dll'),crt=Process.getModuleByName('MSVCR100.dll');
const pending=new Map(); let last=null; const hits={};
Interceptor.attach(ws2.findExportByName('WSARecv'),{onEnter(args){try{const ov=args[5];if(!ov.isNull())pending.set(ov.toString(),args[1].add(8).readPointer());}catch(e){}}});
Interceptor.attach(k32.findExportByName('GetQueuedCompletionStatus'),{onEnter(args){this.ovp=args[3];},onLeave(ret){try{
  if(ret.toInt32()===0)return; const ov=this.ovp.readPointer(); if(ov.isNull())return;
  const buf=pending.get(ov.toString()); if(!buf)return; pending.delete(ov.toString());
  if(buf.add(10).readU16()!==0x554) return;
  const ln=buf.add(12).readU16(); if(ln<1||ln>60000) return;
  const pa=buf.add(16); last={lo:pa,hi:pa.add(ln+32),t:Date.now()};
}catch(e){}}});
['memcpy','memmove'].forEach(nm=>{const a=crt.findExportByName(nm); if(!a)return; Interceptor.attach(a,{onEnter(args){try{
  if(!last||Date.now()-last.t>1500)return; const src=args[1];
  if(src.compare(last.lo)>=0&&src.compare(last.hi)<0){
    const key=this.returnAddress.toString(); if(hits[key])return; hits[key]=1;
    let bt=[]; try{bt=Thread.backtrace(this.context,Backtracer.ACCURATE).map(modof).slice(0,10);}catch(e){bt=['btfail'];}
    send({kind:'read554',src:src.toString(),ret:modof(this.returnAddress),bt});
  }
}catch(e){}}});});
send({kind:'ready'});

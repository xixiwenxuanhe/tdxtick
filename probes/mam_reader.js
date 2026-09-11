const MODS=Process.enumerateModules();
function modof(a){try{const x=ptr(a);for(const m of MODS){if(x.compare(m.base)>=0&&x.compare(m.base.add(m.size))<0)return m.name+'+0x'+x.sub(m.base).toString(16);}}catch(e){} return String(a);}
const ws2=Process.getModuleByName('WS2_32.dll'), k32=Process.getModuleByName('kernel32.dll');
const pending=new Map(); let armed=false, cnt=0;
Interceptor.attach(ws2.findExportByName('WSARecv'),{onEnter(args){try{const ov=args[5]; if(!ov.isNull()) pending.set(ov.toString(), args[1].add(8).readPointer());}catch(e){}}});
Interceptor.attach(k32.findExportByName('GetQueuedCompletionStatus'),{onEnter(args){this.ovp=args[3];},onLeave(ret){try{
  if(ret.toInt32()===0)return; const ov=this.ovp.readPointer(); if(ov.isNull())return;
  const buf=pending.get(ov.toString()); if(!buf)return; pending.delete(ov.toString());
  if(armed) return;
  if(buf.add(10).readU16()!==0x554) return;
  const ln=buf.add(12).readU16();
  const pa=buf.add(16); const t=parseInt(pa.toString()); const page=ptr((t-(t%0x1000))>>>0);
  armed=true;
  send({kind:'arm',payload:pa.toString(),len:ln,page:page.toString(),head:Array.from(new Uint8Array(pa.readByteArray(Math.min(ln,24)))).map(b=>b.toString(16)).join(' ')});
  MemoryAccessMonitor.enable({base:page,size:0x1000},{onAccess(d){try{
    if(cnt>=40) return; cnt++;
    send({kind:'acc',op:d.operation,from:modof(d.from),addr:d.address.toString()});
  }catch(e){}}});
  send({kind:'monitor_on'});
}catch(e){send({kind:'err',e:String(e)});}}});
send({kind:'ready'});

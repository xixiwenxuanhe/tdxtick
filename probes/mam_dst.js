const MODS=Process.enumerateModules();
function modof(a){try{const x=ptr(a);for(const m of MODS){if(x.compare(m.base)>=0&&x.compare(m.base.add(m.size))<0)return m.name+'+0x'+x.sub(m.base).toString(16);}}catch(e){} return String(a);}
const ws2=Process.getModuleByName('WS2_32.dll'),k32=Process.getModuleByName('kernel32.dll'),crt=Process.getModuleByName('MSVCR100.dll');
const pending=new Map(); let last=null; const seen={}; let armed=false,cnt=0;
function onAcc(page,d){ try{
  const key=d.operation+'@'+modof(d.from); cnt++;
  if(!seen[key]&&cnt<80){seen[key]=1; send({kind:'acc',op:d.operation,from:modof(d.from),addr:d.address.toString()});}
  try{MemoryAccessMonitor.disable();}catch(e){}
  try{arm(page);}catch(e){}
}catch(e){send({kind:'inerr',e:String(e)});} }
function arm(page){ MemoryAccessMonitor.enable({base:page,size:0x1000},{onAccess(d){onAcc(page,d);}}); }
Interceptor.attach(ws2.findExportByName('WSARecv'),{onEnter(args){try{const ov=args[5];if(!ov.isNull())pending.set(ov.toString(),args[1].add(8).readPointer());}catch(e){}}});
Interceptor.attach(k32.findExportByName('GetQueuedCompletionStatus'),{onEnter(args){this.ovp=args[3];},onLeave(ret){try{
  if(ret.toInt32()===0)return; const ov=this.ovp.readPointer(); if(ov.isNull())return;
  const buf=pending.get(ov.toString()); if(!buf)return; pending.delete(ov.toString());
  if(buf.add(10).readU16()!==0x554)return; const ln=buf.add(12).readU16(); if(ln<1||ln>60000)return;
  last={lo:buf.add(16),hi:buf.add(16).add(ln+16),t:Date.now()};
}catch(e){}}});
['memcpy','memmove'].forEach(nm=>{const a=crt.findExportByName(nm); if(!a)return; Interceptor.attach(a,{onEnter(args){try{
  if(armed||!last)return; const src=args[1];
  if(src.compare(last.lo)>=0&&src.compare(last.hi)<0){
    const dst=args[0], len=parseInt(args[2].toString());
    if(len<8||len>60000)return;
    const t=parseInt(dst.toString()); const page=ptr((t-(t%0x1000))>>>0);
    armed=true; send({kind:'dstcap',caller:modof(this.returnAddress),dst:dst.toString(),len,page:page.toString()});
    arm(page);
  }
}catch(e){}}});});
send({kind:'ready'});

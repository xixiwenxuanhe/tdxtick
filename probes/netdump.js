const ws2=Process.getModuleByName('WS2_32.dll');
const k32=Process.getModuleByName('kernel32.dll');
function modof(a){let x; try{x=ptr(a);}catch(e){return '?';}for(const m of Process.enumerateModules()){if(x.compare(m.base)>=0&&x.compare(m.base.add(m.size))<0)return m.name+'+0x'+x.sub(m.base).toString(16);}return '?';}
const pending=new Map();
let n=0;
const recvAddr=ws2.findExportByName('WSARecv');
Interceptor.attach(recvAddr,{onEnter(args){try{
  const ov=args[5]; if(ov.isNull())return;
  const wbuf=args[1];
  const len=wbuf.readU32(); const buf=wbuf.add(8).readPointer();
  pending.set(ov.toString(),{buf,len,ret:this.returnAddress.toString()});
}catch(e){}}});
const gqcs=k32.findExportByName('GetQueuedCompletionStatus');
if(gqcs) Interceptor.attach(gqcs,{onLeave(retval){try{
  const ovp=this.context.rsp ? null : null;
}catch(e){}}});
// GQCS onLeave needs args; use onEnter+onLeave with explicit arg capture
if(gqcs) Interceptor.attach(gqcs,{
  onEnter(args){ this.ovp=args[3]; },
  onLeave(retval){ try{
    if(retval.toInt32()===0) return;
    const ov=this.ovp.readPointer(); if(ov.isNull())return;
    const e=pending.get(ov.toString()); if(!e)return; pending.delete(ov.toString());
    if(n>=300)return; n++;
    const bytes=Math.min(e.len,64);
    let data=null; try{ data=e.buf.readByteArray(bytes); }catch(err){}
    send({kind:'pkt',size:e.len,ov:ov.toString(),caller:modof(e.ret)},data);
  }catch(e){send({kind:'e',m:String(e)});}}});
send({kind:'ready',recv:recvAddr.toString(),gqcs:gqcs?gqcs.toString():null});

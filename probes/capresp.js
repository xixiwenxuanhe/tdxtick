const ws2=Process.getModuleByName('WS2_32.dll'), k32=Process.getModuleByName('kernel32.dll');
const pending=new Map(); let n=0;
const recvAddr=ws2.findExportByName('WSARecv');
Interceptor.attach(recvAddr,{onEnter(args){try{
  const ov=args[5]; if(ov.isNull())return; const wbuf=args[1];
  pending.set(ov.toString(),{buf:wbuf.add(8).readPointer(),cap:wbuf.readU32()});
}catch(e){}}});
const gqcs=k32.findExportByName('GetQueuedCompletionStatus');
Interceptor.attach(gqcs,{onEnter(args){this.ovp=args[3];},onLeave(retval){try{
  if(retval.toInt32()===0)return; const ov=this.ovp.readPointer(); if(ov.isNull())return;
  const e=pending.get(ov.toString()); if(!e)return; pending.delete(ov.toString());
  const bytes=Math.min(e.cap, 8192); if(bytes<=0)return; n++;
  send({kind:'resp',n,bytes}, e.buf.readByteArray(bytes));
}catch(e){}}});
send({kind:'ready'});

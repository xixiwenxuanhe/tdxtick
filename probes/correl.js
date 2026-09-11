const ws2=Process.getModuleByName('WS2_32.dll'), k32=Process.getModuleByName('kernel32.dll');
const base=Process.getModuleByName('TdxW.exe').base;
const pending=new Map();
const t0=Date.now();
Interceptor.attach(ws2.findExportByName('WSARecv'),{onEnter(args){try{
  const ov=args[5]; if(ov.isNull())return; const w=args[1];
  pending.set(ov.toString(),{buf:w.add(8).readPointer()});
}catch(e){}}});
Interceptor.attach(k32.findExportByName('GetQueuedCompletionStatus'),{onEnter(args){this.ovp=args[3];},onLeave(ret){try{
  if(ret.toInt32()===0)return; const ov=this.ovp.readPointer(); if(ov.isNull())return;
  const e=pending.get(ov.toString()); if(!e)return; pending.delete(ov.toString());
  const cmd=e.buf.add(8).readU16();
  send({kind:'rx',t:Date.now()-t0,cmd:cmd.toString(16),b0:e.buf.readU32().toString(16)});
}catch(e){}}});
let last=null;
Interceptor.attach(base.add(0x79bd0b),{onEnter(a){try{
  const o=this.context.rdi; const n=o.add(0x250).readU32();
  if(n!==last){ send({kind:'tick',t:Date.now()-t0,count:n,delta:last===null?0:n-last}); last=n; }
}catch(e){}}});
send({kind:'ready'});

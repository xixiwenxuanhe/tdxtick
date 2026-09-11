const ws2=Process.getModuleByName('WS2_32.dll'),k32=Process.getModuleByName('kernel32.dll'),TdxW=Process.getModuleByName('TdxW.exe');
const pending=new Map(); const t0=Date.now();
Interceptor.attach(ws2.findExportByName('WSARecv'),{onEnter(args){try{const ov=args[5];if(!ov.isNull())pending.set(ov.toString(),args[1].add(8).readPointer());}catch(e){}}});
Interceptor.attach(k32.findExportByName('GetQueuedCompletionStatus'),{onEnter(args){this.ovp=args[3];},onLeave(ret){try{
  if(ret.toInt32()===0)return; const ov=this.ovp.readPointer(); if(ov.isNull())return;
  const buf=pending.get(ov.toString()); if(!buf)return; pending.delete(ov.toString());
  if(buf.add(10).readU16()!==0x55e) return;
  const ln=buf.add(12).readU16(); if(ln<1||ln>8192) return;
  send({kind:'wire',t:Date.now()-t0,len:ln}, buf.add(16).readByteArray(ln));
}catch(e){}}});
let obj=null,last=-1;
Interceptor.attach(TdxW.base.add(0x760a80),{onEnter(a){try{
  if(obj) return; obj=a[0];
  send({kind:'obj',t:Date.now()-t0,code:obj.add(0x68).readPointer().readCString(6)});
  last=obj.add(0x254).readU32();
  setInterval(()=>{ try{ const n=obj.add(0x254).readU32();
    if(n!==last){ const from=last; last=n; const p=obj.add(0x3d0).readPointer();
      send({kind:'buf',t:Date.now()-t0,from,to:n}, p.add(from*20).readByteArray((n-from)*20)); }
  }catch(e){} },2);
}catch(e){send({kind:'err',e:String(e)});}}});
send({kind:'ready'});

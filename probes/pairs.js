const ws2=Process.getModuleByName('WS2_32.dll'), k32=Process.getModuleByName('kernel32.dll'), TdxW=Process.getModuleByName('TdxW.exe');
const pending=new Map(); const t0=Date.now();
Interceptor.attach(ws2.findExportByName('WSARecv'),{onEnter(args){try{ const ov=args[5]; if(ov.isNull())return; pending.set(ov.toString(),{buf:args[1].add(8).readPointer(),cap:args[1].readU32()}); }catch(e){}}});
Interceptor.attach(k32.findExportByName('GetQueuedCompletionStatus'),{onEnter(args){this.ovp=args[3];},onLeave(ret){try{
  if(ret.toInt32()===0)return; const ov=this.ovp.readPointer(); if(ov.isNull())return;
  const e=pending.get(ov.toString()); if(!e)return; pending.delete(ov.toString());
  // parse frames in the buffer
  let i=0, n=0;
  while(i+16<=e.cap && n<8){
    const cmd=e.buf.add(i+10).readU16(), ln=e.buf.add(i+12).readU16(), ln2=e.buf.add(i+14).readU16();
    if(ln===0||ln>60000||ln!==ln2||i+16+ln>e.cap) break;
    if(ln>=16) send({kind:'wire',t:Date.now()-t0,cmd,len:ln}, e.buf.add(i+16).readByteArray(ln));
    i+=16+ln; n++;
  }
}catch(e){}}});
let obj=null,last=-1;
Interceptor.attach(TdxW.base.add(0x79bd0b),{onEnter(a){try{
  if(obj) return; obj=this.context.rdi;
  send({kind:'obj',t:Date.now()-t0,obj:obj.toString(),code:obj.add(0x68).readPointer().readCString(6)});
  last=obj.add(0x250).readU32();
  setInterval(()=>{ try{ const n=obj.add(0x250).readU32();
    if(n!==last){ const from=last; last=n; const p=obj.add(0x348).readPointer();
      send({kind:'buf',t:Date.now()-t0,from,to:n}, p.add(from*20).readByteArray((n-from)*20)); }
  }catch(e){} },2);
}catch(e){send({kind:'err',e:String(e)});}}});
send({kind:'ready'});

const MODS=Process.enumerateModules();
function modof(a){try{const x=ptr(a);for(const m of MODS){if(x.compare(m.base)>=0&&x.compare(m.base.add(m.size))<0)return m.name+'+0x'+x.sub(m.base).toString(16);}}catch(e){} return String(a);}
const ws2=Process.getModuleByName('WS2_32.dll'),k32=Process.getModuleByName('kernel32.dll'),TdxW=Process.getModuleByName('TdxW.exe');
const pending=new Map(); const t0=Date.now();
Interceptor.attach(ws2.findExportByName('WSARecv'),{onEnter(args){try{const ov=args[5];if(!ov.isNull())pending.set(ov.toString(),args[1].add(8).readPointer());}catch(e){}}});
Interceptor.attach(k32.findExportByName('GetQueuedCompletionStatus'),{onEnter(args){this.ovp=args[3];},onLeave(ret){try{
  if(ret.toInt32()===0)return; const ov=this.ovp.readPointer(); if(ov.isNull())return;
  const buf=pending.get(ov.toString()); if(!buf)return; pending.delete(ov.toString());
  const cmd=buf.add(10).readU16(), ln=buf.add(12).readU16();
  if(ln>0&&ln<60000) send({kind:'rx',t:Date.now()-t0,cmd:cmd.toString(16),len:ln});
}catch(e){}}});
// 委托渲染
Interceptor.attach(TdxW.base.add(0x760a80),{onEnter(a){try{
  const o=a[0]; const code=o.add(0x68).readPointer().readCString(6);
  const n=o.add(0x254).readU32(), p=o.add(0x3d0).readPointer();
  send({kind:'ORDER',t:Date.now()-t0,code,count:n,ptr:p.toString()});
}catch(e){send({kind:'ordererr',e:String(e)});}}});
// 成交渲染
let tn=0;
Interceptor.attach(TdxW.base.add(0x79bd0b),{onEnter(a){try{ tn++; if(tn%200===0) send({kind:'trade',t:Date.now()-t0,n:tn}); }catch(e){}}});
send({kind:'ready'});

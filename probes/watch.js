const base=Process.getModuleByName('TdxW.exe').base;
send({kind:'base',base:base.toString()});
function modof(addr){
  const a=ptr(addr); const ms=Process.enumerateModules();
  for(const m of ms){ if(a.compare(m.base)>=0 && a.compare(m.base.add(m.size))<0)
     return m.name+'+0x'+a.sub(m.base).toString(16); }
  return '?';
}
let armed=false;
Interceptor.attach(base.add(0x79bd0b),{onEnter(a){try{
  if(armed) return;
  const o=this.context.rdi;
  const cnt=o.add(0x250).readU32(), p=o.add(0x348).readPointer();
  const tail=p.add(cnt*20);
  const t=parseInt(tail.toString());
  const pageAddr=ptr((t-(t%0x1000))>>>0);
  armed=true;
  send({kind:'arm',count:cnt,tail:tail.toString(),page:pageAddr.toString()});
  try{ MemoryAccessMonitor.enable({base:pageAddr,size:0x4000},{onAccess(d){
      send({kind:'access',op:d.operation,from:d.from.toString(),mod:modof(d.from),address:d.address.toString()});}});
      send({kind:'monitor_on'});
  }catch(e){send({kind:'monitor_err',e:String(e)});}
}catch(e){send({kind:'err',e:String(e)});}}});
send({kind:'ready'});

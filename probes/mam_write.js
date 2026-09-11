const MODS=Process.enumerateModules();
function modof(a){try{const x=ptr(a);for(const m of MODS){if(x.compare(m.base)>=0&&x.compare(m.base.add(m.size))<0)return m.name+'+0x'+x.sub(m.base).toString(16);}}catch(e){} return String(a);}
const TdxW=Process.getModuleByName('TdxW.exe');
let armed=false, w=0;
Interceptor.attach(TdxW.base.add(0x79bd0b),{onEnter(a){try{
  if(armed) return; armed=true;
  const o=this.context.rdi, cnt=o.add(0x250).readU32(), p=o.add(0x348).readPointer();
  const t=parseInt(p.add(cnt*20).toString()); const page=ptr((t-(t%0x1000))>>>0);
  send({kind:'arm',code:o.add(0x68).readPointer().readCString(6),count:cnt,page:page.toString()});
  MemoryAccessMonitor.enable({base:page,size:0x10000},{onAccess(d){try{
    if(d.operation!=='write'||w>=25) return; w++;
    let bt=[]; try{bt=Thread.backtrace().map(modof).slice(0,14);}catch(e){bt=['btfail:'+e];}
    send({kind:'write',addr:d.address.toString(),from:modof(d.from),bt});
  }catch(e){send({kind:'inerr',e:String(e)});}}});
  send({kind:'monitor_on'});
}catch(e){send({kind:'err',e:String(e)});}}});
send({kind:'ready'});

const base=Process.getModuleByName('TdxW.exe').base;
function modof(a){const x=ptr(a);for(const m of Process.enumerateModules()){if(x.compare(m.base)>=0&&x.compare(m.base.add(m.size))<0)return m.name+'+0x'+x.sub(m.base).toString(16);}return '?';}
let armed=false;
Interceptor.attach(base.add(0x79bd0b),{onEnter(a){try{
  if(armed)return;
  const o=this.context.rdi;
  const cnt=o.add(0x250).readU32(), p=o.add(0x348).readPointer();
  const t=parseInt(p.add(cnt*20).toString()); const page=ptr((t-(t%0x1000))>>>0);
  armed=true;
  send({kind:'arm',count:cnt,ptr:p.toString(),page:page.toString()});
  MemoryAccessMonitor.enable({base:page,size:0x3000},{onAccess(d){try{
    let bt=[]; try{ bt=Thread.backtrace().map(x=>modof(x)); }catch(e){ bt=['btfail:'+e]; }
    send({kind:'access',op:d.operation,from:modof(d.from),address:d.address.toString(),bt});
  }catch(e){send({kind:'inerr',e:String(e)});}}});
  send({kind:'monitor_on'});
}catch(e){send({kind:'err',e:String(e)});}}});
send({kind:'ready'});

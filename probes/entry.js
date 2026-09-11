const MODS=Process.enumerateModules();
function modof(a){try{const x=ptr(a);for(const m of MODS){if(x.compare(m.base)>=0&&x.compare(m.base.add(m.size))<0)return m.name+'+0x'+x.sub(m.base).toString(16);}}catch(e){} return String(a);}
const crt=Process.getModuleByName('MSVCR100.dll');
const a=crt.base.add(0x3bfa0);
const seen={}; let n=0;
Interceptor.attach(a,{onEnter(){try{
  if(n>=200)return;
  let ret='?'; try{ ret=modof(this.context.rsp.readPointer()); }catch(e){}
  if(seen[ret])return; seen[ret]=1; n++;
  let bt=[]; try{ bt=Thread.backtrace(this.context,Backtracer.ACCURATE).map(modof).slice(0,8); }catch(e){bt=['btfail'];}
  send({kind:'hit',ret,bt});
}catch(e){send({kind:'err',e:String(e)});}}});
send({kind:'ready',addr:a.toString()});

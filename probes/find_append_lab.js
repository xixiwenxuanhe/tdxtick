const MODS=Process.enumerateModules();
function modof(a){try{const x=ptr(a);for(const m of MODS){if(x.compare(m.base)>=0&&x.compare(m.base.add(m.size))<0)return m.name+'+0x'+x.sub(m.base).toString(16);}}catch(e){} return String(a);}
const TdxW=Process.getModuleByName('TdxW.exe');
let lo=null,hi=null,n=0;
function hook(mod,name){ try{ const h=Process.getModuleByName(mod); const a=h.findExportByName(name); if(!a){send({kind:'noexp',mod,name});return;}
  Interceptor.attach(a,{onEnter(args){try{
    if(!lo||n>=16) return; const dst=args[0];
    if(dst.compare(lo)<0||dst.compare(hi)>=0) return; n++;
    let bt=[]; try{bt=Thread.backtrace(this.context,Backtracer.ACCURATE).map(modof).slice(0,12);}catch(e){bt=['btfail'];}
    send({kind:'append',mod,name,dst:dst.toString(),ret:modof(this.returnAddress),bt});
  }catch(e){}}}); send({kind:'hooked',mod,name,addr:a.toString()});
 }catch(e){send({kind:'hookerr',mod,name,e:String(e)});} }
for(const nm of ['memcpy','memmove','memcpy_s','memmove_s']) { hook('MSVCR100.dll',nm); hook('msvcr100.dll',nm); }
let set=false;
Interceptor.attach(TdxW.base.add(0x79bd0b),{onEnter(a){try{ if(set)return; set=true;
  const o=this.context.rdi,p=o.add(0x348).readPointer(); lo=p; hi=p.add(0x800000);
  send({kind:'range',code:o.add(0x68).readPointer().readCString(6),lo:lo.toString()});
}catch(e){send({kind:'err',e:String(e)});}}});
send({kind:'ready'});

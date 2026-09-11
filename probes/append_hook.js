const MODS=Process.enumerateModules();
function modof(a){try{const x=ptr(a);for(const m of MODS){if(x.compare(m.base)>=0&&x.compare(m.base.add(m.size))<0)return m.name+'+0x'+x.sub(m.base).toString(16);}}catch(e){} return String(a);}
const ntdll=Process.getModuleByName('ntdll.dll'), TdxW=Process.getModuleByName('TdxW.exe');
let lo=null,hi=null,n=0;
function hookCopy(addr,label){
  try{ Interceptor.attach(addr,{onEnter(args){try{
    if(!lo||n>=24) return;
    const dst=args[0];
    if(dst.compare(lo)<0||dst.compare(hi)>=0) return;
    n++;
    let bt=[]; try{ bt=Thread.backtrace(this.context,Backtracer.ACCURATE).map(modof).slice(0,12);}catch(e){bt=['btfail'];}
    send({kind:'append',label,dst:dst.toString(),ret:modof(this.returnAddress),bt});
  }catch(e){}}}); send({kind:'hooked',label,addr:addr.toString()});
  }catch(e){ send({kind:'hookerr',label,e:String(e)}); }
}
['memcpy','memmove','RtlMoveMemory','RtlCopyMemory','memcpy_s','memmove_s'].forEach(nm=>{const a=ntdll.findExportByName(nm); if(a) hookCopy(a,nm);});
hookCopy(ntdll.base.add(0x51170),'ntdll+0x51170');
hookCopy(ntdll.base.add(0x2238b),'ntdll+0x2238b');
let set=false;
Interceptor.attach(TdxW.base.add(0x79bd0b),{onEnter(a){try{ if(set)return; set=true;
  const o=this.context.rdi, p=o.add(0x348).readPointer();
  lo=p; hi=p.add(0x600000); send({kind:'range',code:o.add(0x68).readPointer().readCString(6),lo:lo.toString()});
}catch(e){send({kind:'err',e:String(e)});}}});
send({kind:'ready'});

const MODS=Process.enumerateModules();
function modof(a){try{const x=ptr(a);for(const m of MODS){if(x.compare(m.base)>=0&&x.compare(m.base.add(m.size))<0)return m.name+'+0x'+x.sub(m.base).toString(16);}}catch(e){} return String(a);}
const crt=Process.getModuleByName('MSVCR100.dll'), TdxW=Process.getModuleByName('TdxW.exe');
let tickLo=null,tickHi=null, srcLo=null,srcHi=null, n=0; const seen={};
function hook(nm){const a=crt.findExportByName(nm); if(!a)return; Interceptor.attach(a,{onEnter(args){try{
  const dst=args[0]; const len=parseInt(args[2].toString());
  if(!srcLo && tickLo && dst.compare(tickLo)>=0 && dst.compare(tickHi)<0){
    // first copy into tick buffer: capture source range; if it's the decoded cache, watch it
    const src=args[1];
    if(len>1000 && src.compare(ptr('0x10000'))>0){ srcLo=src; srcHi=src.add(len); 
      send({kind:'srccap',ret:modof(this.returnAddress),src:src.toString(),len}); }
    return;
  }
  if(srcLo && dst.compare(srcLo)>=0 && dst.compare(srcHi)<0){
    const ret=this.returnAddress.toString(); if(seen[ret])return; seen[ret]=1; n++;
    let bt=[]; try{bt=Thread.backtrace(this.context,Backtracer.ACCURATE).map(modof).slice(0,10);}catch(e){bt=['btfail'];}
    send({kind:'writesrc',ret:modof(this.returnAddress),dst:dst.toString(),len,bt});
  }
}catch(e){}}});}
['memcpy','memmove'].forEach(hook);
let set=false;
Interceptor.attach(TdxW.base.add(0x79bd0b),{onEnter(a){try{ if(set)return; set=true;
  const o=this.context.rdi,p=o.add(0x348).readPointer(); tickLo=p;tickHi=p.add(0x800000);
  send({kind:'range'});
}catch(e){}}});
send({kind:'ready'});

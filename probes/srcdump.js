const MODS=Process.enumerateModules();
function modof(a){try{const x=ptr(a);for(const m of MODS){if(x.compare(m.base)>=0&&x.compare(m.base.add(m.size))<0)return m.name+'+0x'+x.sub(m.base).toString(16);}}catch(e){} return String(a);}
const crt=Process.getModuleByName('MSVCR100.dll'), TdxW=Process.getModuleByName('TdxW.exe');
let lo=null,hi=null,n=0; const seen={};
function hook(nm){const a=crt.findExportByName(nm); if(!a)return; Interceptor.attach(a,{onEnter(args){try{
  if(!lo||n>=12)return; const dst=args[0]; if(dst.compare(lo)<0||dst.compare(hi)>=0)return;
  const src=args[1]; const len=parseInt(args[2].toString());
  const ret=this.returnAddress.toString(); if(seen[ret])return; seen[ret]=1; n++;
  let head=null; try{head=Array.from(new Uint8Array(src.readByteArray(Math.min(len,32)))).map(b=>b.toString(16).padStart(2,'0')).join(' ');}catch(e){}
  send({kind:'copy',ret:modof(this.returnAddress),len,src:src.toString(),head});
}catch(e){}}}); send({kind:'hooked',nm});}
['memcpy','memmove'].forEach(hook);
let set=false;
Interceptor.attach(TdxW.base.add(0x79bd0b),{onEnter(a){try{ if(set)return; set=true;
  const o=this.context.rdi,p=o.add(0x348).readPointer(); lo=p;hi=p.add(0x800000);
  send({kind:'range',code:o.add(0x68).readPointer().readCString(6),lo:lo.toString()});
}catch(e){send({kind:'err',e:String(e)});}}});
send({kind:'ready'});

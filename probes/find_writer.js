const base=Process.getModuleByName('TdxW.exe').base;
const ntdll=Process.getModuleByName('ntdll.dll');
function modof(a){const x=ptr(a);for(const m of Process.enumerateModules()){if(x.compare(m.base)>=0&&x.compare(m.base.add(m.size))<0)return m.name+'+0x'+x.sub(m.base).toString(16);}return '?';}
let bufLo=null,bufHi=null;
send({kind:'mods',memcpy:ntdll.findExportByName('memcpy')?ntdll.findExportByName('memcpy').toString():null,
      memmove:ntdll.findExportByName('memmove')?ntdll.findExportByName('memmove').toString():null});
for(const nm of ['memcpy','memmove']){
  const addr=ntdll.findExportByName(nm); if(!addr){send({kind:'noexport',nm});continue;}
  Interceptor.attach(addr,{onEnter(args){try{
    if(!bufLo)return;
    const dst=args[0];
    if(dst.compare(bufLo)>=0&&dst.compare(bufHi)<0){
      send({kind:'copy',fn:nm,dst:dst.toString(),size:args[2].toInt32(),
            ret:this.returnAddress.toString(),retmod:modof(this.returnAddress),
            bt:Thread.backtrace(this.context,Backtracer.ACCURATE).map(x=>x.toString()).slice(0,10)});
    }}catch(e){}}});
  send({kind:'hooked',nm,addr:addr.toString()});
}
Interceptor.attach(base.add(0x79bd0b),{onEnter(a){try{
  if(bufLo)return;
  const o=this.context.rdi;
  const cnt=o.add(0x250).readU32(), p=o.add(0x348).readPointer();
  bufLo=p; bufHi=p.add(0x1000000);
  send({kind:'range',count:cnt,lo:bufLo.toString()});
}catch(e){send({kind:'err',e:String(e)});}}});
send({kind:'ready'});

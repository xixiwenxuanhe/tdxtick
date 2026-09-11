const ntdll=Process.getModuleByName('ntdll.dll');
function modof(a){const x=ptr(a);for(const m of Process.enumerateModules()){if(x.compare(m.base)>=0&&x.compare(m.base.add(m.size))<0)return m.name+'+0x'+x.sub(m.base).toString(16);}return '?';}
function bt(ctx){try{return Thread.backtrace(ctx,Backtracer.ACCURATE).map(modof).slice(0,10);}catch(e){return [String(e)];}}
let n=0;
const alloc=ntdll.findExportByName('RtlAllocateHeap');
Interceptor.attach(alloc,{onEnter(args){this.sz=args[2].toUInt32?args[2].toUInt32():parseInt(args[2].toString());},
  onLeave(retval){try{ if(this.sz>100000 && n<40){ n++; send({kind:'alloc',size:this.sz,ret:modof(this.returnAddress),bt:bt(this.context)}); } }catch(e){}}});
const realloc=ntdll.findExportByName('RtlReAllocateHeap');
if(realloc) Interceptor.attach(realloc,{onEnter(args){try{ const sz=parseInt(args[3].toString()); if(sz>100000 && n<40){ n++; send({kind:'realloc',size:sz,ret:modof(this.returnAddress),bt:bt(this.context)}); } }catch(e){}}});
send({kind:'ready',alloc:alloc.toString(),realloc:realloc?realloc.toString():null});

// 定位"把0x0554线数据写进逐笔缓冲"的函数: 钩 ntdll 内部拷贝点, 按目标地址过滤
const MODS=Process.enumerateModules();
function modof(a){const x=ptr(a);for(const m of MODS){if(x.compare(m.base)>=0&&x.compare(m.base.add(m.size))<0)return m.name+'+0x'+x.sub(m.base).toString(16);}return x.toString();}
const ntdll=Process.getModuleByName('ntdll.dll');
const TdxW=Process.getModuleByName('TdxW.exe');
let bufLo=null, bufHi=null, armed=false, n=0;
function attachAt(addr,label){
  try{ Interceptor.attach(addr,{onEnter(args){try{
    if(!bufLo || n>=30) return;
    const dst=args[0];
    if(dst.compare(bufLo)>=0 && dst.compare(bufHi)<0){
      n++;
      let bt=[]; try{ bt=Thread.backtrace(this.context,Backtracer.ACCURATE).map(modof).slice(0,10);}catch(e){bt=['btfail'];}
      send({kind:'copy',label,dst:dst.toString(),ret:modof(this.returnAddress),bt});
    }
  }catch(e){}}}); send({kind:'hooked',label,addr:addr.toString()});
  }catch(e){ send({kind:'hookerr',label,e:String(e)}); }
}
['memcpy','memmove','RtlMoveMemory','RtlCopyMemory'].forEach(nm=>{ const a=ntdll.findExportByName(nm); if(a) attachAt(a,nm); });
// MAM 观测到的两个 ntdll 内部写点
attachAt(ntdll.base.add(0x51170),'ntdll+0x51170');
attachAt(ntdll.base.add(0x2238b),'ntdll+0x2238b');
let set=false;
Interceptor.attach(TdxW.base.add(0x79bd0b),{onEnter(a){try{
  if(set) return; set=true;
  const o=this.context.rdi; const p=o.add(0x348).readPointer();
  bufLo=p; bufHi=p.add(0x400000);
  send({kind:'range',lo:bufLo.toString()});
}catch(e){send({kind:'err',e:String(e)});}}});
send({kind:'ready'});

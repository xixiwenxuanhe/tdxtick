const MODS=Process.enumerateModules();
function modof(a){try{const x=ptr(a);for(const m of MODS){if(x.compare(m.base)>=0&&x.compare(m.base.add(m.size))<0)return m.name+'+0x'+x.sub(m.base).toString(16);}}catch(e){} return String(a);}
const ws2=Process.getModuleByName('WS2_32.dll'), k32=Process.getModuleByName('kernel32.dll');
const pending=new Map(); let done=false;
Interceptor.attach(ws2.findExportByName('WSARecv'),{onEnter(args){try{const ov=args[5]; if(!ov.isNull()) pending.set(ov.toString(), args[1].add(8).readPointer());}catch(e){}}});
Interceptor.attach(k32.findExportByName('GetQueuedCompletionStatus'),{onEnter(args){this.ovp=args[3];},onLeave(ret){try{
  if(ret.toInt32()===0)return; const ov=this.ovp.readPointer(); if(ov.isNull())return;
  const buf=pending.get(ov.toString()); if(!buf)return; pending.delete(ov.toString());
  if(done) return;
  const cmd=buf.add(10).readU16();
  if(cmd!==0x554) return;
  done=true;
  const tid=Process.getCurrentThreadId();
  const calls=[];
  try{ Stalker.follow(tid,{events:{call:true},onReceive(ev){
    const a=Stalker.parse(ev,{annotate:false});
    for(const e of a){ if(e[0]==='call') calls.push(e[1].toString()); }
  }});
  setTimeout(()=>{ try{Stalker.unfollow(tid);}catch(e){} try{Stalker.flush();}catch(e){}
    const uniq=[...new Set(calls)];
    send({kind:'calls',n:calls.length,uniq:uniq.map(modof)});
  },50);
  }catch(e){send({kind:'stalkerr',e:String(e)});}
}catch(e){}}});
send({kind:'ready'});

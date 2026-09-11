const MODS=Process.enumerateModules();
function modof(a){try{const x=ptr(a);for(const m of MODS){if(x.compare(m.base)>=0&&x.compare(m.base.add(m.size))<0)return m.name+'+0x'+x.sub(m.base).toString(16);}}catch(e){} return String(a);}
const ws2=Process.getModuleByName('WS2_32.dll'),k32=Process.getModuleByName('kernel32.dll');
const pending=new Map(); let done=false;
Interceptor.attach(ws2.findExportByName('WSARecv'),{onEnter(args){try{const ov=args[5];if(!ov.isNull())pending.set(ov.toString(),args[1].add(8).readPointer());}catch(e){}}});
Interceptor.attach(k32.findExportByName('GetQueuedCompletionStatus'),{onEnter(args){this.ovp=args[3];},onLeave(ret){try{
  if(done||ret.toInt32()===0)return; const ov=this.ovp.readPointer(); if(ov.isNull())return;
  const buf=pending.get(ov.toString()); if(!buf)return; pending.delete(ov.toString());
  if(buf.add(10).readU16()!==0x554)return;
  done=true;
  const events=Object.create(null);
  const followed=[];
  for(const t of Process.enumerateThreads()){
    try{ Stalker.follow(t.id,{events:{call:true},onReceive(ev){ try{
      const a=Stalker.parse(ev,{annotate:false});
      for(const e of a){ if(e[0]==='call'){ const k=e[1].toString(); events[k]=(events[k]||0)+1; } }
    }catch(e){} }}); followed.push(t.id); }catch(e){}
  }
  send({kind:'following',n:followed.length});
  setTimeout(()=>{ for(const id of followed){ try{Stalker.unfollow(id);}catch(e){} } try{Stalker.flush();}catch(e){}
    const keys=Object.keys(events).map(Number).sort((a,b)=>events[b]-events[a]).slice(0,40).map(x=>modof(x)+' x'+events[x]);
    send({kind:'calls',total:Object.keys(events).length,top:keys});
  },40);
}catch(e){send({kind:'err',e:String(e)});}}});
send({kind:'ready'});

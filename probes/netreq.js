const ws2=Process.getModuleByName('WS2_32.dll');
function modof(a){const x=ptr(a);for(const m of Process.enumerateModules()){if(x.compare(m.base)>=0&&x.compare(m.base.add(m.size))<0)return m.name+'+0x'+x.sub(m.base).toString(16);}return '?';}
const getpeer=ws2.findExportByName('getpeername');
let sent=0;
const wsasend=ws2.findExportByName('WSASend');
Interceptor.attach(wsasend,{onEnter(args){try{
  if(sent>=40)return; sent++;
  const wbuf=args[1]; const len=wbuf.readU32(); const buf=wbuf.add(8).readPointer();
  let ep='';
  try{ const sa=Memory.alloc(64); const sal=Memory.alloc(4); sal.writeInt(64);
       if(getpeer(args[0],sa,sal)===0){ const fam=sa.readU16();
         if(fam===2){ const port=(sa.add(2).readU8()<<8)|sa.add(3).readU8();
           const ip=[sa.add(4).readU8(),sa.add(5).readU8(),sa.add(6).readU8(),sa.add(7).readU8()].join('.');
           ep=ip+':'+port; } } }catch(e){ep='?';}
  send({kind:'send',sock:args[0].toString(),ep,len,caller:modof(this.returnAddress)},buf.readByteArray(Math.min(len,160)));
}catch(e){send({kind:'err',e:String(e)});}}});
send({kind:'ready',send:wsasend.toString()});

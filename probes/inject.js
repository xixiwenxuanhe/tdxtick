const ws2=Process.getModuleByName('WS2_32.dll'),k32=Process.getModuleByName('kernel32.dll');
const sendFn=new NativeFunction(ws2.findExportByName('WSASend'),'int',['pointer','pointer','uint','pointer','uint','pointer','pointer']);
let sock=null;
Interceptor.attach(ws2.findExportByName('WSASend'),{onEnter(args){try{
  if(sock) return;
  const w=args[1]; const len=w.readU32(); const buf=w.add(8).readPointer();
  if(len<12) return; const cmd=buf.add(10).readU16();
  if(cmd===0x550||cmd===0x555||cmd===0x554||cmd===0x55e){ sock=args[0]; send({kind:'sock',s:sock.toString(),cmd:cmd.toString(16)}); }
}catch(e){}}});
// capture responses
const pending=new Map();
Interceptor.attach(ws2.findExportByName('WSARecv'),{onEnter(args){try{const ov=args[5];if(!ov.isNull())pending.set(ov.toString(),args[1].add(8).readPointer());}catch(e){}}});
Interceptor.attach(k32.findExportByName('GetQueuedCompletionStatus'),{onEnter(args){this.ovp=args[3];},onLeave(ret){try{
  if(ret.toInt32()===0)return; const ov=this.ovp.readPointer(); if(ov.isNull())return;
  const buf=pending.get(ov.toString()); if(!buf)return; pending.delete(ov.toString());
  const cmd=buf.add(10).readU16(), ln=buf.add(12).readU16();
  if(cmd===0x55e) send({kind:'resp55e',len:ln}, buf.add(16).readByteArray(ln));
}catch(e){}}});
rpc.exports={ inject(hex){ if(!sock) return -1; const n=hex.length/2; const b=Memory.alloc(n); for(let i=0;i<n;i++) b.add(i).writeU8(parseInt(hex.substr(i*2,2),16)); const wb=Memory.alloc(16); wb.writeU32(n); wb.add(8).writePointer(b); const sent=Memory.alloc(4); sent.writeU32(0); const r=sendFn(sock,wb,1,sent,0,ptr(0),ptr(0)); return r; } };
send({kind:'ready'});

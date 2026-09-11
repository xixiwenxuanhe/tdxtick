const ws2=Process.getModuleByName('WS2_32.dll');
const seen={};
Interceptor.attach(ws2.findExportByName('WSASend'),{onEnter(args){try{
  const wbuf=args[1]; const len=wbuf.readU32(); const buf=wbuf.add(8).readPointer();
  if(len<12||len>600) return;
  const cmd=buf.add(10).readU16();
  const key=cmd+':'+len;
  if(seen[key] && seen[key]>=3) return; seen[key]=(seen[key]||0)+1;
  send({kind:'send',cmd:cmd.toString(16),len}, buf.readByteArray(Math.min(len,80)));
}catch(e){}}});
send({kind:'ready'});

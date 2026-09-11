const TdxW=Process.getModuleByName('TdxW.exe');
let done=false;
Interceptor.attach(TdxW.base.add(0x760a80),{onEnter(a){try{
  if(done)return; done=true;
  const o=a[0]; const code=o.add(0x68).readPointer().readCString(6);
  const n=o.add(0x254).readU32(), p=o.add(0x3d0).readPointer();
  send({kind:'dump',code,count:n}, p.readByteArray(Math.min(n,4000)*20));
}catch(e){send({kind:'err',e:String(e)});}}});
send({kind:'ready'});
